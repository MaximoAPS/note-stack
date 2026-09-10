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
- **🎸 Pattern → Base**: Generate ordered bass lines from digit patterns (e.g., Pi "3-1-4-1-5" → bass with those degrees)
- **🎸🎵 Fill Base from Solo**: Generate ordered bass from pattern that harmonizes under an existing Solo track with AI-chosen offset
- **🤖 AI Track Generation**: Heuristic-based bass, chord, harmony, and adornment generators

## Studio UI

The **Studio UI** provides an end-to-end workflow for creating expressive piano compositions:

1. **Style / Training MIDI Library** (NEW) — Global session-wide style pack at the top
   - Upload multiple MIDIs + pick demos into a session style pack
   - Shared by Number Melody, Pattern→Base, AI fills, jump_predict, etc.
   - Shows loaded MIDIs with track counts
   - Clear / remove entries individually or all at once
   - Tools fall back to MIDI-GPT / heuristics / neutral defaults if empty

2. **Number Sequence → Solo / Melody** — Prominent digit input and solo generation
   - Paste digit sequences (Pi, Fibonacci, dates) right at the top
   - Generate Solo melody OR upload a solo MIDI
   - **pair_mod chunking**: Digit pairs (00-99) mapped via modulus for rich pitch variation
   - **Multi-style training**: Uses global style pack (or override in advanced options)
   - **Tonic/mode/BPM controls**: Customize scale, range, and tempo
   - **Advanced options in expander**: Chunking, register, key range, style override
   - Generates a "🎵 Solo" track ready to play or edit

3. **Pattern → Base Generator** — Create ordered bass lines from digit patterns
   - **Ordered pattern mapping**: Digits like "3-1-4-1-5" become bass notes in that exact sequence
   - **Offset or tonic+scale modes**: Map digits as simple offsets (3+10=13) or scale degrees
   - **AI duration learning**: Uses global style pack for rhythm patterns
   - **Bass register control**: Set min/max keys (e.g., 28-42 for typical bass range)
   - Generates a "🎸 Base" track distinct from arbitrary AI Fill Bass

4. **Tracks Studio** — Add, edit, and generate AI tracks
   - **Track roles**: Mark tracks as Solo (melody), Base (bass/chords), or Adorn (decoration)
   - **Loop tracks** (NEW): Enable 🔁 Loop for Base tracks to repeat pattern across timeline
     - Loop length in beats (or 0 for "loop until song end")
     - When playing/exporting, track notes repeat automatically
   - **AI Fill Track** buttons: Generate Bass Line (keys 1-28), Chord Base (keys 29-52), Adorn Pluck, or Harmony Line from existing tracks
   - **FX Calibration** (IMPROVED): Clear Intensity/Delay/Hold controls with sensible ranges
     - Intensity: 1.0=melody, 2.0=bass (captions show guidance)
     - Delay: 30/160s echo toggle
     - Hold: 0.5s=short, 2.0s=long sustain
     - 🔄 Piano Defaults button: Reset to I=1.0, Hold=0.8s, Delay=On
   - **Cluster Badge Editor**: Edit notes as horizontal badges showing simultaneous keys + duration chips
   - **Insert Silence / Rests** (NEW): Add timed silences between notes
     - Insert rest at end or at specific beat position
     - Shifts later notes to create gaps
     - Rests are gaps (no fake notes)
   - **Paste cluster strings**: Import note sequences like `35-35,36-38-35` (dash separates clusters, comma separates keys)
   - **Advanced table editor**: Full data table available in expander for precise edits
   - **Mute/solo**: Isolate tracks during composition

5. **One-Click Play** — Synthesize and download WAV/MIDI instantly

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

### Pattern → Base

Generate bass lines that follow a specific ordered pattern! Unlike AI Fill Bass (which extracts arbitrary low notes from donors), Pattern → Base constrains the bass to follow your digit sequence in order.

**Example workflow:**
1. Enter pattern: `3-1-4-1-5` (Pi digits)
2. Choose mode:
   - **Offset**: Each digit + offset (e.g., 3+10=13, 1+10=11, 4+10=14...)
   - **Tonic+Scale**: Map digits to scale degrees in bass octave (e.g., tonic E0=16, chromatic)
