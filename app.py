"""Note Stack V1 - Piano synthesis Streamlit app."""

import streamlit as st
import numpy as np
import os
from pathlib import Path
import io
import pandas as pd
import altair as alt

from notes import Song, Track, Note
from synth import synthesize_song, export_wav
from midi_io import load_midi, export_midi


def create_piano_song_preset() -> Song:
    """Create the Piano Song preset from Desmos graph."""
    bpm = 160
    
    # Track 1: Melody (I=1, delay=on, d=0.8)
    tempo_list_1 = [i * 0.5 for i in range(0, 30)] + [15, 16]
    notes_1 = [57,54,49,54,57,54,49,54,57,52,49,52,57,52,49,52,
               57,53,49,53,57,53,49,53,57,53,49,53,57,62]
    
    track1_notes = []
    for i, key in enumerate(notes_1):
        start_sec = tempo_list_1[i]
        end_sec = tempo_list_1[i + 1]
        duration_sec = end_sec - start_sec
        
        # Convert to beats: beats = seconds * bpm / 60
        start_beat = start_sec * bpm / 60
        duration_beats = duration_sec * bpm / 60
        
        track1_notes.append(Note(key=key, start_beat=start_beat, 
                                duration_beats=duration_beats))
    
    track1 = Track(name="Melody", intensity=1.0, delay=True, 
                   hold_seconds=0.8, notes=track1_notes)
    
    # Track 2: Bass low (I=2, delay=off, d=2)
    tempo_list_2 = [0, 4, 8, 12, 14, 16]
    notes_2 = [18, 21, 25, 25, 25]
    
    track2_notes = []
    for i, key in enumerate(notes_2):
        start_sec = tempo_list_2[i]
        end_sec = tempo_list_2[i + 1]
        duration_sec = end_sec - start_sec
        
        start_beat = start_sec * bpm / 60
        duration_beats = duration_sec * bpm / 60
        
        track2_notes.append(Note(key=key, start_beat=start_beat, 
                                duration_beats=duration_beats))
    
    track2 = Track(name="Bass Low", intensity=2.0, delay=False, 
                   hold_seconds=2.0, notes=track2_notes)
    
    # Track 3: Bass high (I=2, delay=off, d=2)
    notes_3 = [30, 33, 37, 37, 37]
    
    track3_notes = []
    for i, key in enumerate(notes_3):
        start_sec = tempo_list_2[i]
        end_sec = tempo_list_2[i + 1]
        duration_sec = end_sec - start_sec
        
        start_beat = start_sec * bpm / 60
        duration_beats = duration_sec * bpm / 60
        
        track3_notes.append(Note(key=key, start_beat=start_beat, 
                                duration_beats=duration_beats))
    
    track3 = Track(name="Bass High", intensity=2.0, delay=False, 
                   hold_seconds=2.0, notes=track3_notes)
    
    # Track 4: Arpeggio (I=2, delay=on, d=0.5)
    tempo_list_3 = [16 + i * 0.5 for i in range(65)]
    notes_4 = [18,25,30,25,33,30,25,30,18,25,33,25,33,30,25,30,
               21,28,33,28,37,33,28,33,21,28,33,28,37,33,28,33,
               26,33,38,33,42,38,33,38,26,33,38,33,42,38,33,38,
               28,35,40,35,44,40,35,28,28,32,37,32,41,37,32,25,
               18,25,30]
    
    track4_notes = []
    for i, key in enumerate(notes_4):
        start_sec = tempo_list_3[i]
        end_sec = tempo_list_3[i + 1]
        duration_sec = end_sec - start_sec
        
        start_beat = start_sec * bpm / 60
        duration_beats = duration_sec * bpm / 60
        
        track4_notes.append(Note(key=key, start_beat=start_beat, 
                                duration_beats=duration_beats))
    
    track4 = Track(name="Arpeggio", intensity=2.0, delay=True, 
                   hold_seconds=0.5, notes=track4_notes)
    
    return Song(bpm=bpm, tracks=[track1, track2, track3, track4])


def get_demo_options():
    """Get list of available demos."""
    demos = ["Piano Song (Desmos)"]
    
    demos_dir = Path("demos")
    if demos_dir.exists():
        for midi_file in sorted(demos_dir.glob("*.mid")):
            demos.append(f"MAESTRO — {midi_file.stem}")
    
    return demos


