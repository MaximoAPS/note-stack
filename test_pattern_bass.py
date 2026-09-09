#!/usr/bin/env python3
"""Test script for Pattern → Base feature."""

from number_melody import generate_pattern_bass
from midi_io import load_midi

# Load a style MIDI for duration learning
print("Loading style MIDI...")
style_song = load_midi("demos/chopin-etude.mid")
style_tracks = style_song.tracks
print(f"  Loaded {len(style_tracks)} tracks from Chopin Etude")

# Test 1: Offset mode with Pi pattern (using offset that puts keys in bass range)
print("\nTest 1: Offset mode - Pi pattern '3-1-4-1-5' with offset 25")
bass_track = generate_pattern_bass(
    pattern_string="3-1-4-1-5",
    style_tracks=style_tracks,
    bpm=96.0,
    mode="offset",
    bass_offset=25,  # 3+25=28, 1+25=26->28, 4+25=29, 5+25=30
    min_key=28,
    max_key=42
)
print(f"  Generated {len(bass_track.notes)} notes")
print(f"  Track name: {bass_track.name}")
if bass_track.notes:
    keys = [n.key for n in bass_track.notes]
    print(f"  Keys: {keys}")
    print(f"  Expected pattern with offset 25 clamped to [28,42]: [28, 28, 29, 28, 30]")
    durations = [round(n.duration_beats, 2) for n in bass_track.notes]
    print(f"  Durations: {durations}")
    print(f"  Key range: {min(keys)} - {max(keys)}")
    # Verify the pattern is correct (accounting for clamping)
    # 3+25=28, 1+25=26->28, 4+25=29, 1+25=26->28, 5+25=30
    expected = [28, 28, 29, 28, 30]
    if keys == expected:
        print("  ✓ Pattern matches expected output!")
    else:
        print(f"  ⚠ Pattern mismatch: got {keys}, expected {expected}")
else:
    print("  ✗ ERROR: No notes generated")

# Test 2: Tonic+scale mode
print("\nTest 2: Tonic+scale mode - Pattern '0-2-4-5-7'")
bass_track2 = generate_pattern_bass(
    pattern_string="0-2-4-5-7",
    style_tracks=style_tracks,
    bpm=96.0,
    mode="tonic_scale",
    tonic=28,  # E1
    scale_mode="major",
    min_key=28,
    max_key=42
)
print(f"  Generated {len(bass_track2.notes)} notes")
print(f"  Track name: {bass_track2.name}")
if bass_track2.notes:
    keys = [n.key for n in bass_track2.notes]
    print(f"  Keys: {keys}")
    # Major scale has 7 degrees [0,2,4,5,7,9,11], pattern digits map as:
    # 0->0, 2->4, 4->7, 5->9, 7->0 (wraps), so: 28, 32, 35, 37, 28
    print(f"  Expected (digit maps to scale degree): [28, 32, 35, 37, 28]")
    durations = [round(n.duration_beats, 2) for n in bass_track2.notes]
    print(f"  Durations: {durations}")
    expected = [28, 32, 35, 37, 28]
    if keys == expected:
        print("  ✓ Tonic+scale pattern matches expected!")
    else:
        print(f"  ⚠ Pattern mismatch: got {keys}, expected {expected}")
else:
    print("  ✗ ERROR: No notes generated")

# Test 3: Comma-separated pattern (with lower min_key to allow full range)
print("\nTest 3: Comma-separated pattern '1,2,3,4,5'")
bass_track3 = generate_pattern_bass(
    pattern_string="1,2,3,4,5",
    style_tracks=style_tracks,
    bpm=96.0,
    mode="offset",
    bass_offset=10,
    min_key=1,  # Allow full piano range
    max_key=88
)
print(f"  Generated {len(bass_track3.notes)} notes")
if bass_track3.notes:
    keys = [n.key for n in bass_track3.notes]
    print(f"  Keys: {keys}")
    expected = [11, 12, 13, 14, 15]
    if keys == expected:
        print("  ✓ Comma-separated pattern works!")
    else:
        print(f"  ⚠ Pattern mismatch: got {keys}, expected {expected}")

# Test 4: Empty pattern
print("\nTest 4: Empty pattern")
bass_track4 = generate_pattern_bass(
    pattern_string="",
    style_tracks=style_tracks,
    bpm=96.0,
    mode="offset",
    bass_offset=10
)
print(f"  Generated {len(bass_track4.notes)} notes (should be 0)")
if len(bass_track4.notes) == 0:
    print("  ✓ Empty pattern handled correctly!")
else:
    print("  ✗ ERROR: Should have generated 0 notes")

print("\n" + "="*60)
print("All tests completed!")
print("="*60)
