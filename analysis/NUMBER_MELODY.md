# Number Melody — Digits to Pitched Melody with Learned Durations

## Product Vision

**Number Melody** transforms numeric sequences (like digits of Pi, Fibonacci, dates, or any number string) into expressive melodies with intelligent rhythm. This feature combines:
- **Deterministic pitch mapping** (digits → piano keys via scale/mode)
- **Statistical duration modeling** (learned from style MIDIs)
- **Integration with existing adorn** (melody becomes Solo track for jump_adorn)

### Example User Story

1. User pastes digits of Pi: `314159265358979323846...`
2. Sets tuning: C major, tonic=48 (middle C), octave range 2
3. Loads style MIDI(s): Joplin "The Entertainer", Albéniz "Asturias"
4. System learns duration patterns from jumps (interval transitions) in style
5. Output: Solo track with musically sensible durations
6. User adorns melody with existing pattern generators

---

## Technical Design

### 1. Pitch Mapping: Digits → Keys

**Modes supported (Phase 1)**:
- **Major**: 0→1→2→3→4→5→6→7→8→9 maps to C D E F G A B C D E
- **Natural Minor**: A B C D E F G A B C
- **Pentatonic Major**: C D E G A C D E G A
- **Pentatonic Minor**: A C D E G A C D E G
- **Chromatic**: All 12 semitones (0→tonic, 9→tonic+9)

**Octave wrapping**:
```python
scale_degrees = mode_intervals[digit]  # e.g. [0,2,4,5,7,9,11] for major
pitch_class = scale_degrees[digit % len(scale_degrees)]
octave_offset = (digit // len(scale_degrees)) % octave_range
key = tonic + pitch_class + octave_offset * 12
```

**Custom maps** (Phase 2): User can define arbitrary digit→key mappings.

---

### 2. Duration Model: Jump-Conditioned Histograms

**Problem**: Raw note sequence has no rhythm. We need to predict duration for each note.

**Approach (Phase 1 — Practical Statistical Model)**:

For each consecutive note pair in the digit melody:
1. Compute **jump** (interval): `Δkey = key[i] - key[i-1]`
2. Look up P(duration | jump) from style MIDIs
3. Quantize duration to musical grid (0.25, 0.5, 1.0, 2.0 beats)

**Training**:
- Load style MIDI(s) as `mashup_source` tracks
- For each note pair `(n_prev, n_curr)` in style:
  - `jump = n_curr.key - n_prev.key`
  - `duration = n_curr.duration_beats`
  - Record `(jump, duration)` in histogram
- Build conditional distribution: `P(duration_bin | jump)`
- Optional: smooth with context (last k jumps)

**Prediction**:
- For each note in digit melody, given previous note:
  - `jump = current_key - prev_key`
  - Sample duration from `P(duration | jump)` (or use mode/median)
  - Clamp duration to [0.25, 4.0] beats
  - Assign to note

**Fallback**:
- If jump not seen in style, use nearest jump or global duration mode (0.5 beats)

---

### 3. Integration with Existing Adorn (Future)

Once the Number Melody track is generated, user can:
- Mark it as Solo track in Editor
- Mark style MIDIs as `mashup_source`
- Run `jump_adorn` (when implemented) to add bass/chords/plucks around the melody

Phase 1 outputs the melody track ready for manual editing or existing pattern generators.

---

## Phase 1 Implementation

**Module**: `number_melody.py`

### Functions

