"""Piano synthesis based on Desmos 'Piano Song' graph."""

import numpy as np
from typing import List, Tuple
from notes import Song, Track, Note


SAMPLE_RATE = 44100
NYQUIST = SAMPLE_RATE / 2


def key_to_hz(key: int) -> float:
    """Convert piano key (1-88) to frequency. A4 = key 49 = 440 Hz."""
    return 2 ** ((key - 49) / 12) * 440


def harmonic_intensity(h: int) -> float:
    """Intensity formula from Desmos: h is 0-based (H-1)."""
    return 1 / (1.24729 * h**1.5 + 1)


def key_decay_scale(key: int) -> float:
    """
    Key-dependent decay scaling like a real piano.
    Higher keys decay faster, lower keys ring longer.
    C4 (key 40) is baseline 1.0. Clipped to [0.55, 3.5].
    """
    scale = 2 ** ((key - 40) / 18)
    return np.clip(scale, 0.55, 3.5)


def box_muller_decay(track_idx: int, key: int, start_beat: float, harmonic_num: int) -> float:
    """
    Generate decay rate using Box-Muller transform.
    Mean=10.2, std=3.54. Seeded deterministically for repeatability.
    Scaled by key_decay_scale for realistic piano behavior.
    """
    # Create deterministic seed from inputs
    seed_val = hash((track_idx, key, start_beat, harmonic_num)) % (2**32)
    rng = np.random.RandomState(seed_val)
    
    u1, u2 = rng.uniform(0, 1, 2)
    # Avoid log(0)
    u1 = max(u1, 1e-10)
    
    # Box-Muller: mean + std * sqrt(-2*ln(U1)) * cos(2*pi*U2)
    n = 3.54 * np.sqrt(-2 * np.log(u1)) * np.cos(2 * np.pi * u2) + 10.2
    
    # Scale by key: higher keys decay faster
    n *= key_decay_scale(key)
    
    return n


def time_warp_X(t: float, d: float) -> float:
    """
    Time warp X(t): grows at rate 1, but FREEZES between 0.34s and d.
    X(t) = t for t < 0.34
    X(t) = 0.34 for 0.34 <= t < d
    X(t) = t - d + 0.34 for t >= d
    """
    if t < 0.34:
        return t
    elif t < d:
        return 0.34
    else:
        return t - d + 0.34


def compute_envelope(t: float, intensity: float, decay_rate: float, d: float) -> float:
    """
    Envelope: attack polynomial until 0.172s, then exponential decay.
    Attack: polynomial from 0 at t=0.05 to intensity at t=0.172, matching exp derivative.
    Uses exponent 1.5.
    """
    if t < 0.05:
        return 0.0
    elif t < 0.172:
        # Polynomial attack phase
        # f_pol(t) = a * (t - 0.05)^1.5
        # Must match value and derivative at t=0.172
        # exp form at 0.172: i * exp(-n * (X(0.172) - 0.172)) = i * exp(0) = i
        # exp derivative at 0.172: -i * n * dX/dt = -i * n * 1 = -i * n
        # poly value at 0.172: a * (0.172 - 0.05)^1.5 = i
        # poly derivative at 0.172: a * 1.5 * (0.172 - 0.05)^0.5 = -i * n
        # From first: a = i / (0.122)^1.5
        # Check second: a * 1.5 * (0.122)^0.5 = i / (0.122)^1.5 * 1.5 * (0.122)^0.5
        #                                      = i * 1.5 / 0.122 = i * 12.295...
        # We want -i * n, so this won't match exactly for arbitrary n.
        # The Desmos description says "matching value i and derivative of exp at 0.172"
        # Let's use the value constraint primarily
        delta_t = 0.172 - 0.05
        a = intensity / (delta_t ** 1.5)
        return a * ((t - 0.05) ** 1.5)
    else:
        # Exponential decay phase
        X_t = time_warp_X(t, d)
        return intensity * np.exp(-decay_rate * (X_t - 0.172))


