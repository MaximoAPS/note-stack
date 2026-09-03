"""Data model for Note Stack."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Note:
    """A note on a piano (key 1-88)."""
    key: int  # Piano key 1-88
    start_beat: float
    duration_beats: float
    velocity: int = 100


@dataclass
class Track:
    """A track containing notes."""
    name: str
    intensity: float = 1.0  # I parameter for timbre
    mute: bool = False
    delay: bool = False  # Enable delay voice
    hold_seconds: float = 0.8  # d parameter for sustain
    notes: List[Note] = field(default_factory=list)


@dataclass
class Song:
    """A song with multiple tracks."""
    bpm: float = 120.0
    tracks: List[Track] = field(default_factory=list)


def continue_sequence(song: Song, track_index: int, num_notes: int) -> None:
    """Continue a sequence pattern (stub)."""
    raise NotImplementedError("continue_sequence is not yet implemented")


def mix_midi(songs: List[Song]) -> Song:
    """Mix multiple MIDI songs (stub)."""
    raise NotImplementedError("mix_midi is not yet implemented")
