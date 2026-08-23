#Musicai
-------
**Hand Gesture Music Maker**
---------------------------------------

A Python project that turns hand gestures into music.
Point at different parts of the screen to play piano notes, make a fist to trigger a beat, open your palm for a hi-hat, and make a triangle with both hands to play back the music you just created.
-------------------------------------------

**Tech Stack**:
Python, OpenCV, MediaPipe, Pygame

-------------------------------------------------

## What can it do?

- Detect up to two hands using MediaPipe
- Play piano notes using your index finger (keep the other fingers closed)
- Trigger a beat with a fist
- Trigger a hi-hat with an open palm
- Record the timing of the gestures
- Play the recorded sequence back
- Use mouse clicks as an alternative way to play piano notes
- Display detected hand landmarks in real time

## Gestures

☝️ (yes copy this exact pose) Index finger -> Play a piano note 
                             <br>  Fist -> Play the beat 
                             <br>  Open palm -> Play the hi-hat 
                             <br>  Two-hand triangle -> Start playback 

The horizontal position of the index finger determines which piano note gets played.

There are currently eight notes:

`C4 D4 E4 F4 G4 A4 B4 C5`

-------------------------------------------------

## How it works

The webcam feed is captured using OpenCV and passed into MediaPipe's hand-tracking model.

MediaPipe gives the program the positions of the hand landmarks. The program then compares the distances between landmarks to figure out which gesture is being made.

For example, a fist is detected by comparing the fingertip positions with their corresponding joints. An extended index finger is detected separately so it can be used to select piano notes.

The program also keeps track of when each sound was triggered.

Instead of recording the actual audio, it stores events like:
(time, sound_type, note)

For example:

(0.42, "piano", 3)
(1.10, "beat", None)
(1.48, "hihat", None)

When playback starts, the program checks the elapsed time and plays each recorded event at approximately the same point in the sequence.
--------------------------------------
**Controls**
-Q — Quit the program
-R — Start a new recording
- Mouse: Clicking inside the OpenCV window can also play a piano note based on the horizontal position of the mouse.
----------------------------------------
**Setup**

You'll need Python (3.12 preferably since mediapipe doesn't have a 3.13 or 3.14 version yet) installed along with these packages:

`pip install opencv-python mediapipe pygame`

The project also needs the audio files used by the program.
Create a sounds folder next to the Python file:

Hand-Gesture-Music-Maker/
│
├── main.py
├── README.md
└── sounds/
    ├── C4.mp3
    ├── D4.mp3
    ├── E4.mp3
    ├── F4.mp3
    ├── G4.mp3
    ├── A4.mp3
    ├── B4.mp3
    ├── C5.mp3
    ├── beat.mp3
    └── hihat.mp3

The program expects those filenames exactly.

Then run:
`python main.py`

You'll need to allow the program to access your webcam.
