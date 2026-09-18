"""Data model for Note Stack."""

from dataclasses import dataclass, field
from typing import List, Literal
from uuid import uuid4

# Piano synthesis defaults (Desmos melody voice)
PIANO_INTENSITY = 1.0
PIANO_HOLD_SECONDS = 0.8
PIANO_DELAY = True

# Piano keys 1–88. MIDI note number = piano key + 20 (A0 = key 1 = MIDI 21).
MIDI_NOTE_OFFSET = 20

TrackRole = Literal["solo", "base", "adorn", "other"]


def _new_track_id() -> str:
    return uuid4().hex[:8]


def piano_duration_beats(bpm: float, hold_seconds: float = PIANO_HOLD_SECONDS) -> float:
    """Express piano sustain (hold) as a beat length at the song tempo."""
    if bpm <= 0:
        return 0.5
    return max(0.25, hold_seconds * bpm / 60.0)


def fit_durations_to_timbre(
    durations: List[float],
    bpm: float,
    hold_seconds: float = PIANO_HOLD_SECONDS,
) -> List[float]:
    """Keep learned rhythm, but never shorter than the piano attack (~0.172s)."""
    attack_beats = max(0.25, (0.172 * bpm) / 60.0)
    return [max(float(d), attack_beats) for d in durations]


def midi_note_from_key(key: int) -> int:
    return key + MIDI_NOTE_OFFSET


def key_from_midi_note(midi_note: int) -> int:
    return midi_note - MIDI_NOTE_OFFSET


@dataclass
class Note:
    """A note on a piano (key 1-88)."""
    key: int  # Piano key 1-88
    start_beat: float
    duration_beats: float
    velocity: int = 100

    def __post_init__(self) -> None:
        self.key = max(1, min(88, int(self.key)))
        self.velocity = max(1, min(127, int(self.velocity)))
        if self.duration_beats <= 0:
            self.duration_beats = 0.01
        if self.start_beat < 0:
            self.start_beat = 0.0


@dataclass
class Track:
    """A track containing notes."""
    name: str
    intensity: float = 1.0  # I parameter for timbre
    mute: bool = False
    delay: bool = False  # Enable delay voice
    hold_seconds: float = 0.8  # d parameter for sustain
    notes: List[Note] = field(default_factory=list)
    loop_enabled: bool = False
    loop_length_beats: float = 0.0  # 0 = written pattern is the cycle
    id: str = field(default_factory=_new_track_id)
    role: TrackRole = "other"


@dataclass
class Song:
    """A song with multiple tracks."""
    bpm: float = 120.0
    tracks: List[Track] = field(default_factory=list)


def song_span_beats(song: Song, include_muted: bool = False) -> float:
    """Song length in beats.

    Non-looped tracks define when the song ends. Looped tracks then repeat
    until that point. If every active track is looped, fall back to the
    longest written pattern.
    """
    non_loop = 0.0
    looped = 0.0
    for track in song.tracks:
        if track.mute and not include_muted:
            continue
        if not track.notes:
            continue
        written = max(n.start_beat + n.duration_beats for n in track.notes)
        if track.loop_enabled:
            looped = max(looped, written)
        else:
            non_loop = max(non_loop, written)
    return non_loop if non_loop > 0 else looped


def continue_sequence(song: Song, track_index: int, num_notes: int) -> None:
    """Future MidiGPT / sequence-continuation hook."""
    raise NotImplementedError(
        "continue_sequence will be handled by a future AI; MidiGPT is the current prior"
    )


def mix_midi(songs: List[Song]) -> Song:
    """Future MidiGPT / multi-MIDI mix hook."""
    raise NotImplementedError(
        "mix_midi will be handled by a future AI; MidiGPT is the current prior"
    )
