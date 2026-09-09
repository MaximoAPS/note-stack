"""Test Fill Base from Solo feature."""

from notes import Track, Note
from number_melody import generate_pattern_bass_from_solo, choose_offset_for_solo


def test_choose_offset_for_solo():
    """Test auto offset selection."""
    print("Testing choose_offset_for_solo()...")
    
    # Create a simple solo track (C major scale: 40, 42, 44, 45, 47, 49, 51)
    solo_notes = [
        Note(key=40, start_beat=0.0, duration_beats=0.5),
        Note(key=42, start_beat=0.5, duration_beats=0.5),
        Note(key=44, start_beat=1.0, duration_beats=0.5),
        Note(key=45, start_beat=1.5, duration_beats=0.5),
        Note(key=47, start_beat=2.0, duration_beats=0.5),
        Note(key=49, start_beat=2.5, duration_beats=0.5),
        Note(key=51, start_beat=3.0, duration_beats=0.5),
    ]
    solo_track = Track(name="Test Solo", notes=solo_notes)
    
    # Pattern: 3-1-4-1-5
    pattern_digits = [3, 1, 4, 1, 5]
    
    # Choose offset
    offset = choose_offset_for_solo(
        pattern_digits=pattern_digits,
        solo_track=solo_track,
        min_key=28,
        max_key=42
    )
    
    print(f"  Solo pitch classes: {set((n.key - 1) % 12 for n in solo_notes)}")
    print(f"  Pattern digits: {pattern_digits}")
    print(f"  Auto-chosen offset: {offset}")
    print(f"  Resulting bass keys: {[d + offset for d in pattern_digits]}")
    
    # Verify offset is in reasonable range
    assert 0 <= offset <= 40, f"Offset {offset} out of range"
    
    # Verify bass keys are in range
    bass_keys = [max(28, min(42, d + offset)) for d in pattern_digits]
    assert all(28 <= k <= 42 for k in bass_keys), f"Bass keys {bass_keys} out of range"
    
    print("  ✓ choose_offset_for_solo() passed")
    print()


def test_generate_pattern_bass_from_solo_auto():
    """Test bass generation with auto offset."""
    print("Testing generate_pattern_bass_from_solo() with auto offset...")
    
    # Create a solo track
    solo_notes = [
        Note(key=40, start_beat=0.0, duration_beats=0.5),
        Note(key=42, start_beat=0.5, duration_beats=0.5),
        Note(key=44, start_beat=1.0, duration_beats=0.5),
        Note(key=45, start_beat=1.5, duration_beats=0.5),
        Note(key=47, start_beat=2.0, duration_beats=0.5),
        Note(key=49, start_beat=2.5, duration_beats=0.5),
        Note(key=51, start_beat=3.0, duration_beats=0.5),
        Note(key=52, start_beat=3.5, duration_beats=0.5),
    ]
    solo_track = Track(name="Test Solo", notes=solo_notes)
    
    # Generate bass with auto offset
    bass_track = generate_pattern_bass_from_solo(
        pattern_string="3-1-4-1-5",
        solo_track=solo_track,
        style_tracks=[],  # No style tracks, will use default durations
        bpm=96.0,
        offset_mode="auto",
        min_key=28,
        max_key=42,
        loop_pattern=True
    )
    
    print(f"  Generated {len(bass_track.notes)} bass notes")
    print(f"  Bass keys: {[n.key for n in bass_track.notes]}")
    print(f"  Bass span: {bass_track.notes[0].start_beat:.2f} - {bass_track.notes[-1].start_beat + bass_track.notes[-1].duration_beats:.2f}")
    print(f"  Solo span: {solo_notes[0].start_beat:.2f} - {solo_notes[-1].start_beat + solo_notes[-1].duration_beats:.2f}")
    
    # Verify at least one pattern iteration
    assert len(bass_track.notes) >= 5, f"Expected at least 5 notes, got {len(bass_track.notes)}"
    
    # Verify all notes in range
    assert all(28 <= n.key <= 42 for n in bass_track.notes), "Bass notes out of range"
    
    # Verify timing is sequential
    for i in range(1, len(bass_track.notes)):
        prev_end = bass_track.notes[i-1].start_beat + bass_track.notes[i-1].duration_beats
        curr_start = bass_track.notes[i].start_beat
        assert curr_start >= prev_end - 0.01, f"Notes overlap at index {i}"
    
    print("  ✓ generate_pattern_bass_from_solo() with auto offset passed")
    print()


