"""MidiGPT — built-in duration/jump prior used when no style pack is trained.

This is the current fallback "AI" for Number Melody and Pattern generators.
A future model can replace these histograms without changing call sites.
"""

from typing import Dict, List


def builtin_duration_model() -> Dict[int, List[float]]:
    """Typical piano rhythms keyed by interval (semitones)."""
    return {
        0: [0.5, 0.5, 1.0, 1.0],
        1: [0.5, 0.25, 0.5],
        -1: [0.5, 0.25, 0.5],
        2: [0.5, 1.0, 0.5],
        -2: [0.5, 1.0, 0.5],
        3: [1.0, 0.5],
        -3: [1.0, 0.5],
        4: [1.0, 0.5, 1.0],
        -4: [1.0, 0.5],
        5: [1.0, 2.0],
        -5: [1.0, 0.5],
        7: [1.0, 2.0, 1.0],
        -7: [1.0, 0.5],
        12: [2.0, 1.0],
        -12: [1.0, 0.5],
    }


def builtin_jump_model() -> Dict[int, int]:
    """Typical piano interval frequencies for octave disambiguation."""
    return {
        0: 40,
        1: 18,
        -1: 16,
        2: 22,
        -2: 20,
        3: 10,
        -3: 8,
        4: 12,
        -4: 8,
        5: 14,
        -5: 10,
        7: 16,
        -7: 12,
        12: 6,
        -12: 5,
    }


