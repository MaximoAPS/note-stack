#!/usr/bin/env python3
"""Test cluster badge functionality."""

from app import (
    parse_cluster_string,
    format_duration_label,
    notes_to_clusters,
    clusters_to_notes,
    NoteCluster
)
from notes import Note

print("Testing cluster badge functionality...")

# Test 1: Parse cluster string
clusters = parse_cluster_string("35-35,36-38-35", 0.5)
assert len(clusters) == 4
assert clusters[0].keys == [35]
assert clusters[1].keys == [35, 36]
assert clusters[2].keys == [38]
assert clusters[3].keys == [35]
print("✓ Parse cluster string: PASSED")

# Test 2: Format duration labels
assert format_duration_label(0.25) == "1/4"
assert format_duration_label(0.5) == "1/2"
assert format_duration_label(1.0) == "1"
print("✓ Format duration labels: PASSED")

# Test 3: Notes to clusters
notes = [
    Note(key=35, start_beat=0.0, duration_beats=0.5),
    Note(key=35, start_beat=0.5, duration_beats=0.5),
    Note(key=36, start_beat=0.5, duration_beats=0.5),
    Note(key=38, start_beat=1.0, duration_beats=0.5),
]
clusters = notes_to_clusters(notes)
assert len(clusters) == 3
assert len(clusters[1].keys) == 2  # Chord
print("✓ Notes to clusters: PASSED")

# Test 4: Round trip
back = clusters_to_notes(clusters)
assert len(back) == 4
print("✓ Clusters to notes: PASSED")

print("\n✓ ALL TESTS PASSED!")
