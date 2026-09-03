# Note Stack

Python timeline sequencer with piano key numbers on tracks and Desmos piano harmonic synthesis.

## Overview

Note Stack V1 is a Streamlit web application for composing and synthesizing piano music using a physically-inspired timbre model. The synthesis engine implements the exact harmonic series and envelope characteristics from the [Desmos Piano Song graph](https://www.desmos.com/calculator/iilldhgqnk).

## Features

- **Piano Key Notation**: Use piano keys 1-88 (not MIDI note numbers)
- **Multi-Track Sequencer**: Create and edit multiple tracks with independent parameters
- **Desmos Timbre Synthesis**: 64-harmonic synthesis matching the reference Desmos graph
- **Interactive Timeline**: Visual timeline editor for each track
- **MIDI Import/Export**: Load MIDI files and export your compositions
- **Demo Presets**: Includes the original "Piano Song" from Desmos

## Installation

```bash
pip install -r requirements.txt
```

## Running the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## Usage

### Quick Start

1. Click "Load Piano Song" to load the Desmos reference composition
2. Click "▶ Play" to synthesize and hear the music
3. Adjust BPM, mute tracks, or modify parameters in each track expander
4. Download as WAV or MIDI

### Creating Music

- **Add Track**: Click "➕ Add Track" to create a new empty track
- **Track Parameters**:
  - **Intensity (I)**: Harmonic intensity multiplier (1.0 for melody, 2.0 for bass)
  - **Delay**: Enable 30/160 second delay voice for richer sound
  - **Hold (d)**: Sustain duration in seconds (0.5 for short, 2.0 for long notes)
- **Add Notes**: Use the controls at the bottom of each track to add notes
  - Piano Key: 1-88 (A4 = key 49 = 440 Hz)
  - Start Beat: When the note begins
  - Duration: How long the note plays (in beats)
  - Velocity: Note dynamics (1-127, default 100)

### MIDI Import

Load MIDI files from the `demos/` folder:
- MIDI note numbers are automatically converted (MIDI note - 20 = piano key)
- Multiple channels are split into separate tracks
- Tempo is extracted from MIDI file

## Synthesis Model

The timbre synthesis precisely matches the Desmos "Piano Song" graph:

### Key to Frequency
```
f = 2^((key - 49) / 12) × 440 Hz
```

### Harmonics
- 64 harmonics per note: `f_h = H × f0` (H = 1 to 64)
- Skip harmonics above Nyquist frequency (22,050 Hz)
- Intensity: `I(h) = 1 / (1.24729 × h^1.5 + 1)` where h = H - 1

### Envelope
- **Attack**: Polynomial rise from t=0.05s to peak at t=0.172s
- **Sustain**: Time freeze between 0.34s and d seconds
- **Decay**: Exponential decay with Box-Muller randomized rate per harmonic
- Decay rate: `n ~ Normal(μ=10.2, σ=3.54)` seeded deterministically for repeatability

### Output
- Sample rate: 44,100 Hz
- Bit depth: 16-bit PCM
- Channels: Mono
- Peak normalization: 0.89

## Project Structure

```
note-stack/
├── app.py              # Streamlit web interface
├── notes.py            # Data model (Note, Track, Song)
├── synth.py            # Synthesis engine
├── midi_io.py          # MIDI import/export
├── check_synth.py      # Synthesis test
├── requirements.txt    # Python dependencies
├── demos/              # MIDI demo files
│   ├── ATTRIBUTION.md  # MAESTRO dataset license
│   └── .gitkeep
└── README.md
```

## Testing

Verify the synthesis engine:

```bash
python check_synth.py
```

This renders the Piano Song melody track and verifies output duration.

## Credits

- **Timbre Model**: Based on the [Desmos Piano Song graph](https://www.desmos.com/calculator/iilldhgqnk)
- **MAESTRO Dataset**: Demo MIDI files (if present) from MAESTRO v3.0.0, © CC BY-NC-SA 4.0

## Piano Key Reference

Piano keys 1-88 correspond to:
- Key 1: A0 (27.5 Hz)
- Key 49: A4 (440 Hz) - Concert pitch
- Key 88: C8 (4,186 Hz)

MIDI conversion: `MIDI note = piano key + 20`

## License

This project is open source. MAESTRO dataset excerpts are licensed under CC BY-NC-SA 4.0.
