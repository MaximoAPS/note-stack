"""Pattern generation for AI tracks (Phase 1 heuristics)."""

from typing import List, Optional
from copy import deepcopy
import random

from notes import Track, Note
from track_helpers import (
    filter_notes_by_key_range,
    get_lowest_notes_per_beat,
    get_note_clusters,
    thin_notes_rhythm,
    quantize_notes,
    merge_tracks
)


def generate_bass_pattern(
    donor_tracks: List[Track],
    key_range: tuple[int, int] = (1, 28),
    num_beats: float = 16.0,
    bpm: float = 120.0,
    intensity: float = 2.0,
    hold_seconds: float = 2.0
) -> Track:
    """
    Generate bass line from donor tracks, filtered to key range.
    
    Phase 1 V1 heuristic: Extract lowest notes from donors in range,
    thin out to beat grid.
    
    Args:
        donor_tracks: Source tracks to extract patterns from
        key_range: (min_key, max_key) for bass range
        num_beats: Target length in beats
        bpm: Tempo
        intensity: Intensity parameter (2.0 typical for bass)
        hold_seconds: Hold parameter for bass sustain
    
    Returns:
        Generated bass track
    """
    if not donor_tracks:
        return Track(
            name="Bass (AI V1)",
            intensity=intensity,
            hold_seconds=hold_seconds,
            notes=[]
        )
    
    # Merge all donor tracks
    merged = merge_tracks(donor_tracks, "Bass Source")
    
    # Filter to bass key range
    bass_notes = filter_notes_by_key_range(
        merged.notes,
        key_lo=key_range[0],
        key_hi=key_range[1]
    )
    
    # If no notes in range, transpose some notes down
    if not bass_notes and merged.notes:
        # Take lowest notes and transpose down to bass range
        temp_track = Track(name="temp", notes=merged.notes)
        lowest_track = get_lowest_notes_per_beat(temp_track, beat_quantize=1.0)
        
        # Find average key and transpose to bass range
        if lowest_track.notes:
            avg_key = sum(n.key for n in lowest_track.notes) / len(lowest_track.notes)
            target_key = (key_range[0] + key_range[1]) / 2
            transpose_semitones = int(target_key - avg_key)
            
            for note in lowest_track.notes:
                new_key = note.key + transpose_semitones
                if key_range[0] <= new_key <= key_range[1]:
                    transposed = deepcopy(note)
                    transposed.key = new_key
                    bass_notes.append(transposed)
    
    # Create track and get lowest notes per beat
    temp_track = Track(name="Bass", notes=bass_notes)
    bass_track = get_lowest_notes_per_beat(temp_track, beat_quantize=1.0)
    
    # Quantize to grid
    bass_track = quantize_notes(bass_track, beat_grid=0.5)
    
    # Trim to target length
    bass_track.notes = [n for n in bass_track.notes if n.start_beat < num_beats]
    
    # Set parameters
    bass_track.name = "Bass (AI V1 heuristic)"
    bass_track.intensity = intensity
    bass_track.hold_seconds = hold_seconds
    bass_track.delay = False
    
    return bass_track


def generate_chord_pattern(
    donor_tracks: List[Track],
    key_range: tuple[int, int] = (29, 52),
    num_beats: float = 16.0,
    bpm: float = 120.0,
    intensity: float = 1.5,
    hold_seconds: float = 1.5
) -> Track:
    """
    Generate chord pattern from donor tracks.
    
    Phase 1 V1 heuristic: Extract note clusters from donors,
    quantize to grid.
    
    Args:
        donor_tracks: Source tracks to extract patterns from
        key_range: (min_key, max_key) for chord range
        num_beats: Target length in beats
        bpm: Tempo
        intensity: Intensity parameter
        hold_seconds: Hold parameter
    
    Returns:
        Generated chord track
    """
    if not donor_tracks:
        return Track(
            name="Chords (AI V1)",
            intensity=intensity,
            hold_seconds=hold_seconds,
            notes=[]
        )
    
    # Merge all donor tracks
    merged = merge_tracks(donor_tracks, "Chord Source")
    
    # Filter to chord key range
    chord_notes = filter_notes_by_key_range(
        merged.notes,
        key_lo=key_range[0],
        key_hi=key_range[1]
    )
    
    # Extract clusters (chords)
    temp_track = Track(name="Chords", notes=chord_notes)
    chord_track = get_note_clusters(temp_track, max_gap_beats=0.2)
    
    # Quantize to grid
    chord_track = quantize_notes(chord_track, beat_grid=1.0)
    
    # Trim to target length
    chord_track.notes = [n for n in chord_track.notes if n.start_beat < num_beats]
    
    # Set parameters
    chord_track.name = "Chords (AI V1 heuristic)"
    chord_track.intensity = intensity
    chord_track.hold_seconds = hold_seconds
    chord_track.delay = False
    
    return chord_track


