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

#### Chunking Modes (Phase 1.1)

**single mode** (original):
- Each digit 0-9 maps directly to a scale degree
- Limited pitch variation (only 10 distinct values)

**pair_mod mode** (recommended, new default):
- Consecutive digit pairs treated as 00-99
- Apply modulus: `value % modulus` → pitch steps
- **Much richer variation** (up to `modulus` distinct values)
- Odd trailing digit handled alone

**Modulus values**:
- **12** (recommended): Chromatic offsets from tonic (full 12-tone range)
- **7**: Diatonic scale degrees (major/minor scale)
- **5**: Pentatonic degrees

**Example — Pi digits with pair_mod, modulus=12**:
```
Digits:  3 1 4 1 5 9 2 6 5 3 5 8
Pairs:   31     41     59     26     53     58
Mod 12:   7      5     11      2      5     10
→ Chromatic offsets from tonic: G, F, B, D, F, A#
```

**Modes supported**:
- **Major**: 0→1→2→3→4→5→6→7→8→9 maps to C D E F G A B C D E
- **Natural Minor**: A B C D E F G A B C
- **Pentatonic Major**: C D E G A C D E G A
- **Pentatonic Minor**: A C D E G A C D E G
- **Chromatic**: All 12 semitones (0→tonic, 11→tonic+11)

**Register Control**:
- `max_key` parameter caps highest note (default: ~64 for comfortable listening)
- `min_key` parameter sets lowest note (default: tonic)
- `octave_range` controls vertical span (basic mode)
- Prevents occasional "bursts" of very high notes

**Mapping logic (basic mode, pair_mod + modulus=12)**:
```python
# For each digit pair 00-99:
pair_value = digit1 * 10 + digit2
chromatic_offset = pair_value % 12  # 0-11
octave_offset = (chromatic_offset // 12) % octave_range
key = tonic + chromatic_offset + octave_offset * 12
key = min(key, max_key)  # Clamp to comfortable register
```

#### Jump Prediction Register Mode (Phase 2.0)

**Problem**: The basic mapping algorithm sometimes limits octave spanning because the octave is determined mechanically. For example, with modulus=12, all values 0-11 map to one octave, 12-23 to another, etc. This can prevent the melody from using the full [min_key, max_key] range in a musically natural way.

**Solution**: `jump_predict` register mode uses **octave disambiguation via jump likelihood**.

**How it works**:
1. **Digits → Pitch Classes**: Same as basic mode (pair_mod % 12 → PC 0-11)
2. **Find Candidates**: For each target pitch class, find ALL keys in [min_key, max_key] with that PC
3. **Pick Best Jump**: Use a jump histogram learned from style MIDIs to pick the jump with highest likelihood
4. **Duration Model**: Unchanged, still learned from style MIDIs

**Example — PC 3 to PC 7**:
```
Previous key: 40 (E)
Target pitch class: 7 (G)
Candidates in [28, 64]: 31 (G, jump=-9), 43 (G, jump=+3), 55 (G, jump=+15)

If style MIDIs prefer small intervals:
  → Pick 43 (jump=+3)

If style MIDIs prefer downward leaps:
  → Pick 31 (jump=-9)

If style MIDIs prefer large upward intervals:
  → Pick 55 (jump=+15)
```

**When to use**:
- Multi-style training with diverse classical MIDIs (Chopin, Liszt, Scarlatti)
- Want melody to span multiple octaves based on style's natural melodic motion
- Working with wide [min_key, max_key] range (e.g. 28-64, spanning 3 octaves)

**CLI Usage**:
```bash
python number_melody.py \
  --digits 314159265358979323846 \
  --tonic 40 \
  --chunk pair_mod \
  --modulus 12 \
  --register jump_predict \
  --min-key 28 \
  --max-key 64 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --style demos/scarlatti-sonata.mid \
  --out pi_jump_predict.mid \
  --bpm 96
```

**Studio UI**:
1. Select "Register / Registro": **jump_predict**
2. Set Min Key: **28** (E1, bass range start)
3. Set Max Key: **64** (E4, comfortable treble)
4. Select multiple style MIDIs for rich jump statistics
5. Generate — melody will span multiple octaves based on learned jump preferences

**Technical Details**:
- Jump model: `Dict[int, int]` mapping signed jump (semitones) to count
- Clamped to ±24 semitones (±2 octaves) for melodic realism
- Tiebreaker: Prefer smaller absolute jumps for equal counts (more melodic)
- First note: Always uses tonic

---

