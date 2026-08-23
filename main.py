import cv2
import mediapipe as mp
import pygame
import time
import math
from pathlib import Path

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.init()

NOTE_NAMES = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
SOUND_FOLDER = Path(__file__).parent / "sounds"

def load_sound(filename):
    """Load a user-provided MP3 and fail with a useful setup message."""
    path = SOUND_FOLDER / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing audio file: {path}")
    return pygame.mixer.Sound(str(path))

PIANO_NOTES = [load_sound(f"{note}.mp3") for note in NOTE_NAMES]

SOUND_BEAT = load_sound("beat.mp3")
SOUND_HIHAT = load_sound("hihat.mp3")

def dist(p1, p2):
    """Euclidean distance between two landmarks (normalized coordinates)."""
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def is_fist(hand_landmarks):
    """Detects if a hand is forming a fist."""
    wrist = hand_landmarks.landmark[0]
    tips = [8, 12, 16, 20] # index, middle, ring, pinky tips
    mcp_joints = [5, 9, 13, 17]
    
    closed_count = 0
    for tip, mcp in zip(tips, mcp_joints):
        if dist(hand_landmarks.landmark[tip], wrist) < dist(hand_landmarks.landmark[mcp], wrist):
            closed_count += 1
    return closed_count == len(tips)

def is_index_pointing(hand_landmarks):
    """Detect an extended index finger with the other fingers closed."""
    wrist = hand_landmarks.landmark[0]
    index_is_extended = dist(hand_landmarks.landmark[8], wrist) > dist(hand_landmarks.landmark[5], wrist)
    other_fingers_closed = all(
        dist(hand_landmarks.landmark[tip], wrist) < dist(hand_landmarks.landmark[mcp], wrist)
        for tip, mcp in zip([12, 16, 20], [9, 13, 17])
    )
    return index_is_extended and other_fingers_closed

def is_open_palm(hand_landmarks):
    """Detect an open palm by checking that all fingertips are extended."""
    wrist = hand_landmarks.landmark[0]
    tips = [4, 8, 12, 16, 20]
    mcp_joints = [2, 5, 9, 13, 17]
    return all(
        dist(hand_landmarks.landmark[tip], wrist)
        > dist(hand_landmarks.landmark[mcp], wrist)
        for tip, mcp in zip(tips, mcp_joints)
    )

def is_triangle_gesture(hand1, hand2):
    """Detects two hands forming a triangle (illuminati/play gesture).
       - Index tips (8) close together at top
       - Thumb tips (4) close together at bottom
    """
    h1_index = hand1.landmark[8]
    h2_index = hand2.landmark[8]
    h1_thumb = hand1.landmark[4]
    h2_thumb = hand2.landmark[4]
    
    index_dist = dist(h1_index, h2_index)
    thumb_dist = dist(h1_thumb, h2_thumb)
    
    indices_close = index_dist < 0.12
    thumbs_close = thumb_dist < 0.12
    indices_above = (h1_index.y < h1_thumb.y) and (h2_index.y < h2_thumb.y)
    
    return indices_close and thumbs_close and indices_above

