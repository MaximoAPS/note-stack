# Mood FX Chain Implementation Summary

## ✅ Completed Tasks

### 1. Audio FX Engine (audio_fx.py)
- **Created** comprehensive audio FX module using `pedalboard` library
- **Implemented effects:**
  - Distortion: Drive (0-30dB), mix
  - Chorus: Rate, depth, center delay, feedback, mix
  - Tremolo: Rate, depth (manual implementation)
  - Flanger: Rate, depth, center delay, feedback, mix (using Chorus)
  - Wah (Phaser): Rate, depth, center frequency, feedback, mix
  - Pitch Shift: Semitones (-12 to +12), mix
- **Features:**
  - Dry/wet mixing per effect
  - Stackable effects (order matters)
  - Graceful error handling (fallback to dry signal)
  - Musical defaults via `create_default_effect()`

### 2. Data Model Updates (notes.py)
- Added `audio_fx: List[Any]` field to Track dataclass
- Effects stored as list of AudioEffect objects
- Preserves backward compatibility (default empty list)

### 3. Synthesis Pipeline (synth.py)
- Updated `synthesize_track()` to apply FX chain post-synth
- FX applied AFTER piano synthesis, BEFORE song mix
- Desmos formulas completely unchanged:
  - Intensity (harmonic_intensity)
  - Box-Muller decay
  - Time warp envelope
  - Key-dependent decay scaling
  - High-key harmonic rolloff

### 4. UI Updates (app.py)
- **Separated Synth Params vs Audio FX sections:**
  - **Synth Params**: Intensity/Delay/Hold (piano synthesis controls)
  - **Audio FX**: Post-synth mood effects (stackable)
- **New FX UI:**
  - Dropdown selector for mood effects
  - "Agregar efecto" button adds to chain
  - Each effect shows configurable parameters
  - Remove button (🗑️) per effect
  - Visual chain display showing effect order
- **All width='stretch'** constraints maintained
- **Unique keys** for all widgets

### 5. Testing
- Created `test_mood_fx.py` demonstrating:
  - Clean baseline
  - Single effect (Distortion)
  - Stacked chain (Distortion + Chorus)
- Successfully exported test WAV files
- Verified peak normalization intact (0.89 max)

## 🎯 User Requirements Met

✅ **Post-synth dry/wet FX chain** for mood/character  
✅ **Distortion, Chorus, Tremolo, Flanger, Wah, Pitch** implemented  
✅ **Stackable effects** (order matters: synth → FX chain)  
✅ **Per-track "Agregar efecto"** with mood FX list  
✅ **Multiple effects** with individual params and remove buttons  
✅ **Synth params (Intensity/Delay/Hold)** preserved and separated  
✅ **Desmos piano formulas unchanged**  
✅ **No loudness changes** (peak normalize at 0.89 retained)  

## 📦 Dependencies Added
- `pedalboard` - Production-quality audio DSP library (Spotify's library)

## 🎵 How It Works

1. **Synthesis Phase**: Piano notes synthesized using Desmos formulas
2. **FX Chain Phase**: Post-synth effects applied in order:
   ```
   Piano Synth → [FX 1] → [FX 2] → ... → [FX N] → Track Output
   ```
3. **Mix Phase**: All tracks mixed to stereo with Haas effect
4. **Normalize Phase**: Peak normalize to 0.89 (unchanged)

## 🎨 Example Usage

```python
# In Streamlit UI:
# 1. Create/load a track
# 2. Scroll to "Audio FX" section
# 3. Select "Distortion" → Click "Agregar efecto"
# 4. Adjust Drive: 15 dB, Mix: 0.4
# 5. Select "Chorus" → Click "Agregar efecto" (stacks after distortion)
# 6. Adjust Rate: 1.5 Hz, Depth: 0.4, Mix: 0.5
# 7. Play or export to hear acoustic → gritty chorus character
```

## 🔊 Technical Details

### Effect Processing
- Each effect operates on mono signal (per track)
- Normalized to prevent clipping through FX chain
- Dry/wet mixing done per effect
- Original peak scaling restored after FX chain

### Effect Types
- **Distortion**: Waveshaping for grit/aggression
- **Chorus**: Modulated delay for thickness/shimmer
- **Tremolo**: Amplitude modulation for pulsing
- **Flanger**: Short modulated delay for jet/whoosh
- **Wah/Phaser**: Sweeping filter for vowel-like tones
- **Pitch Shift**: Harmony/detuning for doubled effect

### Order Matters
Effects applied sequentially:
- `[Distortion → Chorus]` ≠ `[Chorus → Distortion]`
- Classic pedal chain: Pitch → Distortion → Modulation (Chorus/Flanger) → Time (Delay)

## ✨ Ready for Merge
- All code tested and working
- No breaking changes to existing functionality
- Backward compatible (empty audio_fx list = no FX)
- UI clearly separates synth params from audio FX
- Graceful degradation if pedalboard fails
