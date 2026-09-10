"""Audio FX processors for mood/character effects.

Post-synth dry/wet FX chain applied per track after piano synthesis.
Supports: Distortion, Chorus, Tremolo, Flanger, Wah, Pitch Shift.
Uses pedalboard for maintained, production-quality DSP.
"""

from dataclasses import dataclass, field
from typing import List, Literal
import numpy as np

# Lazy import pedalboard to avoid startup overhead if not used
_pedalboard = None

def _get_pedalboard():
    """Lazy load pedalboard."""
    global _pedalboard
    if _pedalboard is None:
        import pedalboard
        _pedalboard = pedalboard
    return _pedalboard


@dataclass
class AudioEffect:
    """Base class for audio effects with dry/wet mix."""
    effect_type: str
    mix: float = 0.5  # Dry/wet mix (0=dry, 1=wet)


@dataclass
class Distortion(AudioEffect):
    """Distortion effect for grit and aggression."""
    effect_type: str = "distortion"
    drive_db: float = 10.0  # Drive in dB (0-30)
    mix: float = 0.5


@dataclass
class Chorus(AudioEffect):
    """Chorus effect for thickening and shimmer."""
    effect_type: str = "chorus"
    rate_hz: float = 1.0  # LFO rate in Hz (0.1-5)
    depth: float = 0.5  # Modulation depth (0-1)
    centre_delay_ms: float = 7.0  # Center delay in ms (1-20)
    feedback: float = 0.0  # Feedback amount (0-0.95)
    mix: float = 0.5


@dataclass
class Tremolo(AudioEffect):
    """Tremolo effect for amplitude modulation."""
    effect_type: str = "tremolo"
    rate_hz: float = 3.0  # LFO rate in Hz (0.1-20)
    depth: float = 0.5  # Modulation depth (0-1)
    mix: float = 1.0  # Usually 100% wet for tremolo


@dataclass
class Flanger(AudioEffect):
    """Flanger effect for jet/whoosh sounds."""
    effect_type: str = "flanger"
    rate_hz: float = 0.5  # LFO rate in Hz (0.1-10)
    depth: float = 0.5  # Modulation depth (0-1)
    centre_delay_ms: float = 5.0  # Center delay in ms (1-15)
    feedback: float = 0.5  # Feedback amount (0-0.95)
    mix: float = 0.5


@dataclass
class Phaser(AudioEffect):
    """Phaser effect for sweeping notches (wah-like)."""
    effect_type: str = "phaser"
    rate_hz: float = 1.0  # LFO rate in Hz (0.1-10)
    depth: float = 0.5  # Modulation depth (0-1)
    centre_frequency_hz: float = 1000.0  # Center frequency (200-5000)
    feedback: float = 0.5  # Feedback amount (0-0.95)
    mix: float = 0.5


@dataclass
class PitchShift(AudioEffect):
    """Pitch shift effect for harmony/detuning."""
    effect_type: str = "pitch"
    semitones: float = 0.0  # Pitch shift in semitones (-12 to +12)
    mix: float = 0.5


def apply_effect_chain(signal: np.ndarray, effects: List[AudioEffect], sample_rate: int) -> np.ndarray:
    """
    Apply a chain of audio effects to a mono signal.
    
    Args:
        signal: Mono audio signal (1D array)
        effects: List of AudioEffect instances to apply in order
        sample_rate: Sample rate in Hz (e.g., 44100)
    
    Returns:
        Processed mono signal (same length as input)
    """
    if len(effects) == 0:
        return signal
    
    pb = _get_pedalboard()
    
    # Convert to float32 for pedalboard (normalized to [-1, 1])
    signal_float = signal.astype(np.float32)
    
    # Normalize to prevent clipping through FX chain
    max_val = np.abs(signal_float).max()
    if max_val > 0:
        signal_float = signal_float / max_val
    else:
        max_val = 1.0
    
    # Apply each effect in the chain
    for effect in effects:
        signal_float = _apply_single_effect(signal_float, effect, sample_rate, pb)
    
    # Restore original scaling
    signal_float = signal_float * max_val
    
    return signal_float


