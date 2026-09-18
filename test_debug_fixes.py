#!/usr/bin/env python3
"""Regression tests for the debug/refactor pass."""

from cluster_editor import parse_cluster_string
from midi_gpt import builtin_duration_model
from midi_io import export_midi, load_midi, song_to_midi_bytes
from notes import (
    Note,
    Song,
    Track,
    fit_durations_to_timbre,
    key_from_midi_note,
    midi_note_from_key,
    piano_duration_beats,
    song_span_beats,
)
from number_melody import map_values_to_keys, parse_pattern_digits
from pattern_generators import run_pattern_generator
from synth import _stable_seed, song_to_wav_bytes
from track_helpers import expand_looped_track


def test_piano_key_is_not_midi():
    assert midi_note_from_key(40) == 60  # C4
    assert midi_note_from_key(49) == 69  # A4
    assert key_from_midi_note(60) == 40
    assert key_from_midi_note(21) == 1


def test_midigpt_fallback_and_timbre_duration():
    from number_melody import generate_number_melody

    track = generate_number_melody(
        digit_string="31415",
        tonic=40,
        mode="major",
        style_tracks=[],
        bpm=96.0,
    )
    assert track.role == "solo"
    assert track.hold_seconds == 0.8
    assert track.intensity == 1.0
    assert track.notes
    assert builtin_duration_model()
    fitted = fit_durations_to_timbre([0.1, 0.5], bpm=96.0)
    assert fitted[0] >= 0.25
    assert piano_duration_beats(96.0) == 0.8 * 96.0 / 60.0


def test_loop_repeats_until_song_end():
    bass = Track(
        name="bass",
        role="base",
        loop_enabled=True,
        loop_length_beats=0.0,
        notes=[
            Note(key=28, start_beat=0.0, duration_beats=1.0),
            Note(key=32, start_beat=1.0, duration_beats=1.0),
        ],
    )
    solo = Track(
        name="solo",
        role="solo",
        notes=[Note(key=52, start_beat=0.0, duration_beats=8.0)],
    )
    song = Song(bpm=96, tracks=[bass, solo])
    end = song_span_beats(song)
    assert end == 8.0
    expanded = expand_looped_track(bass, end)
    last = max(n.start_beat + n.duration_beats for n in expanded.notes)
    assert last > 2.0
    assert last <= 8.0 + 1e-6


def test_parse_pattern_digits():
    assert parse_pattern_digits("3-1-4-1-5") == [3, 1, 4, 1, 5]
    assert parse_pattern_digits("3,1,4,1,5") == [3, 1, 4, 1, 5]
    assert parse_pattern_digits("") == []


def test_min_key_is_respected():
    keys = map_values_to_keys(
        values=[0, 1, 2],
        tonic=20,
        mode="chromatic",
        chunk_mode="single",
        modulus=10,
        octave_range=2,
        min_key=28,
        max_key=42,
    )
    assert all(28 <= k <= 42 for k in keys), keys


def test_run_pattern_generator_returns_track():
    donor = Track(
        name="🎵 Solo: test",
        notes=[
            Note(key=40, start_beat=0.0, duration_beats=1.0),
            Note(key=44, start_beat=1.0, duration_beats=1.0),
            Note(key=47, start_beat=2.0, duration_beats=1.0),
        ],
    )
    result = run_pattern_generator(
        "bass_line", [donor], bpm=96, key_lo=1, key_hi=28
    )
    assert isinstance(result, Track)
    assert all(1 <= n.key <= 28 for n in result.notes)


def test_midi_export_expands_loops():
    pattern = Track(
        name="Loop Bass",
        loop_enabled=True,
        loop_length_beats=0.0,
        notes=[
            Note(key=28, start_beat=0.0, duration_beats=1.0),
            Note(key=32, start_beat=1.0, duration_beats=1.0),
        ],
    )
    melody = Track(
        name="Melody",
        notes=[Note(key=52, start_beat=0.0, duration_beats=8.0)],
    )
    song = Song(bpm=120, tracks=[pattern, melody])

    expanded = expand_looped_track(pattern, song_span_beats(song))
    assert len(expanded.notes) > len(pattern.notes)

    data = song_to_midi_bytes(song)
    assert data[:4] == b"MThd"
    assert len(data) > 20

    loaded = load_midi_from_bytes(data)
    looped = next(t for t in loaded.tracks if t.notes and min(n.key for n in t.notes) <= 32)
    assert len(looped.notes) > 2


def load_midi_from_bytes(data: bytes) -> Song:
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as handle:
        handle.write(data)
        path = handle.name
    try:
        return load_midi(path)
    finally:
        os.unlink(path)


def test_wav_bytes_are_valid():
    song = Song(
        bpm=120,
        tracks=[Track(name="t", notes=[Note(key=49, start_beat=0, duration_beats=0.5)])],
    )
    payload = song_to_wav_bytes(song)
    assert payload[:4] == b"RIFF"
    assert b"WAVE" in payload[:16]


def test_stable_seed_is_deterministic():
    assert _stable_seed(1, 49, 0.0, 3) == _stable_seed(1, 49, 0.0, 3)
    assert _stable_seed("detune", 0, 40, 0.5, 2) != _stable_seed(0, 40, 0.5, 2)


def test_parse_cluster_out_of_range_warns():
    clusters, warnings = parse_cluster_string("0-90", 0.5)
    assert len(clusters) == 2
    assert any("outside the piano range" in w for w in warnings)
    assert all(1 <= key <= 88 for c in clusters for key in c.keys)


def test_note_clamps_invalid_values():
    note = Note(key=0, start_beat=-1, duration_beats=0, velocity=0)
    assert note.key == 1
    assert note.start_beat == 0.0
    assert note.duration_beats > 0
    assert note.velocity == 1


def test_export_midi_roundtrip_file(tmp_path=None):
    import os
    import tempfile

    song = Song(
        bpm=100,
        tracks=[Track(name="t", notes=[Note(key=40, start_beat=0, duration_beats=1)])],
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as handle:
        path = handle.name
    try:
        export_midi(path, song)
        loaded = load_midi(path)
        assert loaded.tracks
        assert loaded.tracks[0].notes
        assert loaded.tracks[0].notes[0].key == 40
    finally:
        os.unlink(path)


def main():
    tests = [
        test_piano_key_is_not_midi,
        test_midigpt_fallback_and_timbre_duration,
        test_loop_repeats_until_song_end,
        test_parse_pattern_digits,
        test_min_key_is_respected,
        test_run_pattern_generator_returns_track,
        test_midi_export_expands_loops,
        test_wav_bytes_are_valid,
        test_stable_seed_is_deterministic,
        test_parse_cluster_out_of_range_warns,
        test_note_clamps_invalid_values,
        test_export_midi_roundtrip_file,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"OK {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
            raise
    print(f"\nPassed: {len(tests) - failed}/{len(tests)}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