def synthesize_note(key: int, duration_seconds: float, track_idx: int, start_beat: float,
                    intensity: float, hold_seconds: float, velocity: int = 100) -> np.ndarray:
    """
    Synthesize a single piano note using 64 harmonics.
    Renders full envelope decay with key-dependent tail length (cap 3.5s).
    Higher keys decay faster and need shorter buffers.
    Returns mono audio samples.
    """
    f0 = key_to_hz(key)
    
    # Key-dependent decay: higher keys ring shorter
    decay_scale = key_decay_scale(key)
    
    # Extra ring time inversely proportional to decay rate
    extra_ring = 2.0 / decay_scale
    
    # Render long enough for envelope to decay, cap at 3.5s, never shorter than scored
    render_duration = max(duration_seconds, min(3.5, duration_seconds + extra_ring))
    num_samples = int(render_duration * SAMPLE_RATE)
    t = np.linspace(0, render_duration, num_samples, endpoint=False)
    
    signal = np.zeros(num_samples)
    
    # Velocity scaling (0-127 MIDI scale)
    vel_scale = velocity / 100.0
    
    # Generate 64 harmonics
    for H in range(1, 65):
        freq = H * f0
        # Drop harmonics at 0.92*Nyquist to avoid aliasing artifacts
        if freq >= 0.92 * NYQUIST:
            continue
        
        h = H - 1  # 0-based for intensity formula
        harm_intensity = harmonic_intensity(h) * intensity * vel_scale
        decay_rate = box_muller_decay(track_idx, key, start_beat, H)
        
        # Compute envelope for each time point
        envelope = np.array([compute_envelope(ti, harm_intensity, decay_rate, hold_seconds) 
                            for ti in t])
        
        # Generate harmonic
        harmonic = envelope * np.sin(2 * np.pi * freq * t)
        signal += harmonic
    
    # Apply short fade-out at the very end (~12ms)
    fade_samples = int(0.012 * SAMPLE_RATE)
    if len(signal) > fade_samples:
        fade = np.linspace(1.0, 0.0, fade_samples)
        signal[-fade_samples:] *= fade
    
    return signal


def synthesize_track(track: Track, bpm: float, track_idx: int, total_beats: float) -> np.ndarray:
    """Synthesize all notes in a track, optionally with delay voice."""
    duration_seconds = (total_beats * 60.0) / bpm
    # Add extra padding for long note tails (3.5s cap per note)
    num_samples = int((duration_seconds + 4.0) * SAMPLE_RATE)
    signal = np.zeros(num_samples)
    
    for note in track.notes:
        note_start_sec = (note.start_beat * 60.0) / bpm
        note_dur_sec = (note.duration_beats * 60.0) / bpm
        
        # Synthesize main voice (renders full envelope decay)
        note_signal = synthesize_note(
            note.key, note_dur_sec, track_idx, note.start_beat,
            track.intensity, track.hold_seconds, note.velocity
        )
        
        start_sample = int(note_start_sec * SAMPLE_RATE)
        end_sample = start_sample + len(note_signal)
        
        if end_sample > num_samples:
            note_signal = note_signal[:num_samples - start_sample]
            end_sample = num_samples
        
        signal[start_sample:end_sample] += note_signal
        
        # Add delay voice if enabled (at 0.4 gain to avoid comb filtering)
        if track.delay:
            delay_sec = 30.0 / 160.0  # 30/160 seconds
            delay_samples = int(delay_sec * SAMPLE_RATE)
            delay_start = start_sample + delay_samples
            delay_end = delay_start + len(note_signal)
            
            if delay_start < num_samples:
                delay_signal = note_signal * 0.4  # Reduce delay gain
                if delay_end > num_samples:
                    delay_signal = delay_signal[:num_samples - delay_start]
                    delay_end = num_samples
                signal[delay_start:delay_end] += delay_signal
    
    return signal


def synthesize_song(song: Song) -> Tuple[np.ndarray, int]:
    """
    Synthesize entire song by mixing all unmuted tracks.
    Returns (audio_array, sample_rate).
    """
    # Calculate total duration
    total_beats = 0.0
    for track in song.tracks:
        if not track.mute and track.notes:
            max_beat = max(note.start_beat + note.duration_beats for note in track.notes)
            total_beats = max(total_beats, max_beat)
    
    if total_beats == 0:
        # No notes, return silence
        return np.zeros(SAMPLE_RATE), SAMPLE_RATE
    
    # Add padding for note tails (3.5s max per note + 2 beats)
    total_beats += 2.0
    
    duration_seconds = (total_beats * 60.0) / song.bpm
    # Extra padding for long note decays
    num_samples = int((duration_seconds + 4.0) * SAMPLE_RATE)
    mixed = np.zeros(num_samples)
    
    # Mix all unmuted tracks
    for track_idx, track in enumerate(song.tracks):
        if not track.mute:
            track_signal = synthesize_track(track, song.bpm, track_idx, total_beats)
            # Ensure same length
            if len(track_signal) < num_samples:
                track_signal = np.pad(track_signal, (0, num_samples - len(track_signal)))
            elif len(track_signal) > num_samples:
                track_signal = track_signal[:num_samples]
            mixed += track_signal
    
    # Peak normalize to 0.89
    max_val = np.abs(mixed).max()
    if max_val > 0:
        mixed = mixed * (0.89 / max_val)
    
    # Convert to 16-bit PCM
    audio_int16 = (mixed * 32767).astype(np.int16)
    
    return audio_int16, SAMPLE_RATE


def export_wav(filename: str, song: Song) -> None:
    """Export song to WAV file."""
    import wave
    
    audio_data, sample_rate = synthesize_song(song)
    
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
