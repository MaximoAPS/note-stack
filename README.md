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
- **🔢 Number Melody**: Transform digit sequences (Pi, Fibonacci, dates) into melodies with learned durations
- **🤖 AI Track Generation**: Heuristic-based bass, chord, harmony, and adornment generators

## Studio UI

The **Studio UI** provides an end-to-end workflow for creating expressive piano compositions:

1. **Number Melody Generator** — Paste digit sequences (Pi, Fibonacci, dates) and transform them into melodies
   - **pair_mod chunking**: Digit pairs (00-99) mapped via modulus for rich pitch variation
   - **Multi-style training**: Learn duration patterns from multiple demo MIDIs
   - **Tonic/mode/octave controls**: Customize scale and range
   - Generates a "Solo" track ready to play or edit

2. **Tracks Studio** — Add, edit, and generate AI tracks
   - **Track roles**: Mark tracks as Solo (melody), Base (bass/chords), or Adorn (decoration)
   - **AI Fill Track** buttons: Generate Bass Line (keys 1-28), Chord Base (keys 29-52), Adorn Pluck, or Harmony Line from existing tracks
   - **Per-track FX**: Intensity (harmonic multiplier), Delay (30/160s echo), Hold (sustain duration)
   - **Edit notes**: Interactive data editor with add/delete rows, beat-range delete
   - **Mute/solo**: Isolate tracks during composition

3. **One-Click Play** — Synthesize and download WAV/MIDI instantly

### Number Melody

Turn any digit sequence into expressive melodies! The Number Melody feature maps digits to piano keys using scales (major, minor, pentatonic, chromatic) and learns natural rhythm patterns from style MIDIs.

**Example workflow:**
1. Paste digits of Pi: `3.14159265358979323846...`
2. Choose chunking: `pair_mod` with modulus 12 (chromatic)
3. Select multiple style MIDIs (Chopin + Liszt + Scarlatti)
4. Set tonic 40 (E), max key 64
5. Generate → Creates melody with musically-sensible rhythms

The system analyzes interval jumps in your style MIDIs and predicts note durations based on melodic motion, creating melodies that feel musical rather than mechanical.

**CLI Usage:**
```bash
python3 number_melody.py \
  --digits 314159265358979323846 \
  --tonic 40 \
  --chunk pair_mod \
  --modulus 12 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --out pi_melody.mid \
  --bpm 96
```

See `analysis/NUMBER_MELODY.md` for full documentation and technical details.

### AI Track Generation

Generate new tracks using **Phase 1 heuristic patterns** from existing tracks:
- **Bass Line** (keys 1-28): Extracts lowest notes
- **Chord Base** (keys 29-52): Extracts note clusters/chords
- **Adorn Pluck** (keys 45-72): Creates sparse decorative patterns
- **Harmony Line** (keys 45-72): Harmonizes melody with interval transposition

AI tracks are generated from other tracks in the song and automatically assigned role names (Base/Adorn).

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

1. **Generate a Number Melody**: Paste Pi digits, select 3 style MIDIs, click "Generate"
2. **Add AI tracks**: Open the generated Solo track, click "Bass Line" or "Chord Base"
3. **Edit notes**: Use the interactive table to fine-tune individual notes
4. **Adjust FX**: Set intensity (1.0-2.0), enable delay, adjust hold duration
5. Click "▶ Play" to synthesize and hear the music
6. Download as WAV or MIDI

### Creating Music

- **Add Track**: Click "➕ Add Empty Track" to create a new track
- **Track Parameters**:
  - **Intensity (I)**: Harmonic intensity multiplier (1.0 for melody, 2.0 for bass)
  - **Delay**: Enable 30/160 second delay voice for richer sound
  - **Hold (d)**: Sustain duration in seconds (0.5 for short, 2.0 for long notes)
- **Edit Notes**: Use the data editor to add/modify/delete notes
  - Piano Key: 1-88 (A4 = key 49 = 440 Hz)
  - Start Beat: When the note begins
  - Duration: How long the note plays (in beats)
  - Velocity: Note dynamics (1-127, default 100)
- **Delete beat ranges**: Enter range like "4-8" and click "Delete Range"

### MIDI Import

Load MIDI files from the `demos/` folder or **upload your own** using the file uploader:
- MIDI note numbers are automatically converted (MIDI note - 20 = piano key)
- Multiple channels are split into separate tracks
- Tempo is extracted from MIDI file

## Synthesis Model

The timbre synthesis precisely matches the Desmos "Piano Song" graph with realistic key-dependent decay:

### Key to Frequency
```
f = 2^((key - 49) / 12) × 440 Hz
```

### Harmonics
- 64 harmonics per note: `f_h = H × f0` (H = 1 to 64)
- Skip harmonics above 0.92×Nyquist (20,286 Hz)
- Intensity: `I(h) = 1 / (1.24729 × h^1.5 + 1)` where h = H - 1

### Envelope
- **Attack**: Polynomial rise from t=0.05s to peak at t=0.172s
- **Sustain**: Time freeze between 0.34s and d seconds
- **Decay**: Exponential decay with Box-Muller randomized rate per harmonic
- **Key-dependent**: Higher keys decay faster (×3.5 at C8), lower keys ring longer (×0.55 at A0), like a real piano
- Decay rate: `n ~ Normal(μ=10.2, σ=3.54)` × key_scale, seeded deterministically for repeatability

### Output
- Sample rate: 44,100 Hz
- Bit depth: 16-bit PCM
- Channels: Stereo (Haas effect ~15ms for spatial width)
- Master filter: Soft lowpass ~13 kHz
- Micro-detune: ±3.5 cents per harmonic for organic timbre
- Peak normalization: 0.89

## Project Structure

```
note-stack/
├── app.py                  # Streamlit Studio UI
├── notes.py                # Data model (Note, Track, Song)
├── synth.py                # Synthesis engine
├── midi_io.py              # MIDI import/export (with velocity fix)
├── number_melody.py        # Number Melody feature
├── pattern_generators.py   # AI track generation heuristics
├── track_helpers.py        # Track manipulation utilities
├── editor_session.py       # Multi-MIDI session model (for advanced workflows)
├── check_synth.py          # Synthesis test
├── test_editor_session.py  # Editor session smoke tests
├── requirements.txt        # Python dependencies
├── analysis/               # Technical documentation
│   ├── NUMBER_MELODY.md    # Number Melody docs (EN)
│   ├── NUMBER_MELODY.es.md # Number Melody docs (ES)
│   ├── EDITOR_UX.md        # Advanced editor vision (EN)
│   └── EDITOR_UX.es.md     # Advanced editor vision (ES)
├── demos/                  # MIDI demo files
│   ├── ATTRIBUTION.md      # MAESTRO dataset license
│   └── *.mid
└── README.md
```

## Testing

Verify the synthesis engine:

```bash
python check_synth.py
```

This renders the Piano Song melody track and verifies output duration.

Test the editor session model:

```bash
python test_editor_session.py
```

This runs smoke tests for multi-MIDI session management, track role assignment, and key range filtering.

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
