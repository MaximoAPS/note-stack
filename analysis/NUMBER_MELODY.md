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
- `octave_range` controls vertical span (only in fixed mode)
- Prevents occasional "bursts" of very high notes

**Mapping logic (pair_mod + modulus=12, fixed mode)**:
```python
# For each digit pair 00-99:
pair_value = digit1 * 10 + digit2
chromatic_offset = pair_value % 12  # 0-11
octave_offset = (chromatic_offset // 12) % octave_range
key = tonic + chromatic_offset + octave_offset * 12
key = min(key, max_key)  # Clamp to comfortable register
```

---

#### Octave Disambiguation (Phase 1.5 — Jump Predict Mode)

**Problem**: Fixed mode maps pitch classes to a small register (typically 2 octaves). Real melodies roam the full keyboard.

**Solution — Jump Predict Mode** (`--octave-mode jump_predict`):

1. **Digits → Pitch Classes**: Pair_mod with modulus 12 gives pitch classes 0-11 (C, C♯, D, ..., B)
2. **Octave Ambiguity**: Pitch class 3 (E♭) could be key 27, 39, 51, 63, 75... (E♭ in different octaves)
3. **Jump Model**: Learn `P(Δkey | pitch_class_delta)` from style MIDIs
   - For each consecutive note pair in style, record: pitch class delta (mod 12) → actual signed jump
   - Example: PC delta 4 (major third) might be +4 semitones (up), -8 (down sixth), +16 (compound third)
4. **Resolution**: For each next pitch class, pick the absolute key (octave) that gives the most probable jump from previous key

**Example — Pi digits with jump_predict**:
```
Digits:      3 1 4 1 5 9 2 6 5
Pairs:      31    41    59    26    5 (odd)
Mod 12:      7     5    11     2    5
PCs:        G     F     B     D    F

Fixed mode (tonic=48, octave_range=2):
  Keys: 55, 53, 59, 50, 53  (all within ~1 octave, predictable)

Jump predict mode (min_key=28, max_key=72, Chopin+Liszt style):
  Candidates for each PC:
    G: [31, 43, 55, 67]  → pick 55 (start near tonic)
    F: [29, 41, 53, 65]  → pick 53 (−2 semitones, common in style)
    B: [35, 47, 59, 71]  → pick 59 (+6, fourth up, very common)
    D: [26, 38, 50, 62]  → pick 50 (−9, down sixth, style shows composers drop after high note)
    F: [29, 41, 53, 65]  → pick 53 (+3, small upward recovery)
  
  Keys: 55, 53, 59, 50, 53  (spans 28-72 range naturally, follows style jump patterns)
```

**Why This Works**:
- Romantic piano (Chopin, Liszt) uses rich jump vocabulary: small steps, fourths, sixths, octaves
- Jump model captures these preferences: after going up high, composers often drop down
- Melody follows digit pitch classes **exactly** (mod 12) but octave choices are musical

**CLI Example**:
```bash
python number_melody.py --digits 314159265358979 --tonic 48 \
  --chunk pair_mod --modulus 12 --octave-mode jump_predict \
  --min-key 28 --max-key 72 \
  --style demos/chopin-etude.mid --style demos/liszt-preludio.mid \
  --out pi_jump.mid --bpm 96
```

**Parameters**:
- `--octave-mode jump_predict` (new, default: `fixed`)
- `--min-key 28` (E below bass staff, default for jump_predict)
- `--max-key 72` (C above treble staff, default for jump_predict)

**When to Use Jump Predict**:
- Want melody to span full keyboard range
- Have rich style MIDIs with varied melodic motion (Romantic piano, Baroque, Jazz)
- Pair_mod with modulus=12 for chromatic pitch classes

**When to Use Fixed Mode**:
- Simpler, more predictable output
- Tighter register control with `octave_range`
- Legacy compatibility

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

def build_jump_model(
    style_tracks: List[Track]
) -> Dict[int, List[int]]:
    """
    Build P(jump | pitch_class_delta) from style tracks.
    Returns: Dict[pc_delta] -> List[signed_jumps]
    """

def resolve_keys_by_jump(
    pitch_classes: List[int],
    style_tracks: List[Track],
    min_key: int = 28,
    max_key: int = 72,
    start_key: Optional[int] = None,
    modulus: int = 12
) -> List[int]:
    """
    Resolve pitch classes to absolute keys using jump prediction.
    Core octave disambiguation algorithm.
    """

