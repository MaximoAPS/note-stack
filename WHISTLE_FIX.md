# High Whistle Fix — Technical Notes

**PR**: https://github.com/MaximoAPS/note-stack/pull/14  
**Branch**: `cursor/fix-high-whistle-3eab`

## Problem

High-register notes exhibited piercing whistling artifacts despite existing `key_decay_scale`. Contributors:
- Per-track delay (0.4 gain) causing comb filtering on bright notes
- 64 harmonics too bright on high keys
- Master LP at 13 kHz too high

## Solution (3 Surgical Fixes)

All changes are **multiplicative filters** applied AFTER Desmos calculations. Core formulas untouched.

### 1. `high_key_harmonic_rolloff(key, harmonic_num)` → float
**Location**: `synth.py:29-46`  
**Applied**: In `synthesize_note()` at line 228

```python
harm_intensity *= high_key_harmonic_rolloff(key, H)
```

**Behavior**:
- Keys ≤55 (G4): Returns 1.0 (no change)
- Keys >55: Progressive attenuation of higher harmonics
- Formula: `1.0 - (key_excess * harmonic_excess * 0.0015)`
- Clipped to 0.5 minimum (max 50% reduction)
- At key 72 (C5), harmonics 32+ reduced by ~30-50%

### 2. `key_delay_gain(key)` → float
**Location**: `synth.py:59-72`  
**Applied**: In `synthesize_track()` at line 299

```python
delay_gain = key_delay_gain(note.key)
if delay_start < num_samples and delay_gain > 0:
    delay_signal = note_signal * delay_gain
```

**Behavior**:
- Keys ≤55: Returns 0.4 (full delay, unchanged)
- Keys 55-68: Linear fade from 0.4 → 0
- Keys ≥68 (G#5): Returns 0.0 (no delay)
- Prevents comb filtering on bright high notes

### 3. Adaptive Master Lowpass
**Location**: `synth.py:354-363`  
**Applied**: In `synthesize_song()` before master filter

```python
if max_key_in_song >= 60:
    cutoff_reduction = min(2000, (max_key_in_song - 60) * 100)
    master_cutoff = 13000 - cutoff_reduction
else:
    master_cutoff = 13000
```

**Behavior**:
- Detects highest key in entire song
- Keys <60: 13 kHz cutoff (unchanged)
- Keys 60+: Reduce by 100 Hz per key
- Capped at -2 kHz (11 kHz minimum)
- Example: key 72 → 13000 - 1200 = 11800 Hz

## Desmos Formulas Preserved

✅ **Unchanged core formulas:**
- `harmonic_intensity(h) = 1 / (1.24729 * h^1.5 + 1)`
- Attack polynomial (0.05 → 0.172s)
- Box-Muller decay (`mean=10.2, std=3.54`)
- Time warp freeze (0.34s to `d`)

All fixes are **post-multiplication** or **gain scaling** only.

## Testing

### Automated Verification
```bash
# Verify synth still works
$ python3 check_synth.py
✓ Synthesis test passed!

# Generate high-register test audio
$ python3 test_high_whistle.py
✓ Saved to test_high_whistle.wav
```

### Manual Testing
1. **High register with delay**:
   - Create track with keys 60-72, enable delay
   - Apply, Play → should be smooth, no piercing
   
2. **Low register verification**:
   - Create track with keys 20-40, enable delay
   - Apply, Play → should ring naturally, full delay preserved

3. **Mixed content**:
   - Bass (keys 28-42) + melody (keys 60-72)
   - Bass should have full delay, highs reduced delay

## Code Changes Summary

### `synth.py` (128 additions, 6 deletions)

**New functions:**
1. `high_key_harmonic_rolloff(key, harmonic_num)` — lines 29-46
2. `key_delay_gain(key)` — lines 59-72

**Modified functions:**
1. `synthesize_note()` — line 228: Apply harmonic rolloff
2. `synthesize_track()` — lines 291-307: Key-scaled delay gain
3. `synthesize_song()` — lines 338-363: Track max key, adaptive LP

**Documentation:**
- Module docstring updated with recent changes (lines 1-8)

### `test_high_whistle.py` (new file, 52 lines)
Creates dense high-register test passage:
- Keys 60-72 (C4 to C5)
- Delay enabled
- Rapid ascending/descending pattern
- Outputs `test_high_whistle.wav`

## Performance

✅ **No performance regression:**
- Still uses vectorized envelope
- Rolloff/delay scaling are O(1) per harmonic/note
- Adaptive LP detection is O(notes) — negligible

## Key Thresholds Reference

| Key | Note | Rolloff Starts | Delay Fade | Full Cutoff Reduction |
|-----|------|----------------|------------|----------------------|
| 55  | G4   | 1.0 (none)     | 0.4 (full) | 0 Hz                 |
| 60  | C5   | Active         | 0.31       | -100 Hz              |
| 65  | F5   | Active         | 0.16       | -500 Hz              |
| 68  | G#5  | Active         | 0.0 (off)  | -800 Hz              |
| 72  | C6   | Strong         | 0.0        | -1200 Hz             |

## Next Steps

1. Merge PR #14 when approved
2. Test with real compositions containing high register passages
3. If highs still whistle: consider reducing rolloff threshold from 55 → 52
4. If lows sound too dark: increase adaptive LP threshold from 60 → 65

---

**Note**: All changes preserve Desmos core synthesis model. Can be reverted independently if needed.
