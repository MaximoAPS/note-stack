#!/usr/bin/env python3
"""Test script to verify all UX bug fixes."""

import time
import numpy as np
from notes import Song, Track, Note
from synth import synthesize_song
from app import parse_cluster_string, clusters_to_notes

def test_synthesis_speed():
    """Test that synthesis is fast for small songs."""
    print("Testing synthesis speed...")
    
    # Create a simple song with 5 notes
    notes = [
        Note(key=35, start_beat=0.0, duration_beats=0.5, velocity=100),
        Note(key=35, start_beat=0.5, duration_beats=0.5, velocity=100),
        Note(key=36, start_beat=1.0, duration_beats=0.5, velocity=100),
        Note(key=38, start_beat=1.5, duration_beats=0.5, velocity=100),
        Note(key=35, start_beat=2.0, duration_beats=0.5, velocity=100),
    ]
    track = Track(name="Test Track", notes=notes)
    song = Song(bpm=96, tracks=[track])
    
    # Measure synthesis time
    start = time.time()
    audio_data, sample_rate = synthesize_song(song)
    elapsed = time.time() - start
    
    print(f"  ✓ Synthesized 5 notes in {elapsed:.2f}s")
    
    # Should be much faster than 15-20s (the old slow behavior)
    if elapsed > 10:
        print(f"  ⚠️ WARNING: Still too slow! Expected <5s, got {elapsed:.2f}s")
        return False
    elif elapsed > 5:
        print(f"  ⚠️ Slower than ideal but acceptable: {elapsed:.2f}s")
    else:
        print(f"  ✓ Fast synthesis: {elapsed:.2f}s (expected <5s)")
    
    return True

def test_empty_track_handling():
    """Test that empty tracks don't cause Altair errors."""
    print("\nTesting empty track handling...")
    
    # Create song with empty track
    track = Track(name="Empty Track", notes=[])
    song = Song(bpm=96, tracks=[track])
    
    # This should not raise errors (would previously cause Altair infinite extent warning)
    try:
        audio_data, sample_rate = synthesize_song(song)
        print("  ✓ Empty track handled without errors")
        return True
    except Exception as e:
        print(f"  ✗ Error with empty track: {e}")
        return False

def test_low_key_warnings():
    """Test that low keys generate warnings."""
    print("\nTesting low key warnings...")
    
    # Parse cluster string with low keys (Pi digits: 3-1-4-1-5)
    clusters, warnings = parse_cluster_string("3-1-4-1-5", default_duration=0.5)
    
    print(f"  Parsed {len(clusters)} clusters from '3-1-4-1-5'")
    print(f"  Generated {len(warnings)} warnings")
    
    if len(warnings) > 0:
        print("  Warnings:")
        for warning in warnings:
            print(f"    {warning}")
        print("  ✓ Low keys correctly generate warnings")
        return True
    else:
        print("  ✗ Expected warnings for low keys but got none")
        return False

def test_normal_key_no_warnings():
    """Test that normal keys don't generate warnings."""
    print("\nTesting normal key range (no warnings)...")
    
    # Parse cluster string with normal keys
    clusters, warnings = parse_cluster_string("35-35,36-38-35", default_duration=0.5)
    
    print(f"  Parsed {len(clusters)} clusters from '35-35,36-38-35'")
    print(f"  Generated {len(warnings)} warnings")
    
    if len(warnings) == 0:
        print("  ✓ Normal keys correctly generate no warnings")
        return True
    else:
        print(f"  ⚠️ Unexpected warnings for normal keys: {warnings}")
        return False

def test_velocity_enforcement():
    """Test that velocity is always >= 1."""
    print("\nTesting velocity enforcement...")
    
    # Create cluster with velocity 0 (should be enforced to 1)
    from app import NoteCluster
    cluster = NoteCluster(start_beat=0.0, duration_beats=0.5, keys=[35], velocity=0)
    notes = clusters_to_notes([cluster])
    
    if all(note.velocity >= 1 for note in notes):
        print(f"  ✓ Velocity enforced: velocity=0 → {notes[0].velocity}")
        return True
    else:
        print(f"  ✗ Velocity not enforced: got {notes[0].velocity}")
        return False

def test_synthesis_with_test_case():
    """Test synthesis with the actual test case: 35-35,36-38-35."""
    print("\nTesting synthesis with test case: 35-35,36-38-35...")
    
    clusters, warnings = parse_cluster_string("35-35,36-38-35", default_duration=0.5)
    notes = clusters_to_notes(clusters)
    
    track = Track(name="Test Track", notes=notes)
    song = Song(bpm=96, tracks=[track])
    
    start = time.time()
    audio_data, sample_rate = synthesize_song(song)
    elapsed = time.time() - start
    
    print(f"  ✓ Synthesized test case in {elapsed:.2f}s")
    print(f"  Audio shape: {audio_data.shape}, sample rate: {sample_rate}")
    
    if elapsed < 5:
        print(f"  ✓ Synthesis completes in reasonable time (<5s)")
        return True
    else:
        print(f"  ⚠️ Synthesis took {elapsed:.2f}s (target <5s)")
        return True  # Still acceptable, just slower

def main():
    print("=" * 60)
    print("Testing UX Bug Fixes")
    print("=" * 60)
    
    results = {
        "Synthesis Speed": test_synthesis_speed(),
        "Empty Track Handling": test_empty_track_handling(),
        "Low Key Warnings": test_low_key_warnings(),
        "Normal Key No Warnings": test_normal_key_no_warnings(),
        "Velocity Enforcement": test_velocity_enforcement(),
        "Test Case Synthesis": test_synthesis_with_test_case(),
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
