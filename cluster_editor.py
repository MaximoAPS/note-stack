"""Cluster badge helpers: group simultaneous notes for the Studio editor."""

from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple

from notes import Note


@dataclass
class NoteCluster:
    """A cluster of simultaneous notes with a duration."""
    start_beat: float
    duration_beats: float
    keys: List[int]
    velocity: int = 100


def notes_to_clusters(notes: List[Note]) -> List[NoteCluster]:
    """Group notes by start_beat into clusters."""
    if not notes:
        return []

    groups = defaultdict(list)
    for note in notes:
        groups[note.start_beat].append(note)

    clusters = []
    for start_beat in sorted(groups.keys()):
        group_notes = groups[start_beat]
        durations = [n.duration_beats for n in group_notes]
        duration = max(set(durations), key=durations.count)
        keys = [n.key for n in group_notes]
        velocity = group_notes[0].velocity
        clusters.append(NoteCluster(start_beat, duration, keys, velocity))

    return clusters


def clusters_to_notes(clusters: List[NoteCluster]) -> List[Note]:
    """Convert clusters back to individual notes."""
    notes = []
    for cluster in clusters:
        for key in cluster.keys:
            notes.append(Note(
                key=key,
                start_beat=cluster.start_beat,
                duration_beats=cluster.duration_beats,
                velocity=max(1, cluster.velocity),
            ))
    return notes


def parse_cluster_string(
    cluster_str: str,
    default_duration: float = 0.5,
) -> Tuple[List[NoteCluster], List[str]]:
    """Parse cluster string like '35-35,36-38-35' into clusters.

    Syntax:
    - Dash (-) separates clusters
    - Comma (,) separates keys within a cluster
    - Each cluster gets default_duration beats

    Example: '35-35,36-38-35' creates:
    1. [35] at beat 0.0
    2. [35,36] at beat 0.5
    3. [38] at beat 1.0
    4. [35] at beat 1.5

    Returns:
        (clusters, warnings) - list of clusters and list of warning messages
    """
    clusters = []
    warnings = []
    current_beat = 0.0

    parts = cluster_str.strip().split('-')
    for part in parts:
        if not part.strip():
            continue

        key_strs = part.split(',')
        keys = []
        for k in key_strs:
            token = k.strip()
            if not token:
                continue
            try:
                key_val = int(token)
            except ValueError:
                warnings.append(f"⚠️ Ignored invalid key '{token}' (not an integer)")
                continue

            if key_val < 1 or key_val > 88:
                warnings.append(f"⚠️ Key {key_val} is outside the piano range 1–88")
                key_val = max(1, min(88, key_val))

            keys.append(key_val)

            if key_val < 20:
                warnings.append(
                    f"⚠️ Key {key_val} is very low (near bottom of piano, barely audible)"
                )
            elif key_val > 80:
                warnings.append(f"⚠️ Key {key_val} is very high (top of piano)")

        if keys:
            clusters.append(NoteCluster(
                start_beat=current_beat,
                duration_beats=default_duration,
                keys=keys,
                velocity=100,
            ))
            current_beat += default_duration

    return clusters, warnings


def format_duration_label(duration: float) -> str:
    """Format duration as fraction like '1/4', '1/2', '1', '2'."""
    if duration >= 1.0:
        if duration == int(duration):
            return str(int(duration))
        return f"{duration:.2f}"

    if abs(duration - 0.25) < 0.01:
        return "1/4"
    if abs(duration - 0.5) < 0.01:
        return "1/2"
    if abs(duration - 0.75) < 0.01:
        return "3/4"
    return f"{duration:.2f}"
