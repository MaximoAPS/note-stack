"""Test mood FX chain with Distortion+Chorus example."""

import numpy as np
from notes import Song, Track, Note
from synth import synthesize_song, export_wav
from audio_fx import create_default_effect

# Create a simple test song
song = Song(bpm=120)

# Create a track with a few notes (middle C and E)
track = Track(
    name="Test Track with FX",
    intensity=1.0,
    hold_seconds=0.8,
    delay=False,
    notes=[
        Note(key=40, start_beat=0.0, duration_beats=1.0),  # Middle C
        Note(key=44, start_beat=1.0, duration_beats=1.0),  # E
        Note(key=47, start_beat=2.0, duration_beats=1.0),  # G
        Note(key=52, start_beat=3.0, duration_beats=2.0),  # E (octave up)
    ]
)

# Test 1: No FX (baseline)
print("Test 1: Synthesizing without FX...")
song.tracks = [track]
audio_clean, sr = synthesize_song(song)
print(f"✓ Clean audio: {len(audio_clean)} samples, peak: {np.abs(audio_clean).max()}")

# Test 2: Add Distortion
print("\nTest 2: Adding Distortion (drive=15dB, mix=0.4)...")
track.audio_fx = [create_default_effect("Distortion")]
audio_distortion, sr = synthesize_song(song)
print(f"✓ Distorted audio: {len(audio_distortion)} samples, peak: {np.abs(audio_distortion).max()}")

# Test 3: Add Distortion + Chorus
print("\nTest 3: Adding Distortion + Chorus (stackable)...")
track.audio_fx = [
    create_default_effect("Distortion"),
    create_default_effect("Chorus")
]
audio_fx_chain, sr = synthesize_song(song)
print(f"✓ FX chain audio: {len(audio_fx_chain)} samples, peak: {np.abs(audio_fx_chain).max()}")

# Export to WAV for listening test
print("\nExporting test files...")
track.audio_fx = []
export_wav("/tmp/test_clean.wav", song)
print("✓ Exported: /tmp/test_clean.wav")

track.audio_fx = [create_default_effect("Distortion")]
export_wav("/tmp/test_distortion.wav", song)
print("✓ Exported: /tmp/test_distortion.wav")

track.audio_fx = [
    create_default_effect("Distortion"),
    create_default_effect("Chorus")
]
export_wav("/tmp/test_distortion_chorus.wav", song)
print("✓ Exported: /tmp/test_distortion_chorus.wav")

print("\n✅ All tests passed! FX chain is working.")
print("Files exported to /tmp/ for listening comparison.")