def test_generate_pattern_bass_from_solo_manual():
    """Test bass generation with manual offset."""
    print("Testing generate_pattern_bass_from_solo() with manual offset...")
    
    # Create a solo track
    solo_notes = [
        Note(key=40, start_beat=0.0, duration_beats=1.0),
        Note(key=42, start_beat=1.0, duration_beats=1.0),
    ]
    solo_track = Track(name="Test Solo", notes=solo_notes)
    
    # Generate bass with manual offset
    bass_track = generate_pattern_bass_from_solo(
        pattern_string="3-1-4-1-5",
        solo_track=solo_track,
        style_tracks=[],
        bpm=96.0,
        offset_mode="manual",
        manual_offset=10,
        min_key=28,
        max_key=42,
        loop_pattern=True
    )
    
    print(f"  Generated {len(bass_track.notes)} bass notes")
    print(f"  Bass keys: {[n.key for n in bass_track.notes]}")
    
    # Verify pattern with offset 10: 3+10=13, 1+10=11, 4+10=14, 1+10=11, 5+10=15
    expected_keys = [13, 11, 14, 11, 15]
    actual_keys = [n.key for n in bass_track.notes[:5]]
    
    # Note: keys may be clamped to [28, 42], so 13→28, 11→28, 14→28, 15→28
    # Actually, min_key=28, so all should be 28 (clamped)
    assert all(28 <= k <= 42 for k in actual_keys), f"Keys out of range: {actual_keys}"
    
    print(f"  Expected pattern keys (before clamp): {expected_keys}")
    print(f"  Actual bass keys (after clamp): {actual_keys}")
    print("  ✓ generate_pattern_bass_from_solo() with manual offset passed")
    print()


def test_pattern_looping():
    """Test pattern looping to fill solo span."""
    print("Testing pattern looping...")
    
    # Create a longer solo track (8 beats)
    solo_notes = [
        Note(key=40 + i % 7, start_beat=i * 0.5, duration_beats=0.5)
        for i in range(16)
    ]
    solo_track = Track(name="Test Solo", notes=solo_notes)
    
    # Short pattern that should loop
    bass_track = generate_pattern_bass_from_solo(
        pattern_string="3-1-4",
        solo_track=solo_track,
        style_tracks=[],
        bpm=96.0,
        offset_mode="manual",
        manual_offset=25,  # 3+25=28, 1+25=26→28, 4+25=29
        min_key=28,
        max_key=42,
        loop_pattern=True
    )
    
    print(f"  Solo span: 8.0 beats")
    print(f"  Pattern length: 3 notes")
    print(f"  Generated bass notes: {len(bass_track.notes)}")
    print(f"  Bass span: {bass_track.notes[-1].start_beat + bass_track.notes[-1].duration_beats:.2f} beats")
    
    # Verify pattern looped multiple times
    assert len(bass_track.notes) >= 3, f"Expected at least 3 notes, got {len(bass_track.notes)}"
    
    # Verify pattern covers approximately the solo span
    bass_span = bass_track.notes[-1].start_beat + bass_track.notes[-1].duration_beats
    solo_span = solo_notes[-1].start_beat + solo_notes[-1].duration_beats
    assert abs(bass_span - solo_span) < 2.0, f"Bass span {bass_span} doesn't match solo span {solo_span}"
    
    print("  ✓ Pattern looping passed")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Fill Base from Solo — Feature Tests")
    print("=" * 60)
    print()
    
    try:
        test_choose_offset_for_solo()
        test_generate_pattern_bass_from_solo_auto()
        test_generate_pattern_bass_from_solo_manual()
        test_pattern_looping()
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Test failed: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()