def _apply_single_effect(signal: np.ndarray, effect: AudioEffect, sample_rate: int, pb) -> np.ndarray:
    """Apply a single effect with dry/wet mixing."""
    # Store dry signal for mixing
    dry = signal.copy()
    
    # Build pedalboard plugin based on effect type
    try:
        if effect.effect_type == "distortion":
            board = pb.Pedalboard([
                pb.Distortion(drive_db=effect.drive_db)
            ])
        
        elif effect.effect_type == "chorus":
            board = pb.Pedalboard([
                pb.Chorus(
                    rate_hz=effect.rate_hz,
                    depth=effect.depth,
                    centre_delay_ms=effect.centre_delay_ms,
                    feedback=effect.feedback,
                    mix=1.0  # We do our own mixing
                )
            ])
        
        elif effect.effect_type == "tremolo":
            # Pedalboard doesn't have Tremolo, so we implement it manually
            t = np.arange(len(signal)) / sample_rate
            lfo = effect.depth * np.sin(2 * np.pi * effect.rate_hz * t)
            wet = signal * (1.0 + lfo) / 2.0  # Amplitude modulation
            return dry * (1 - effect.mix) + wet * effect.mix
        
        elif effect.effect_type == "flanger":
            # Pedalboard doesn't have Flanger, use Chorus with tighter delay
            board = pb.Pedalboard([
                pb.Chorus(
                    rate_hz=effect.rate_hz,
                    depth=effect.depth,
                    centre_delay_ms=effect.centre_delay_ms,
                    feedback=effect.feedback,
                    mix=1.0  # We do our own mixing
                )
            ])
        
        elif effect.effect_type == "phaser":
            board = pb.Pedalboard([
                pb.Phaser(
                    rate_hz=effect.rate_hz,
                    depth=effect.depth,
                    centre_frequency_hz=effect.centre_frequency_hz,
                    feedback=effect.feedback,
                    mix=1.0  # We do our own mixing
                )
            ])
        
        elif effect.effect_type == "pitch":
            board = pb.Pedalboard([
                pb.PitchShift(semitones=effect.semitones)
            ])
        
        else:
            # Unknown effect, return dry
            return dry
        
        # Process through pedalboard
        wet = board(signal, sample_rate)
        
        # Ensure same length (pedalboard might change length slightly)
        if len(wet) > len(signal):
            wet = wet[:len(signal)]
        elif len(wet) < len(signal):
            wet = np.pad(wet, (0, len(signal) - len(wet)))
        
        # Mix dry and wet
        return dry * (1 - effect.mix) + wet * effect.mix
    
    except Exception as e:
        # If effect fails, return dry signal
        print(f"Warning: Effect {effect.effect_type} failed: {e}")
        return dry


def create_default_effect(effect_name: str) -> AudioEffect:
    """Create an effect with sensible defaults for musical use."""
    if effect_name.lower() == "distortion":
        return Distortion(drive_db=15.0, mix=0.4)
    
    elif effect_name.lower() == "chorus":
        return Chorus(rate_hz=1.5, depth=0.4, centre_delay_ms=7.0, feedback=0.2, mix=0.5)
    
    elif effect_name.lower() == "tremolo":
        return Tremolo(rate_hz=4.0, depth=0.6, mix=1.0)
    
    elif effect_name.lower() == "flanger":
        return Flanger(rate_hz=0.5, depth=0.6, centre_delay_ms=5.0, feedback=0.6, mix=0.5)
    
    elif effect_name.lower() == "wah" or effect_name.lower() == "phaser":
        # Phaser is the closest to wah in pedalboard
        return Phaser(rate_hz=1.0, depth=0.7, centre_frequency_hz=1500.0, feedback=0.5, mix=0.5)
    
    elif effect_name.lower() == "pitch":
        return PitchShift(semitones=7.0, mix=0.3)  # Default: perfect fifth harmony
    
    else:
        raise ValueError(f"Unknown effect: {effect_name}")