3. Set bass range: min=28 (E1), max=42 (F#2)
4. Select style MIDIs (Chopin + Liszt) for duration learning
5. Generate → Creates Base track with pattern `13-11-14-11-15` and learned rhythms

**Use cases:**
- Pi bass: `3-1-4-1-5-9-2-6-5-3-5-8-9-7-9`
- Fibonacci bass: `1-1-2-3-5-8`
- Custom sequences: `5-3-1-2-4-6-5-3`

The AI assigns durations based on the jump patterns in your style MIDIs, creating a musically flowing bass line that follows your exact pitch sequence.

### Fill Base from Solo

Evolve your cluster/pattern notes into an **ordered Base fill under a Solo** track! This feature takes an existing Solo track and generates a harmonized bass line from your pattern, with AI-powered offset selection and timing that matches the Solo's span.

**Example workflow:**
1. Generate a Solo track first (use Number Melody)
2. Open the "Fill Base from Solo" expander
3. Enter pattern: `3-1-4-1-5` (Pi digits)
4. Choose offset mode:
   - **Auto from Solo**: AI picks offset to harmonize with Solo pitch classes (avoids clashes, maximizes consonance)
   - **Manual**: Specify offset manually
5. Set bass range: min=28 (E1), max=42 (F#2)
6. Select style MIDIs for duration learning (optional)
7. Generate → Creates Base track harmonized under Solo with pattern timing stretched/looped to match Solo span

**Key features:**
- **Auto-harmonization**: AI analyzes Solo pitch classes and chooses offset for best consonance (unison, thirds, fourths, fifths)
- **Register optimization**: Keeps bass in target range under Solo
- **Timing sync**: Pattern loops or stretches to fill Solo span
- **Piano FX defaults**: Base track uses intensity=2.0, hold=2.0 for rich bass tone

**Use cases:**
- Pi melody + Pi bass harmonized: Solo from Pi → Base from same Pi pattern auto-harmonized
- Custom melody + Fibonacci bass: Solo (any) → Base from Fibonacci sequence `1-1-2-3-5-8`
- Experimentation: Try different patterns under same Solo to find best harmony

### AI Track Generation

Generate new tracks using **Phase 1 heuristic patterns** from existing tracks:
- **Bass Line** (keys 1-28): Extracts lowest notes (arbitrary, not pattern-ordered)
- **Chord Base** (keys 29-52): Extracts note clusters/chords
- **Adorn Pluck** (keys 45-72): Creates sparse decorative patterns
- **Harmony Line** (keys 45-72): Harmonizes melody with interval transposition

AI tracks are generated from other tracks in the song and automatically assigned role names (Base/Adorn).

**Note:** AI Fill Bass extracts existing low notes from donors. For ordered bass patterns following a specific digit sequence, use **Pattern → Base** instead.

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
2. **Add Pattern Bass** (optional): Enter "3-1-4-1-5", set offset/range, select styles, generate ordered bass
3. **Add AI tracks**: Click "Bass Line" (arbitrary) or "Chord Base" for accompaniment
4. **Edit notes**: Use cluster badges to edit keys and durations, or paste cluster strings
5. **Adjust FX**: Set intensity (1.0-2.0), enable delay, adjust hold duration
6. Click "▶ Play" to synthesize and hear the music
7. Download as WAV or MIDI

### Cluster Badge Editor

The **Cluster Badge Editor** provides an intuitive way to edit notes as time-slot clusters:

- Each **badge** represents simultaneous keys (chord or single note) + a duration chip (1/4, 1/2, 1, 2... beats)
- **Edit keys** directly in the badge text (comma-separated)
- **Change duration** via dropdown (common fractions displayed as 1/4, 1/2, etc.)
- **Insert** new clusters between existing ones with the ➕ button
- **Delete** clusters with the 🗑️ button
- **Paste cluster strings** for quick entry: `35-35,36-38-35`

**Paste Syntax:**
- Dash (`-`) separates sequential clusters
- Comma (`,`) separates keys within a cluster (simultaneous notes)
- Example: `35-35,36-38-35` creates four clusters:
  1. Key 35
  2. Keys 35 and 36 together
  3. Key 38
  4. Key 35
- Default duration: 1/2 beat (customizable before paste)

**Advanced Table Editor** is still available in an expander for precise timing and velocity control.

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