def main():
    print("Initializing webcam...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("Camera index 0 failed. Trying index 1...")
        cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("ERROR: Could not open any webcam. Check Windows Privacy Settings or if another app is using it.")
        return

    print("Webcam connected! Opening display window...")
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    cv2.namedWindow("Hand Gesture Music Maker", cv2.WINDOW_NORMAL)
    
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )
    mp_draw = mp.solutions.drawing_utils
    
    last_trigger_time = {"beat": 0, "hihat": 0}
    last_note_trigger_time = 0
    last_played_note = None
    last_played_note_time = 0
    
    # music recording n playback state
    is_recording = True
    is_playing_back = False
    recorded_events = []
    start_record_time = time.time()
    playback_start_time = 0
    playback_index = 0
    
    # triangle gesture hold state
    triangle_detect_start = None

    def play_note(note_idx, event_time):
        nonlocal last_played_note, last_played_note_time, last_note_trigger_time
        PIANO_NOTES[note_idx].play()
        last_note_trigger_time = event_time
        last_played_note = NOTE_NAMES[note_idx]
        last_played_note_time = event_time

        if is_recording:
            rel_time = event_time - start_record_time
            recorded_events.append((rel_time, "piano", note_idx))

    def handle_mouse_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and not is_playing_back:
            note_idx = min(max(int(x / max(w, 1) * len(NOTE_NAMES)), 0), len(NOTE_NAMES) - 1)
            play_note(note_idx, time.time())

    cv2.setMouseCallback("Hand Gesture Music Maker", handle_mouse_click)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        current_time = time.time()

        cv2.rectangle(frame, (20, h - 90), (450, h - 20), (20, 20, 20), -1)
        status_text = "PLAYING BACK TRACK..." if is_playing_back else "RECORDING GESTURES..."
        status_color = (0, 255, 0) if is_playing_back else (0, 0, 255)
        
        cv2.putText(frame, f"STATUS: {status_text}", (35, h - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        cv2.putText(frame, "Fist: beat | Open palm: hi-hat | Triangle: playback", (35, h - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        if last_played_note and current_time - last_played_note_time < 0.8:
            cv2.putText(frame, f"NOTE: {last_played_note}", (w // 2 - 100, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 215, 255), 3)

        if results.multi_hand_landmarks and not is_playing_back:
            num_detected_hands = len(results.multi_hand_landmarks)
          
            if num_detected_hands == 2:
                h1 = results.multi_hand_landmarks[0]
                h2 = results.multi_hand_landmarks[1]
                
                if is_triangle_gesture(h1, h2):
                    if triangle_detect_start is None:
                        triangle_detect_start = current_time
                    elif current_time - triangle_detect_start > 0.8: 
                        is_playing_back = True
                        is_recording = False
                        playback_start_time = current_time
                        playback_index = 0
                        triangle_detect_start = None
                    
                        cv2.putText(frame, "PLAYING RECORDED MUSIC!", (w//4, h//2),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                else:
                    triangle_detect_start = None
            else:
                triangle_detect_start = None

            # individual hand gesture processing#
            for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                index_tip = hand_landmarks.landmark[8]
                cx, cy = int(index_tip.x * w), int(index_tip.y * h)
                
                cv2.circle(frame, (cx, cy), 12, (255, 0, 128), cv2.FILLED)
 
                if is_index_pointing(hand_landmarks):
                    note_idx = min(max(int(cx / max(w, 1) * len(NOTE_NAMES)), 0), len(NOTE_NAMES) - 1)
                    if current_time - last_note_trigger_time > 0.3:
                        play_note(note_idx, current_time)

                elif is_fist(hand_landmarks):
                    if (current_time - last_trigger_time["beat"]) > 0.4:
                        SOUND_BEAT.play()
                        last_trigger_time["beat"] = current_time
                        cv2.putText(frame, "BEAT!", (cx - 30, cy - 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                        
                        if is_recording:
                            rel_time = current_time - start_record_time
                            recorded_events.append((rel_time, "beat", None))
                elif is_open_palm(hand_landmarks):
                    if (current_time - last_trigger_time["hihat"]) > 0.25:
                        SOUND_HIHAT.play()
                        last_trigger_time["hihat"] = current_time
                        cv2.putText(frame, "HI-HAT!", (cx - 30, cy - 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                        
                        if is_recording:
                            rel_time = current_time - start_record_time
                            recorded_events.append((rel_time, "hihat", None))
        if is_playing_back and recorded_events:
            elapsed_play_time = current_time - playback_start_time
            
            while playback_index < len(recorded_events):
                event_time, sound_type, param = recorded_events[playback_index]
                
                if elapsed_play_time >= event_time:
                    if sound_type == "piano":
                        play_note(param, current_time)
                    elif sound_type == "beat":
                        SOUND_BEAT.play()
                    elif sound_type == "hihat":
                        SOUND_HIHAT.play()
                    playback_index += 1
                else:
                    break 
            if playback_index >= len(recorded_events):
                if elapsed_play_time > recorded_events[-1][0] + 1.0:
                    playback_start_time = current_time
                    playback_index = 0
        cv2.imshow("Hand Gesture Music Maker", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            is_recording = True
            is_playing_back = False
            recorded_events.clear()
            start_record_time = time.time()

    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()

if __name__ == "__main__":
    main()
