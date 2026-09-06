"""Track manipulation helpers for editor workflow."""

from typing import List, Optional, Tuple
from copy import deepcopy
from notes import Track, Note


def filter_notes_by_key_range(
    notes: List[Note],
    key_lo: Optional[int] = None,
    key_hi: Optional[int] = None
) -> List[Note]:
    """
    Filter notes by key range.
    
    Args:
        notes: List of notes to filter
        key_lo: Minimum key (inclusive), or None for no lower bound
        key_hi: Maximum key (inclusive), or None for no upper bound
    
    Returns:
        Filtered list of notes
    """
    if key_lo is None and key_hi is None:
        return notes
    
    filtered = []
    for note in notes:
        if key_lo is not None and note.key < key_lo:
            continue
        if key_hi is not None and note.key > key_hi:
            continue
        filtered.append(note)
    
    return filtered


def get_lowest_notes_per_beat(track: Track, beat_quantize: float = 1.0) -> Track:
    """
    Extract lowest notes from track, one per beat grid.
    
    Useful for creating bass lines from polyphonic sources.
    
    Args:
        track: Source track
        beat_quantize: Grid size in beats (e.g. 1.0 = one note per beat)
    
    Returns:
        New track with lowest notes only
    """
    if not track.notes:
        return deepcopy(track)
    
    # Group notes by beat grid
    beat_groups: dict[int, List[Note]] = {}
    for note in track.notes:
        beat_slot = int(note.start_beat / beat_quantize)
        if beat_slot not in beat_groups:
            beat_groups[beat_slot] = []
        beat_groups[beat_slot].append(note)
    
    # Get lowest note from each group
    bass_notes = []
    for beat_slot in sorted(beat_groups.keys()):
        notes_in_slot = beat_groups[beat_slot]
        lowest = min(notes_in_slot, key=lambda n: n.key)
        bass_notes.append(deepcopy(lowest))
    
    result = deepcopy(track)
    result.notes = bass_notes
    result.name = f"{track.name} (bass)"
    return result


def get_note_clusters(track: Track, max_gap_beats: float = 0.1) -> Track:
    """
    Extract note clusters (chords) from track.
    
    Groups notes that start within max_gap_beats of each other.
    
    Args:
        track: Source track
        max_gap_beats: Maximum time gap to consider notes as a cluster
    
    Returns:
        New track with clustered notes only
    """
    if not track.notes:
        return deepcopy(track)
    
    # Sort notes by start time
    sorted_notes = sorted(track.notes, key=lambda n: n.start_beat)
    
    clusters = []
    current_cluster = [sorted_notes[0]]
    
    for note in sorted_notes[1:]:
        # Check if this note is close enough to the cluster start
        cluster_start = current_cluster[0].start_beat
        if note.start_beat - cluster_start <= max_gap_beats:
            current_cluster.append(note)
        else:
            # Start new cluster if current has multiple notes (is a chord)
            if len(current_cluster) >= 2:
                clusters.extend(current_cluster)
            current_cluster = [note]
    
    # Don't forget last cluster
    if len(current_cluster) >= 2:
        clusters.extend(current_cluster)
    
    result = deepcopy(track)
    result.notes = [deepcopy(n) for n in clusters]
    result.name = f"{track.name} (chords)"
    return result


def thin_notes_rhythm(track: Track, keep_ratio: float = 0.5, seed: int = 42) -> Track:
    """
    Thin out notes randomly to create sparser rhythm.
    
    Useful for creating pluck/adorn patterns.
    
    Args:
        track: Source track
        keep_ratio: Fraction of notes to keep (0.0-1.0)
        seed: Random seed for reproducibility
    
    Returns:
        New track with fewer notes
    """
    if not track.notes:
        return deepcopy(track)
    
    import random
    rng = random.Random(seed)
    
    kept_notes = []
    for note in track.notes:
        if rng.random() < keep_ratio:
            kept_notes.append(deepcopy(note))
    
    result = deepcopy(track)
    result.notes = kept_notes
    result.name = f"{track.name} (thin)"
    return result


def transpose_track(track: Track, semitones: int) -> Track:
    """
    Transpose all notes in track by semitones.
    
    Args:
        track: Source track
        semitones: Number of semitones to transpose (positive = up, negative = down)
    
    Returns:
        New track with transposed notes
    """
    result = deepcopy(track)
    for note in result.notes:
        new_key = note.key + semitones
        # Clamp to valid piano range
        note.key = max(1, min(88, new_key))
    
    return result


def split_by_key_range(track: Track, split_key: int = 40) -> Tuple[Track, Track]:
    """
    Split track into low and high parts.
    
    Args:
        track: Source track
        split_key: Key to split at (notes < split_key go to low track)
    
    Returns:
        (low_track, high_track) tuple
    """
    low_notes = []
    high_notes = []
    
    for note in track.notes:
        if note.key < split_key:
            low_notes.append(deepcopy(note))
        else:
            high_notes.append(deepcopy(note))
    
    low_track = deepcopy(track)
    low_track.notes = low_notes
    low_track.name = f"{track.name} (low)"
    
    high_track = deepcopy(track)
    high_track.notes = high_notes
    high_track.name = f"{track.name} (high)"
    
    return low_track, high_track


def merge_tracks(tracks: List[Track], name: str = "Merged") -> Track:
    """
    Merge multiple tracks into one.
    
    Args:
        tracks: Tracks to merge
        name: Name for merged track
    
    Returns:
        Single track with all notes
    """
    if not tracks:
        return Track(name=name)
    
    merged = Track(name=name)
    
    # Use parameters from first track
    merged.intensity = tracks[0].intensity
    merged.delay = tracks[0].delay
    merged.hold_seconds = tracks[0].hold_seconds
    merged.mute = tracks[0].mute
    
    # Collect all notes
    for track in tracks:
        merged.notes.extend(deepcopy(track.notes))
    
    # Sort by start time
    merged.notes.sort(key=lambda n: n.start_beat)
    
    return merged


def quantize_notes(track: Track, beat_grid: float = 0.25) -> Track:
    """
    Quantize note start times to beat grid.
    
    Args:
        track: Source track
        beat_grid: Grid size in beats (e.g. 0.25 = sixteenth notes at 4/4)
    
    Returns:
        New track with quantized notes
    """
    result = deepcopy(track)
    
    for note in result.notes:
        # Round to nearest grid point
        note.start_beat = round(note.start_beat / beat_grid) * beat_grid
    
    return result
