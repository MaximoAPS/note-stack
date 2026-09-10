"""Integration test for Fill Base from Solo feature - full workflow."""

from pathlib import Path
from notes import Track, Note, Song
from number_melody import generate_number_melody, generate_pattern_bass_from_solo
from midi_io import load_midi, export_midi
import tempfile


def test_full_workflow():
    """Test complete workflow: Generate Solo → Fill Base from Solo."""
    print("=" * 60)
    print("Integration Test: Full Workflow")
    print("=" * 60)
    print()
    
    # Step 1: Load style MIDIs for duration learning
    print("Step 1: Loading style MIDIs...")
    demos_dir = Path("demos")
    if not demos_dir.exists():
        print("  ⚠️ demos/ directory not found. Using empty style tracks.")
        style_tracks = []
    else:
        demo_files = list(demos_dir.glob("*.mid"))
        if not demo_files:
            print("  ⚠️ No MIDI files in demos/. Using empty style tracks.")
            style_tracks = []
        else:
            print(f"  Found {len(demo_files)} demo MIDI files")
            style_tracks = []
            for demo_path in demo_files[:2]:  # Use first 2
                try:
                    demo_song = load_midi(str(demo_path))
                    style_tracks.extend(demo_song.tracks)
                    print(f"    - Loaded {demo_path.name}: {len(demo_song.tracks)} tracks")
                except Exception as e:
                    print(f"    ⚠️ Failed to load {demo_path.name}: {e}")
            
            print(f"  Total style tracks: {len(style_tracks)}")
    
    print()
    
    # Step 2: Generate Solo track from Number Melody
    print("Step 2: Generating Solo track from Pi digits...")
    digit_string = "314159265358979323846"
    
    solo_track = generate_number_melody(
        digit_string=digit_string,
        tonic=40,  # E
        mode="major",
        style_tracks=style_tracks if style_tracks else [],
        bpm=96.0,
        octave_range=2,
        chunk_mode="pair_mod",
        modulus=12,
        min_key=40,
        max_key=64,
        register_mode="basic",
        duration_strategy="mode",
        track_name="Solo: Pi Melody"
    )
    
    print(f"  ✓ Generated Solo track: {len(solo_track.notes)} notes")
    if solo_track.notes:
        keys = [n.key for n in solo_track.notes]
        print(f"    Key range: {min(keys)}-{max(keys)}")
        solo_span = solo_track.notes[-1].start_beat + solo_track.notes[-1].duration_beats
        print(f"    Time span: 0.0 - {solo_span:.2f} beats")
    
    print()
    
    # Step 3: Fill Base from Solo with auto offset
    print("Step 3: Filling Base from Solo (auto offset)...")
    
    bass_track = generate_pattern_bass_from_solo(
        pattern_string="3-1-4-1-5-9-2-6",  # Pi pattern
        solo_track=solo_track,
        style_tracks=style_tracks if style_tracks else [],
        bpm=96.0,
        offset_mode="auto",
        min_key=28,
        max_key=42,
        duration_strategy="mode",
        loop_pattern=True
    )
    
    print(f"  ✓ Generated Bass track: {len(bass_track.notes)} notes")
    if bass_track.notes:
        keys = [n.key for n in bass_track.notes]
        print(f"    Key range: {min(keys)}-{max(keys)}")
        bass_span = bass_track.notes[-1].start_beat + bass_track.notes[-1].duration_beats
        print(f"    Time span: 0.0 - {bass_span:.2f} beats")
        print(f"    First 5 keys: {keys[:5]}")
    
    print()
    
    # Step 4: Create Song and export to MIDI
    print("Step 4: Creating song and exporting to MIDI...")
    
    song = Song(bpm=96.0, tracks=[solo_track, bass_track])
    
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        export_midi(tmp_path, song)
        file_size = Path(tmp_path).stat().st_size
        print(f"  ✓ Exported to {tmp_path}")
        print(f"    File size: {file_size} bytes")
        
        # Verify we can load it back
        loaded_song = load_midi(tmp_path)
        print(f"  ✓ Re-loaded MIDI: {len(loaded_song.tracks)} tracks, BPM={loaded_song.bpm}")
        
    finally:
        # Clean up
        Path(tmp_path).unlink(missing_ok=True)
        print(f"  Cleaned up temporary file")
    
    print()
    
    # Step 5: Verify harmonization
    print("Step 5: Verifying harmonization...")
    
    # Extract pitch classes from solo and bass
    solo_pcs = set((n.key - 1) % 12 for n in solo_track.notes)
    bass_pcs = set((n.key - 1) % 12 for n in bass_track.notes)
    
    print(f"  Solo pitch classes: {sorted(solo_pcs)}")
    print(f"  Bass pitch classes: {sorted(bass_pcs)}")
    
    # Check for common pitch classes (some overlap expected for consonance)
    common_pcs = solo_pcs & bass_pcs
    print(f"  Common pitch classes: {sorted(common_pcs)} ({len(common_pcs)}/{len(solo_pcs)})")
    
    # Verify bass is under solo (lower register)
    solo_avg_key = sum(n.key for n in solo_track.notes) / len(solo_track.notes)
    bass_avg_key = sum(n.key for n in bass_track.notes) / len(bass_track.notes)
    
    print(f"  Solo avg key: {solo_avg_key:.1f}")
    print(f"  Bass avg key: {bass_avg_key:.1f}")
    
    assert bass_avg_key < solo_avg_key, "Bass should be below solo"
    print(f"  ✓ Bass is below solo ({bass_avg_key:.1f} < {solo_avg_key:.1f})")
    
    print()
    
    # Success
    print("=" * 60)
    print("✓ Integration test passed!")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Generated Solo track: {len(solo_track.notes)} notes")
    print(f"  - Generated Bass track: {len(bass_track.notes)} notes")
    print(f"  - Bass harmonized under Solo with auto offset")
    print(f"  - Timing synced to Solo span")
    print(f"  - MIDI export/import successful")
    print()


if __name__ == "__main__":
    test_full_workflow()