def generate_adorn_pluck(
    donor_tracks: List[Track],
    key_range: tuple[int, int] = (45, 72),
    num_beats: float = 16.0,
    bpm: float = 120.0,
    intensity: float = 1.0,
    hold_seconds: float = 0.5
) -> Track:
    """
    Generate adorn/pluck decoration.
    
    Phase 1 V1 heuristic: Extract sparse high notes from donors,
    rhythm variation.
    
    Args:
        donor_tracks: Source tracks to extract patterns from
        key_range: (min_key, max_key) for pluck range
        num_beats: Target length in beats
        bpm: Tempo
        intensity: Intensity parameter
        hold_seconds: Hold parameter (short for plucks)
    
    Returns:
        Generated adorn track
    """
    if not donor_tracks:
        return Track(
            name="Adorn Pluck (AI V1)",
            intensity=intensity,
            hold_seconds=hold_seconds,
            notes=[]
        )
    
    # Merge all donor tracks
    merged = merge_tracks(donor_tracks, "Adorn Source")
    
    # Filter to pluck key range
    pluck_notes = filter_notes_by_key_range(
        merged.notes,
        key_lo=key_range[0],
        key_hi=key_range[1]
    )
    
    # Thin out to create sparse rhythm
    temp_track = Track(name="Adorn", notes=pluck_notes)
    adorn_track = thin_notes_rhythm(temp_track, keep_ratio=0.3, seed=42)
    
    # Quantize to finer grid for rhythm
    adorn_track = quantize_notes(adorn_track, beat_grid=0.25)
    
    # Trim to target length
    adorn_track.notes = [n for n in adorn_track.notes if n.start_beat < num_beats]
    
    # Set parameters
    adorn_track.name = "Adorn Pluck (AI V1 heuristic)"
    adorn_track.intensity = intensity
    adorn_track.hold_seconds = hold_seconds
    adorn_track.delay = True  # Delay adds space to plucks
    
    return adorn_track


def generate_harmony(
    donor_tracks: List[Track],
    key_range: tuple[int, int] = (45, 72),
    num_beats: float = 16.0,
    bpm: float = 120.0,
    harmony_interval: int = 7,  # fifth
    intensity: float = 1.0,
    hold_seconds: float = 0.8
) -> Track:
    """
    Generate harmony line from donor tracks.
    
    Phase 1 V1 heuristic: Extract melody-like notes and harmonize
    by interval.
    
    Args:
        donor_tracks: Source tracks to extract patterns from
        key_range: (min_key, max_key) for harmony range
        num_beats: Target length in beats
        bpm: Tempo
        harmony_interval: Semitones to harmonize (7=fifth, 4=third, etc.)
        intensity: Intensity parameter
        hold_seconds: Hold parameter
    
    Returns:
        Generated harmony track
    """
    if not donor_tracks:
        return Track(
            name="Harmony (AI V1)",
            intensity=intensity,
            hold_seconds=hold_seconds,
            notes=[]
        )
    
    # Merge all donor tracks
    merged = merge_tracks(donor_tracks, "Harmony Source")
    
    # Filter to key range
    melody_notes = filter_notes_by_key_range(
        merged.notes,
        key_lo=key_range[0],
        key_hi=key_range[1]
    )
    
    # Thin out to get melodic line
    temp_track = Track(name="Melody", notes=melody_notes)
    melody_track = thin_notes_rhythm(temp_track, keep_ratio=0.5, seed=123)
    
    # Create harmony by transposing
    harmony_notes = []
    for note in melody_track.notes:
        harmony_note = deepcopy(note)
        harmony_note.key += harmony_interval
        
        # Keep in valid range
        if 1 <= harmony_note.key <= 88:
            harmony_notes.append(harmony_note)
    
    # Quantize
    harmony_track = Track(name="Harmony", notes=harmony_notes)
    harmony_track = quantize_notes(harmony_track, beat_grid=0.5)
    
    # Trim to target length
    harmony_track.notes = [n for n in harmony_track.notes if n.start_beat < num_beats]
    
    # Set parameters
    harmony_track.name = f"Harmony (AI V1 heuristic, +{harmony_interval})"
    harmony_track.intensity = intensity
    harmony_track.hold_seconds = hold_seconds
    harmony_track.delay = True
    
    return harmony_track


# Pattern generator registry for UI
PATTERN_GENERATORS = {
    "bass": {
        "name": "Bass Line",
        "description": "Low bass line (keys 1-28)",
        "default_range": (1, 28),
        "generator": generate_bass_pattern,
        "default_params": {"intensity": 2.0, "hold_seconds": 2.0}
    },
    "chords": {
        "name": "Chord Base",
        "description": "Chord progression (keys 29-52)",
        "default_range": (29, 52),
        "generator": generate_chord_pattern,
        "default_params": {"intensity": 1.5, "hold_seconds": 1.5}
    },
    "adorn_pluck": {
        "name": "Adorn Pluck",
        "description": "Sparse decorative plucks (keys 45-72)",
        "default_range": (45, 72),
        "generator": generate_adorn_pluck,
        "default_params": {"intensity": 1.0, "hold_seconds": 0.5}
    },
    "harmony": {
        "name": "Harmony Line",
        "description": "Harmonized melody (keys 45-72)",
        "default_range": (45, 72),
        "generator": generate_harmony,
        "default_params": {"intensity": 1.0, "hold_seconds": 0.8, "harmony_interval": 7}
    }
}