def generate_number_melody(
    digit_string: str,
    tonic: int,
    mode: str,
    style_tracks: List[Track],
    bpm: float = 96.0,
    octave_range: int = 2,
    chunk_mode: str = "pair_mod",
    modulus: int = 12,
    max_key: Optional[int] = None,
    min_key: Optional[int] = None,
    octave_mode: Literal["fixed", "jump_predict"] = "fixed",
    duration_strategy: Literal["mode", "median", "random"] = "mode"
) -> Track:
    """
    Generate melody track from digit string.
    
    New defaults (Phase 1.5):
        bpm=96 (calmer tempo)
        chunk_mode="pair_mod" (richer variation)
        modulus=12 (chromatic)
        octave_mode="fixed" (original), or "jump_predict" (new!)
        max_key=None (auto: ~64 for fixed, ~72 for jump_predict)
        min_key=None (auto: ~28 for jump_predict)
    
    Returns:
        Generated melody Track
    """
```

---

## CLI Smoke Test

**Jump predict mode (new! recommended for full keyboard)**:
```bash
python3 number_melody.py \
  --digits 314159265358979323846 \
  --tonic 48 \
  --chunk pair_mod \
  --modulus 12 \
  --octave-mode jump_predict \
  --min-key 28 \
  --max-key 72 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --style demos/scarlatti-sonata.mid \
  --out /tmp/pi_jump.mid \
  --bpm 96
```

**Multi-style with pair_mod (fixed mode)**:
```bash
python3 number_melody.py \
  --digits 314159265358979323846 \
  --tonic 40 \
  --chunk pair_mod \
  --modulus 12 \
  --octave-mode fixed \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --style demos/scarlatti-sonata.mid \
  --out /tmp/pi_fixed.mid \
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

**Expected**: 
- Jump predict: Melody spans full min/max range, octave choices follow style jump preferences
- Fixed: Melody stays in narrow register, deterministic octave mapping
- All: Varied durations learned from style patterns

---

## UI Integration (Streamlit)

Add panel in `app.py`:

**"Number Melody" Section**:
- Text area: Paste digit string
- **Chunk mode selector**: pair_mod (default) or single
- **Modulus input**: 12 (chromatic), 7 (diatonic), 5 (pentatonic)
- Number input: Tonic (1-88, default 40 for lower register)
- Dropdown: Mode (major, minor, pentatonic_major, pentatonic_minor, chromatic)
- **Radio: Octave mode** (fixed, jump_predict) — NEW!
- Number input: Octave range (1-4, default 2, only for fixed mode)
- **Number input: Min key** (default 28 for jump_predict) — NEW!
- **Number input: Max key** (default 64 for fixed, 72 for jump_predict)
- **Multi-select: Style MIDI demos** (select multiple for richer patterns)
- Radio: Duration strategy (mode, median, random)
- **Number input: BPM override** (default 96 for calmer tempo)
- Button: "Generate Melody"

**On Generate**:
- Load multiple style MIDIs and merge all tracks
- Call `generate_number_melody(chunk_mode="pair_mod", modulus=12, octave_mode="jump_predict", ...)`
- Add generated track to session with BPM override
- Display key range and note count
- Button: "Adorn this melody" (if editor_session + pattern_generators available)

---

## Phase 2+ Roadmap (Document Only)

### Deep Learning Jump+Duration Model

**Architecture**:
- **Input**: Pitch class sequence + jump history embeddings
- **CNN**: Local patches (±2 beat context) for rhythm patterns
- **Transformer (GPT-2 style)**: Sequence modeling for longer dependencies
- **Output**: Joint distribution over (jump, duration) pairs

**Training**:
- Collect (pitch_class, jump, duration) sequences from MAESTRO + user style packs
- Train on millions of note transitions
- Fine-tune per style pack (Romantic vs Jazz vs Pop)

**Note**: Phase 1.5 implements statistical jump model (histogram-based). Deep learning would improve:
- Context awareness (previous jumps influence next jump)
- Joint jump+duration modeling
- Style transfer quality

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

✅ **Phase 1.5 Octave Disambiguation**:
- Jump predict mode (`--octave-mode jump_predict`) implemented
- User can set min/max key for full keyboard range
- Jump model learns P(Δkey | pc_delta) from style MIDIs
- Pitch classes (mod 12) resolved to absolute keys via style-aware jump preferences
- Melody spans full keyboard naturally when style supports it
- CLI + UI support for octave mode selection
- Documentation updated with examples showing +4 vs −8 octave choices

---

## References

- **IntervalEmbedder** (future): Jump token embeddings for deep model
- **jump_adorn** (future): Adorn melody with bass/chords conditioned on jump patterns
- **Editor Session** (cursor/editor-ui-phase1-1259): Track roles, mashup_source workflow
- **MAESTRO Dataset**: https://magenta.tensorflow.org/datasets/maestro

---

**Author**: Cloud Agent + Maximo  
**Date**: Sep 2026  
**Version**: 1.5 (Phase 1.5 — Statistical Jump Model + Octave Disambiguation)