### 2. Duration Model: Jump-Conditioned Histograms (Multi-Style)

**Problem**: Raw note sequence has no rhythm. We need to predict duration for each note.

**Approach (Phase 1 — Practical Statistical Model)**:

For each consecutive note pair in the digit melody:
1. Compute **jump** (interval): `Δkey = key[i] - key[i-1]`
2. Look up P(duration | jump) from style MIDIs
3. Quantize duration to musical grid (0.25, 0.5, 1.0, 2.0 beats)

**Training (Multi-Style Support)**:
- Load **multiple style MIDIs** and merge their tracks
- For each note pair `(n_prev, n_curr)` across all style tracks:
  - `jump = n_curr.key - n_prev.key`
  - `duration = n_curr.duration_beats`
  - Record `(jump, duration)` in histogram
- Build conditional distribution: `P(duration_bin | jump)`
- **Richer patterns** from diverse styles (Romantic + Jazz + Classical)

**Prediction**:
- For each note in digit melody, given previous note:
  - `jump = current_key - prev_key`
  - Sample duration from `P(duration | jump)` (use mode/median/random)
  - Clamp duration to [0.25, 4.0] beats
  - Assign to note

**Fallback**:
- If jump not seen in style, use default duration (0.5 beats)

**BPM Guidance**:
- Default BPM: **96** (calmer feel than original 120)
- User can override for specific tempo preferences

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
    bpm: float = 96.0,
    octave_range: int = 2,
    chunk_mode: str = "pair_mod",
    modulus: int = 12,
    min_key: Optional[int] = None,
    max_key: Optional[int] = None,
    register_mode: str = "basic",
    modulus: int = 12,
    max_key: Optional[int] = None,
    duration_strategy: Literal["mode", "median", "random"] = "mode"
) -> Track:
    """
    Generate melody track from digit string.
    
    New defaults (Phase 1.1):
        bpm=96 (calmer tempo)
        chunk_mode="pair_mod" (richer variation)
        modulus=12 (chromatic)
        max_key=None (auto, typically ~64)
    
    Returns:
        Generated melody Track
    """
```

---

## CLI Smoke Test

**Multi-style with pair_mod (recommended)**:
```bash
python3 number_melody.py \
  --digits 314159265358979323846 \
  --tonic 40 \
  --chunk pair_mod \
  --modulus 12 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --style demos/scarlatti-sonata.mid \
  --out /tmp/pi_multi.mid \
  --bpm 96 \
  --max-key 60
```

**Single digit mode (original)**:
```bash
python3 number_melody.py \
  --digits 112358132134 \
  --tonic 48 \
  --mode pentatonic_minor \
  --chunk single \
  --style demos/chopin-etude.mid \
  --out /tmp/fibonacci.mid \
  --bpm 90
```

**Jump prediction mode (octave disambiguation)**:
```bash
python3 number_melody.py \
  --digits 314159265358979323846 \
  --tonic 40 \
  --chunk pair_mod \
  --modulus 12 \
  --register jump_predict \
  --min-key 28 \
  --max-key 64 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --style demos/scarlatti-sonata.mid \
  --out /tmp/pi_jump_predict.mid \
  --bpm 96
```

**Expected**: MIDI files with melodies having varied durations learned from style patterns. Jump prediction mode should produce melodies that span multiple octaves within [min_key, max_key] based on the style's natural melodic motion.

---

## UI Integration (Streamlit)

Add panel in `app.py`:

**"Number Melody" Section**:
- Text area: Paste digit string
- **Chunk mode selector**: pair_mod (default) or single
- **Modulus input**: 12 (chromatic), 7 (diatonic), 5 (pentatonic)
- **Register mode selector**: basic (original) or jump_predict (octave disambiguation)
- Number input: Tonic (1-88, default 40 for lower register)
- Dropdown: Mode (major, minor, pentatonic_major, pentatonic_minor, chromatic)
- **Number input: Min key (default 28 for bass range start)**
- **Number input: Max key (default 64 for comfortable register)**
- Number input: Octave range (1-4, default 2, used in basic mode)
- **Multi-select: Style MIDI demos (select multiple for richer patterns)**
- Radio: Duration strategy (mode, median, random)
- **Number input: BPM override (default 96 for calmer tempo)**
- Button: "Generate Melody"

**On Generate**:
- Load multiple style MIDIs and merge all tracks
- Call `generate_number_melody(chunk_mode="pair_mod", modulus=12, register_mode=..., min_key=..., max_key=..., ...)`
- Add generated track to session with BPM override
- Display key range and note count
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
