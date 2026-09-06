"""Smoke test for editor session."""

import sys
from notes import Song, Track, Note
from editor_session import EditorSession


def test_editor_session_basic():
    """Test basic editor session functionality."""
    print("Testing EditorSession...")
    
    # Create session
    session = EditorSession()
    assert len(session.sources) == 0
    
    # Add a source
    song1 = Song(bpm=120, tracks=[
        Track(name="Track 1", notes=[
            Note(key=49, start_beat=0, duration_beats=1)
        ])
    ])
    source_id = session.add_source("Test Song 1", song1)
    assert len(session.sources) == 1
    assert session.base_source_id == source_id
    
    # Set track role
    assert session.set_track_role(source_id, 0, "final")
    metadata = session.get_track_metadata(source_id, 0)
    assert metadata.role == "final"
    
    # Add another source
    song2 = Song(bpm=140, tracks=[
        Track(name="Bass", notes=[
            Note(key=20, start_beat=0, duration_beats=2)
        ]),
        Track(name="Melody", notes=[
            Note(key=60, start_beat=0, duration_beats=1)
        ])
    ])
    source_id2 = session.add_source("Test Song 2", song2)
    assert len(session.sources) == 2
    
    # Set roles
    session.set_track_role(source_id2, 0, "mashup_source")
    session.set_track_role(source_id2, 1, "ignore")
    
    # Get mashup sources
    mashup_tracks = session.get_mashup_sources()
    assert len(mashup_tracks) == 1
    assert "Bass" in mashup_tracks[0].name
    
    # Compose final
    final_song = session.compose_final_song()
    assert len(final_song.tracks) == 1  # Only "final" track
    assert final_song.bpm == 120  # From base source
    
    print("✓ Basic session tests passed")


def test_key_range_filter():
    """Test key range filtering."""
    print("Testing key range filtering...")
    
    session = EditorSession()
    
    # Create a track with notes across range
    notes = [
        Note(key=10, start_beat=0, duration_beats=1),  # Low
        Note(key=30, start_beat=1, duration_beats=1),  # Mid
        Note(key=60, start_beat=2, duration_beats=1),  # High
        Note(key=80, start_beat=3, duration_beats=1),  # Very high
    ]
    song = Song(bpm=120, tracks=[Track(name="Test", notes=notes)])
    source_id = session.add_source("Test Song", song)
    
    # Set role with key range filter
    session.set_track_role(source_id, 0, "final", key_lo=30, key_hi=70)
    
    # Compose - should only have mid and high notes
    final_song = session.compose_final_song()
    assert len(final_song.tracks) == 1
    track = final_song.tracks[0]
    assert len(track.notes) == 2  # Only keys 30 and 60
    assert all(30 <= n.key <= 70 for n in track.notes)
    
    print("✓ Key range filter tests passed")


def test_multi_track_preservation():
    """Test that multi-track MIDIs preserve separate tracks."""
    print("Testing multi-track preservation...")
    
    # Create a song with multiple tracks (like Madonna L/R)
    track_left = Track(name="Left", notes=[
        Note(key=40, start_beat=0, duration_beats=1),
        Note(key=42, start_beat=1, duration_beats=1),
    ])
    track_right = Track(name="Right", notes=[
        Note(key=50, start_beat=0, duration_beats=1),
        Note(key=52, start_beat=1, duration_beats=1),
    ])
    
    song = Song(bpm=120, tracks=[track_left, track_right])
    
    # Add to session
    session = EditorSession()
    source_id = session.add_source("Madonna-style", song)
    
    # Both tracks should be present
    source = session.get_source(source_id)
    assert len(source.song.tracks) == 2
    assert source.song.tracks[0].name == "Left"
    assert source.song.tracks[1].name == "Right"
    
    # Can assign different roles
    session.set_track_role(source_id, 0, "final")  # Left to final
    session.set_track_role(source_id, 1, "mashup_source")  # Right to mashup
    
    # Compose final should only have left track
    final_song = session.compose_final_song()
    assert len(final_song.tracks) == 1
    assert "Left" in final_song.tracks[0].name
    
    # Mashup sources should only have right track
    mashup = session.get_mashup_sources()
    assert len(mashup) == 1
    assert "Right" in mashup[0].name
    
    print("✓ Multi-track preservation tests passed")


if __name__ == "__main__":
    try:
        test_editor_session_basic()
        test_key_range_filter()
        test_multi_track_preservation()
        print("\n✅ All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
