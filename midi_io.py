"""MIDI import and export functionality."""

import io
from typing import Dict, List

import mido

from notes import Note, Song, Track, key_from_midi_note, midi_note_from_key, song_span_beats
from track_helpers import expand_looped_track


def midi_note_to_key(midi_note: int) -> int:
    """MIDI note number → piano key 1–88. MIDI 21 (A0) = key 1. MIDI 60 (C4) = key 40."""
    return key_from_midi_note(midi_note)


def key_to_midi_note(key: int) -> int:
    """Piano key 1–88 → MIDI note number. Key 40 (C4) = MIDI 60. Key 49 (A4) = MIDI 69."""
    return midi_note_from_key(key)


def load_midi(filename: str) -> Song:
    """
    Load MIDI file and convert to Song.
    Split by channels if multiple channels present.
    """
    mid = mido.MidiFile(filename)
    
    # Extract tempo (default 120 BPM)
    bpm = 120.0
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'set_tempo':
                # Tempo is in microseconds per beat
                bpm = 60000000.0 / msg.tempo
                break
        if bpm != 120.0:
            break
    
    # Get ticks per beat
    ticks_per_beat = mid.ticks_per_beat
    
    # Collect notes by channel
    channel_notes: Dict[int, List[Note]] = {}
    
    for track in mid.tracks:
        current_time = 0
        # Track active notes: (channel, note) -> (start_tick, on_velocity)
        active_notes: Dict[tuple, tuple] = {}
        
        for msg in track:
            current_time += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                channel = msg.channel if hasattr(msg, 'channel') else 0
                # Store both start_tick and note_on velocity
                active_notes[(channel, msg.note)] = (current_time, msg.velocity)
            
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                channel = msg.channel if hasattr(msg, 'channel') else 0
                key_tuple = (channel, msg.note)
                
                if key_tuple in active_notes:
                    # Retrieve stored start_tick and on_velocity
                    start_tick, on_velocity = active_notes.pop(key_tuple)
                    duration_ticks = current_time - start_tick
                    
                    # Convert to beats
                    start_beat = start_tick / ticks_per_beat
                    duration_beats = duration_ticks / ticks_per_beat
                    
                    # Convert MIDI note to piano key
                    piano_key = midi_note_to_key(msg.note)
                    
                    # Only include valid piano keys (1-88)
                    if 1 <= piano_key <= 88:
                        # Use the stored note_on velocity, clamped to valid range
                        velocity = max(1, min(127, on_velocity))
                        note = Note(
                            key=piano_key,
                            start_beat=start_beat,
                            duration_beats=duration_beats,
                            velocity=velocity
                        )
                        
                        if channel not in channel_notes:
                            channel_notes[channel] = []
                        channel_notes[channel].append(note)
    
    # Create tracks
    tracks = []
    if len(channel_notes) == 0:
        # No notes found
        tracks.append(Track(name="Track 1", notes=[]))
    elif len(channel_notes) == 1:
        # Single channel - one track
        channel = list(channel_notes.keys())[0]
        tracks.append(Track(name="Track 1", notes=channel_notes[channel]))
    else:
        # Multiple channels - separate tracks
        for channel in sorted(channel_notes.keys()):
            track_name = f"Channel {channel + 1}"
            tracks.append(Track(name=track_name, notes=channel_notes[channel]))
    
    return Song(bpm=bpm, tracks=tracks)


def song_to_midi(song: Song) -> mido.MidiFile:
    """Build a MIDI file from a Song, expanding looped tracks."""
    mid = mido.MidiFile(ticks_per_beat=480)

    tempo_track = mido.MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_microseconds = int(60000000 / song.bpm)
    tempo_track.append(mido.MetaMessage('set_tempo', tempo=tempo_microseconds, time=0))

    song_end = song_span_beats(song, include_muted=False)

    for track in song.tracks:
        if track.mute:
            continue

        expanded = expand_looped_track(track, song_end)

        midi_track = mido.MidiTrack()
        mid.tracks.append(midi_track)

        sorted_notes = sorted(expanded.notes, key=lambda n: n.start_beat)
        
        # Convert notes to MIDI events
        events = []
        for note in sorted_notes:
            start_tick = int(note.start_beat * mid.ticks_per_beat)
            end_tick = int((note.start_beat + note.duration_beats) * mid.ticks_per_beat)
            midi_note = key_to_midi_note(note.key)
            
            events.append((start_tick, 'note_on', midi_note, note.velocity))
            events.append((end_tick, 'note_off', midi_note, 0))
        
        # Sort events by time
        events.sort(key=lambda e: e[0])
        
        # Convert absolute times to delta times
        current_tick = 0
        for abs_tick, event_type, midi_note, velocity in events:
            delta = abs_tick - current_tick
            
            if event_type == 'note_on':
                midi_track.append(mido.Message('note_on', note=midi_note, 
                                              velocity=velocity, time=delta))
            else:
                midi_track.append(mido.Message('note_off', note=midi_note, 
                                              velocity=velocity, time=delta))
            
            current_tick = abs_tick

    return mid


def song_to_midi_bytes(song: Song) -> bytes:
    """Export song to in-memory MIDI bytes."""
    mid = song_to_midi(song)
    buf = io.BytesIO()
    mid.save(file=buf)
    return buf.getvalue()


def export_midi(filename: str, song: Song) -> None:
    """Export Song to MIDI file."""
    song_to_midi(song).save(filename)