```python
def parse_digit_string(s: str) -> List[int]:
    """Extract digits 0-9 from string, ignore separators."""
    return [int(c) for c in s if c.isdigit()]

def map_digits_to_keys(
    digits: List[int],
    tonic: int,
    mode: Literal["major", "minor", "pentatonic_major", "pentatonic_minor", "chromatic"],
    octave_range: int = 2
) -> List[int]:
    """Map digits to piano keys using scale/mode."""
    # Returns list of piano keys (1-88)
    pass

def build_duration_model(
    style_tracks: List[Track]
) -> Dict[int, List[float]]:
    """
    Build P(duration | jump) from style tracks.
    
    Returns:
        jump_durations: Dict[jump_semitones] -> List[durations in beats]
    """
    # For each note pair in style tracks, record (jump, duration)
    pass

def predict_durations(
    keys: List[int],
    duration_model: Dict[int, List[float]],
    default_duration: float = 0.5
) -> List[float]:
    """
    Predict duration for each note given previous key jump.
    
    Args:
        keys: Piano keys for melody
        duration_model: Jump -> durations histogram
        default_duration: Fallback if jump not in model
    
    Returns:
        List of durations (in beats)
    """
    # For each key, compute jump from previous, sample duration
    pass

def generate_number_melody(
    digit_string: str,
    tonic: int,
    mode: str,
    style_tracks: List[Track],
    bpm: float = 120.0,
    octave_range: int = 2,
    duration_strategy: Literal["mode", "median", "random"] = "mode"
) -> Track:
    """
    Generate melody track from digit string.
    
    Args:
        digit_string: String with digits (e.g. "314159265358979")
        tonic: Root key (e.g. 48 for middle C)
        mode: Scale mode (major, minor, pentatonic_major, etc.)
        style_tracks: Tracks to learn durations from
        bpm: Tempo
        octave_range: How many octaves to span
        duration_strategy: How to pick duration from histogram (mode/median/random)
    
    Returns:
        Generated melody Track
    """
    # 1. Parse digits
    # 2. Map to keys
    # 3. Build duration model from style tracks
    # 4. Predict durations
    # 5. Create Note objects at cumulative start times
    # 6. Return Track with name "Number Melody (Pi)" etc.
    pass
```

---

## CLI Smoke Test

```bash
python number_melody.py \
  --digits 314159265358979323846 \
  --tonic 48 \
  --mode major \
  --style demos/joplin-entertainer.mid \
  --out /tmp/pi_melody.mid \
  --bpm 120
```

**Expected**: `/tmp/pi_melody.mid` contains melody track with varied durations.

---

## UI Integration (Streamlit)

Add panel in `app.py`:

**"Number Melody" Section**:
- Text area: Paste digit string
- Number input: Tonic (1-88, default 48)
- Dropdown: Mode (major, minor, pentatonic_major, pentatonic_minor, chromatic)
- Number input: Octave range (1-4, default 2)
- MIDI uploader: Style MIDI(s) or dropdown from demos
- Radio: Duration strategy (mode, median, random)
- Button: "Generate Melody"

**On Generate**:
- Load style MIDI(s) as Track list
- Call `generate_number_melody()`
- Add generated track to session
- Display success + timeline preview
- Button: "Adorn this melody" (if editor_session + pattern_generators available)

---

## Phase 2+ Roadmap (Document Only)

### Deep Learning Duration Model

**Architecture**:
- **Input**: Jump sequence embeddings (last k jumps)
- **CNN**: Local patches (±2 beat context) for rhythm patterns
- **Transformer (GPT-2 style)**: Sequence modeling for longer dependencies
- **Output**: Duration distribution (categorical over {0.25, 0.5, 1.0, 2.0, 4.0})

**Training**:
- Collect jump→duration sequences from MAESTRO + user style packs
- Train on millions of note transitions
- Fine-tune per style pack (Romantic vs Jazz vs Pop)

### Multi-Digit Chunking

- Base-N encodings: Treat digit pairs/triples as larger alphabet
- Richer pitch space: 100 symbols → more expressive mappings

### Rhythm Templates

- Learn bar-level rhythm patterns from style (not just note-to-note)
- Apply rhythm template to digit melody (quantize to bar structure)

### Integration with Jump Adorn

- Once `jump_adorn` is implemented (mentioned in editor-ui-phase1):
  - Number Melody generates Solo track
  - User marks style MIDIs as `mashup_source`
  - `jump_adorn` generates bass/chords/decoration around Solo

---

## Success Criteria

✅ **Phase 1 Usable**:
- User can paste Pi digits, set tuning, pick style MIDI
- System generates melody track with non-uniform durations learned from style
- CLI smoke test passes
- UI panel works in Streamlit
- Melody loads into session as playable track
- Documentation complete (EN + ES)
- PR opened

---

## References

- **IntervalEmbedder** (future): Jump token embeddings for deep model
- **jump_adorn** (future): Adorn melody with bass/chords conditioned on jump patterns
- **Editor Session** (cursor/editor-ui-phase1-1259): Track roles, mashup_source workflow
- **MAESTRO Dataset**: https://magenta.tensorflow.org/datasets/maestro

---

**Author**: Cloud Agent + Maximo  
**Date**: Sep 2026  
**Version**: 1.0 (Phase 1 Statistical Duration Model)