def render_timeline_chart(track: Track, bpm: float):
    """Render a timeline chart for a track."""
    if not track.notes:
        st.write("No notes in this track")
        return
    
    # Prepare data for Altair
    chart_data = []
    for note in track.notes:
        chart_data.append({
            'start': note.start_beat,
            'end': note.start_beat + note.duration_beats,
            'key': note.key,
            'velocity': note.velocity
        })
    
    df = pd.DataFrame(chart_data)
    
    # Create timeline chart
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('start:Q', title='Beat'),
        x2='end:Q',
        y=alt.Y('key:Q', scale=alt.Scale(domain=[1, 88]), title='Piano Key'),
        color=alt.Color('velocity:Q', scale=alt.Scale(scheme='viridis')),
        tooltip=['key:Q', 'start:Q', 'end:Q', 'velocity:Q']
    ).properties(
        width=700,
        height=200
    )
    
    st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config(page_title="Note Stack V1", layout="wide")
    
    st.title("Note Stack V1")
    st.caption("Piano key numbers (1-88) on timeline tracks. "
              "Timbre synthesis from Desmos Piano Song graph. "
              "MAESTRO excerpts © CC BY-NC-SA 4.0")
    
    # Initialize session state
    if 'song' not in st.session_state:
        st.session_state.song = Song(bpm=120, tracks=[Track(name="Track 1")])
    
    # Demo selector
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        demo_options = get_demo_options()
        selected_demo = st.selectbox("Demo", demo_options)
    
    with col2:
        if st.button("Load Piano Song"):
            st.session_state.song = create_piano_song_preset()
            st.rerun()
    
    with col3:
        if st.button("Load Demo"):
            if selected_demo == "Piano Song (Desmos)":
                st.session_state.song = create_piano_song_preset()
                st.rerun()
            else:
                # Load MIDI file
                filename = selected_demo.replace("MAESTRO — ", "")
                midi_path = Path("demos") / f"{filename}.mid"
                if midi_path.exists():
                    st.session_state.song = load_midi(str(midi_path))
                    st.rerun()
    
    # MIDI file upload
    uploaded_file = st.file_uploader("Upload MIDI file", type=["mid", "midi"])
    if uploaded_file is not None:
        try:
            # Write to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name
            
            # Load the MIDI file
            st.session_state.song = load_midi(tmp_path)
            
            # Clean up temp file
            import os
            os.unlink(tmp_path)
            
            st.success(f"✓ Loaded {uploaded_file.name}")
            st.rerun()
        except Exception as e:
            st.error(f"Error loading MIDI: {str(e)}")
    
    # BPM slider
    st.session_state.song.bpm = st.slider("BPM", 40, 240, 
                                          int(st.session_state.song.bpm), 1)
    
    # Play and download controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("▶ Play", type="primary"):
            with st.spinner("Synthesizing..."):
                audio_data, sample_rate = synthesize_song(st.session_state.song)
                
                # Convert to bytes for st.audio
                audio_bytes = io.BytesIO()
                import wave
                with wave.open(audio_bytes, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data.tobytes())
                
                audio_bytes.seek(0)
                st.audio(audio_bytes, format='audio/wav')
    
    with col2:
        if st.button("Download WAV"):
            with st.spinner("Exporting WAV..."):
                wav_path = "/tmp/note_stack_export.wav"
                export_wav(wav_path, st.session_state.song)
                
                with open(wav_path, 'rb') as f:
                    st.download_button(
                        label="Save WAV",
                        data=f.read(),
                        file_name="note_stack.wav",
                        mime="audio/wav"
                    )
    
    with col3:
        if st.button("Download MIDI"):
            with st.spinner("Exporting MIDI..."):
                midi_path = "/tmp/note_stack_export.mid"
                export_midi(midi_path, st.session_state.song)
                
                with open(midi_path, 'rb') as f:
                    st.download_button(
                        label="Save MIDI",
                        data=f.read(),
                        file_name="note_stack.mid",
                        mime="audio/midi"
                    )
    
    with col4:
        if st.button("➕ Add Track"):
            new_track = Track(name=f"Track {len(st.session_state.song.tracks) + 1}")
            st.session_state.song.tracks.append(new_track)
            st.rerun()
    
    # Track editors
    st.divider()
    
    for track_idx, track in enumerate(st.session_state.song.tracks):
        with st.expander(f"🎹 {track.name}" + (" (MUTED)" if track.mute else ""), 
                        expanded=track_idx == 0):
            
            col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
            
            with col1:
                track.name = st.text_input("Track Name", track.name, 
                                          key=f"name_{track_idx}")
            
            with col2:
                track.mute = st.checkbox("Mute", track.mute, key=f"mute_{track_idx}")
            
            with col3:
                track.intensity = st.number_input("Intensity", 0.1, 5.0, 
                                                 track.intensity, 0.1, 
                                                 key=f"intensity_{track_idx}")
            
            with col4:
                track.delay = st.checkbox("Delay", track.delay, 
                                         key=f"delay_{track_idx}")
            
            with col5:
                track.hold_seconds = st.number_input("Hold (s)", 0.1, 5.0, 
                                                    track.hold_seconds, 0.1,
                                                    key=f"hold_{track_idx}")
            
            with col6:
                if len(st.session_state.song.tracks) > 1:
                    if st.button("🗑️ Remove", key=f"remove_{track_idx}"):
                        st.session_state.song.tracks.pop(track_idx)
                        st.rerun()
            
            # Timeline chart
            render_timeline_chart(track, st.session_state.song.bpm)
            
            # Notes table
            if track.notes:
                notes_data = []
                for note in track.notes:
                    notes_data.append({
                        'Key': note.key,
                        'Start Beat': note.start_beat,
                        'Duration': note.duration_beats,
                        'Velocity': note.velocity
                    })
                
                df = pd.DataFrame(notes_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.write("No notes in this track")
            
            # Add note controls
            st.write("**Add Note**")
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            
            with col1:
                new_key = st.number_input("Piano Key", 1, 88, 49, 1,
                                         key=f"new_key_{track_idx}")
            
            with col2:
                new_start = st.number_input("Start Beat", 0.0, 1000.0, 0.0, 0.25,
                                           key=f"new_start_{track_idx}")
            
            with col3:
                new_duration = st.number_input("Duration", 0.25, 100.0, 1.0, 0.25,
                                              key=f"new_duration_{track_idx}")
            
            with col4:
                new_velocity = st.number_input("Velocity", 1, 127, 100, 1,
                                              key=f"new_velocity_{track_idx}")
            
            with col5:
                if st.button("Add", key=f"add_note_{track_idx}"):
                    track.notes.append(Note(
                        key=new_key,
                        start_beat=new_start,
                        duration_beats=new_duration,
                        velocity=new_velocity
                    ))
                    st.rerun()


if __name__ == "__main__":
    main()
