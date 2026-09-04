"""MIDI import and export functionality."""

import mido
from typing import List, Dict
from notes import Song, Track, Note


def midi_note_to_key(midi_note: int) -> int:
    """Convert MIDI note number to piano key (1-88)."""
    return midi_note - 20


def key_to_midi_note(key: int) -> int:
    """Convert piano key (1-88) to MIDI note number."""
    return key + 20


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
        # Track active notes: (channel, note) -> start_tick
        active_notes: Dict[tuple, int] = {}
        
        for msg in track:
            current_time += msg.time
            
            if msg.type == 'note_on' and msg.velocity > 0:
                channel = msg.channel if hasattr(msg, 'channel') else 0
                active_notes[(channel, msg.note)] = current_time
            
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                channel = msg.channel if hasattr(msg, 'channel') else 0
                key_tuple = (channel, msg.note)
                
                if key_tuple in active_notes:
                    start_tick = active_notes.pop(key_tuple)
                    duration_ticks = current_time - start_tick
                    
                    # Convert to beats
                    start_beat = start_tick / ticks_per_beat
                    duration_beats = duration_ticks / ticks_per_beat
                    
                    # Convert MIDI note to piano key
                    piano_key = midi_note_to_key(msg.note)
                    
                    # Only include valid piano keys (1-88)
                    if 1 <= piano_key <= 88:
                        velocity = msg.velocity if hasattr(msg, 'velocity') else 100
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


def export_midi(filename: str, song: Song) -> None:
    """Export Song to MIDI file."""
    mid = mido.MidiFile(ticks_per_beat=480)
    
    # Set tempo
    tempo_track = mido.MidiTrack()
    mid.tracks.append(tempo_track)
    tempo_microseconds = int(60000000 / song.bpm)
    tempo_track.append(mido.MetaMessage('set_tempo', tempo=tempo_microseconds, time=0))
    
    # Create a track for each song track
    for track_idx, track in enumerate(song.tracks):
        if track.mute:
            continue
        
        midi_track = mido.MidiTrack()
        mid.tracks.append(midi_track)
        
        # Sort notes by start time
        sorted_notes = sorted(track.notes, key=lambda n: n.start_beat)
        
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
    
    mid.save(filename)
