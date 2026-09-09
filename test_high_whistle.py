"""Test high register whistle issue and verify fixes."""

import numpy as np
from notes import Song, Track, Note
from synth import synthesize_song, export_wav


def create_high_register_test() -> Song:
    """
    Create a dense high-register passage to test for whistling.
    Uses keys 60-72 (C4 to C5) with delay enabled.
    """
    song = Song(bpm=120)
    
    # Create a track with dense high notes and delay enabled
    track = Track(
        name="High Test",
        intensity=1.5,
        delay=True,  # This could cause comb filtering on highs
        hold_seconds=1.0
    )
    
    # Create a rapid ascending/descending pattern in high register
    # Keys 60-72 = C4 to C5 (bright register where whistling occurs)
    pattern = [60, 64, 67, 72, 67, 64, 60, 62, 65, 69, 72]
    
    beat = 0.0
    for key in pattern:
        track.notes.append(Note(
            key=key,
            start_beat=beat,
            duration_beats=0.5,
            velocity=100
        ))
        beat += 0.5
    
    song.tracks.append(track)
    return song


def test_synthesis():
    """Synthesize test and save to file."""
    print("Creating high register test passage...")
    song = create_high_register_test()
    
    print("Synthesizing (this may take a moment)...")
    audio_data, sample_rate = synthesize_song(song)
    
    print("Exporting to test_high_whistle.wav...")
    export_wav("test_high_whistle.wav", song)
    
    print(f"✓ Generated {len(audio_data)} samples at {sample_rate} Hz")
    print("✓ Saved to test_high_whistle.wav")
    print("\nListen for piercing/whistling artifacts in the high notes.")


if __name__ == "__main__":
    test_synthesis()
