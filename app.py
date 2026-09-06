"""Note Stack V1 - Piano synthesis Streamlit app."""

import streamlit as st
import numpy as np
import os
from pathlib import Path
import io
import pandas as pd
import altair as alt
import tempfile

from notes import Song, Track, Note
from synth import synthesize_song, export_wav
from midi_io import load_midi, export_midi
from editor_session import EditorSession
from pattern_generators import PATTERN_GENERATORS


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


def render_editor_ui():
    """Render the Editor Mode UI for multi-MIDI workflow."""
    session = st.session_state.editor_session
    
    st.subheader("🎛️ Editor — Multi-MIDI / Track-Role Workflow")
    
    # === SOURCES PANEL ===
    with st.expander("📂 MIDI Sources", expanded=True):
        st.write("**Load multiple MIDI files as sources**")
        
        # Multi-file uploader
        uploaded_files = st.file_uploader(
            "Upload MIDI files",
            type=["mid", "midi"],
            accept_multiple_files=True,
            key="editor_midi_upload"
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                    
                    song = load_midi(tmp_path)
                    source_id = session.add_source(uploaded_file.name, song, tmp_path)
                    os.unlink(tmp_path)
                    st.success(f"✓ Loaded {uploaded_file.name} ({len(song.tracks)} tracks)")
                except Exception as e:
                    st.error(f"Error loading {uploaded_file.name}: {str(e)}")
            
            st.rerun()
        
        # Demo picker
        col1, col2 = st.columns([3, 1])
        with col1:
            demo_options = get_demo_options()
            selected_demo = st.selectbox("Or load a demo", demo_options, key="editor_demo_select")
        with col2:
            if st.button("Add Demo", key="editor_add_demo"):
                try:
                    if selected_demo == "Piano Song (Desmos)":
                        song = create_piano_song_preset()
                        session.add_source("Piano Song (Desmos)", song)
                    else:
                        filename = selected_demo.replace("MAESTRO — ", "")
                        midi_path = Path("demos") / f"{filename}.mid"
                        if midi_path.exists():
                            song = load_midi(str(midi_path))
                            session.add_source(selected_demo, song, str(midi_path))
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading demo: {str(e)}")
        
        # List sources
        if session.sources:
            st.write("---")
            st.write(f"**Loaded sources: {len(session.sources)}**")
            
            for source in session.sources:
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                
                with col1:
                    st.write(f"**{source.name}**")
                
                with col2:
                    st.caption(f"{len(source.song.tracks)} tracks, {source.song.bpm} BPM")
                
                with col3:
                    is_base = (source.id == session.base_source_id)
                    if st.checkbox("Base", value=is_base, key=f"base_{source.id}"):
                        session.set_base_source(source.id)
                        st.rerun()
                
                with col4:
                    if st.button("🗑️", key=f"remove_source_{source.id}"):
                        session.remove_source(source.id)
                        st.rerun()
        else:
            st.info("No sources loaded. Upload MIDI files or add demos to get started.")
    
    # === TRACK ROLES TABLE ===
    if session.sources:
        with st.expander("🎹 Track Roles", expanded=True):
            st.write("**Assign role to each track**: `final` (goes to output), `mashup_source` (used for AI), or `ignore`")
            
            # Build table data
            table_data = []
            for source, track, metadata in session.get_all_tracks_with_roles():
                table_data.append({
                    "Source": source.name,
                    "Track": track.name,
                    "Role": metadata.role,
                    "Key Lo": metadata.key_lo if metadata.key_lo else "",
                    "Key Hi": metadata.key_hi if metadata.key_hi else "",
                    "Notes": len(track.notes),
                    "Mute": track.mute,
                    "Intensity": track.intensity,
                    "source_id": source.id,
                    "track_idx": metadata.track_index
                })
            
            if table_data:
                df = pd.DataFrame(table_data)
                
                # Configure column
                edited_df = st.data_editor(
                    df[["Source", "Track", "Role", "Key Lo", "Key Hi", "Notes", "Mute", "Intensity"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Role": st.column_config.SelectboxColumn(
                            "Role",
                            options=["final", "mashup_source", "ignore"],
                            required=True
                        ),
                        "Key Lo": st.column_config.NumberColumn(
                            "Key Lo",
                            help="Min key (1-88), empty = no filter",
                            min_value=1,
                            max_value=88,
                            step=1
                        ),
                        "Key Hi": st.column_config.NumberColumn(
                            "Key Hi",
                            help="Max key (1-88), empty = no filter",
                            min_value=1,
                            max_value=88,
                            step=1
                        ),
                        "Mute": st.column_config.CheckboxColumn("Mute"),
                        "Intensity": st.column_config.NumberColumn(
                            "Intensity",
                            min_value=0.1,
                            max_value=5.0,
                            step=0.1
                        )
                    },
                    key="track_roles_editor"
                )
                
                # Apply changes from edited_df
                for i, row in edited_df.iterrows():
                    source_id = table_data[i]["source_id"]
                    track_idx = table_data[i]["track_idx"]
                    
                    # Update role and key range
                    key_lo = int(row["Key Lo"]) if row["Key Lo"] != "" and pd.notna(row["Key Lo"]) else None
                    key_hi = int(row["Key Hi"]) if row["Key Hi"] != "" and pd.notna(row["Key Hi"]) else None
                    session.set_track_role(source_id, track_idx, row["Role"], key_lo, key_hi)
                    
                    # Update track parameters
                    source = session.get_source(source_id)
                    if source:
                        source.song.tracks[track_idx].mute = row["Mute"]
                        source.song.tracks[track_idx].intensity = row["Intensity"]
        
        # === COMPOSE FINAL ===
        st.divider()
        col1, col2, col3 = st.columns([2, 2, 3])
        
        with col1:
            if st.button("🎼 Compose Final Song", type="primary", use_container_width=True):
                st.session_state.song = session.compose_final_song()
                st.success(f"✓ Composed {len(st.session_state.song.tracks)} final tracks")
                st.rerun()
        
        with col2:
            # Count tracks by role
            final_count = sum(1 for _, _, m in session.get_all_tracks_with_roles() if m.role == "final")
            mashup_count = sum(1 for _, _, m in session.get_all_tracks_with_roles() if m.role == "mashup_source")
            st.metric("Final tracks", final_count)
        
        with col3:
            st.metric("Mashup source tracks", mashup_count)
        
        # === AI TRACK GENERATION ===
        with st.expander("🤖 Add AI Track", expanded=False):
            st.write("**Generate new tracks** using pattern heuristics (Phase 1 V1)")
            
            col1, col2 = st.columns(2)
            
            with col1:
                pattern_type = st.selectbox(
                    "Pattern Type",
                    options=list(PATTERN_GENERATORS.keys()),
                    format_func=lambda x: PATTERN_GENERATORS[x]["name"],
                    key="ai_pattern_type"
                )
                
                pattern_info = PATTERN_GENERATORS[pattern_type]
                st.caption(pattern_info["description"])
                
                default_lo, default_hi = pattern_info["default_range"]
                
                key_lo = st.number_input("Key Range Low", 1, 88, default_lo, 1, key="ai_key_lo")
                key_hi = st.number_input("Key Range High", 1, 88, default_hi, 1, key="ai_key_hi")
            
            with col2:
                num_beats = st.number_input("Length (beats)", 4.0, 256.0, 16.0, 4.0, key="ai_num_beats")
                
                # Get BPM from base source
                bpm = 120.0
                if session.base_source_id:
                    base_source = session.get_source(session.base_source_id)
                    if base_source:
                        bpm = base_source.song.bpm
                
                st.caption(f"BPM: {bpm} (from base source)")
            
            if st.button("🎵 Generate AI Track", use_container_width=True):
                try:
                    # Get mashup source tracks
                    donor_tracks = session.get_mashup_sources()
                    
                    if not donor_tracks:
                        st.warning("⚠️ No mashup_source tracks available. Mark some tracks as 'mashup_source' first.")
                    else:
                        # Generate track
                        generator_func = pattern_info["generator"]
                        default_params = pattern_info["default_params"]
                        
                        new_track = generator_func(
                            donor_tracks=donor_tracks,
                            key_range=(key_lo, key_hi),
                            num_beats=num_beats,
                            bpm=bpm,
                            **default_params
                        )
                        
                        # Add to session as a new source with role=final
                        new_song = Song(bpm=bpm, tracks=[new_track])
                        source_id = session.add_source(new_track.name, new_song)
                        session.set_track_role(source_id, 0, "final")
                        
                        st.success(f"✓ Generated {new_track.name} with {len(new_track.notes)} notes")
                        st.rerun()
                
                except Exception as e:
                    st.error(f"Error generating track: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
    
    st.divider()


def main():
    st.set_page_config(page_title="Note Stack V1", layout="wide")
    
    st.title("Note Stack V1")
    st.caption("Piano key numbers (1-88) on timeline tracks. "
              "Timbre synthesis from Desmos Piano Song graph. "
              "MAESTRO excerpts © CC BY-NC-SA 4.0")
    
    # Initialize session state
    if 'song' not in st.session_state:
        st.session_state.song = Song(bpm=120, tracks=[Track(name="Track 1")])
    if 'editor_session' not in st.session_state:
        st.session_state.editor_session = EditorSession()
    if 'editor_mode' not in st.session_state:
        st.session_state.editor_mode = False
    
    # Mode selector
    st.divider()
    mode_col1, mode_col2 = st.columns([1, 4])
    with mode_col1:
        editor_mode = st.checkbox("🎛️ Editor Mode", value=st.session_state.editor_mode,
                                   help="Multi-MIDI workflow with track roles and AI generation")
        if editor_mode != st.session_state.editor_mode:
            st.session_state.editor_mode = editor_mode
            st.rerun()
    
    with mode_col2:
        if editor_mode:
            st.caption("**Editor Mode**: Upload multiple MIDIs, assign track roles (final/mashup/ignore), generate AI tracks, and compose.")
        else:
            st.caption("**Simple Mode**: Single-song quick edit workflow (legacy).")
    
    st.divider()
    
    # === EDITOR MODE ===
    if st.session_state.editor_mode:
        render_editor_ui()
    
    # === SIMPLE MODE (Legacy) ===
    else:
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
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_path = tmp_file.name
                
                # Load the MIDI file
                st.session_state.song = load_midi(tmp_path)
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                st.success(f"✓ Loaded {uploaded_file.name}")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading MIDI: {str(e)}")
    # === PLAYBACK & EXPORT (Both Modes) ===
    st.subheader("▶️ Playback & Export")
    
    # BPM slider
    st.session_state.song.bpm = st.slider("BPM", 40, 240, 
                                          int(st.session_state.song.bpm), 1)
    
    # Play and download controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("▶ Play", type="primary"):
            with st.spinner("Synthesizing..."):
                audio_data, sample_rate = synthesize_song(st.session_state.song)
                
                # Convert to bytes for st.audio (stereo)
                audio_bytes = io.BytesIO()
                import wave
                with wave.open(audio_bytes, 'wb') as wav_file:
                    wav_file.setnchannels(2)  # Stereo
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
        if not st.session_state.editor_mode:
            if st.button("➕ Add Track"):
                new_track = Track(name=f"Track {len(st.session_state.song.tracks) + 1}")
                st.session_state.song.tracks.append(new_track)
                st.rerun()
    
    # === TRACK EDITORS (Both Modes) ===
    st.divider()
    st.subheader("🎹 Track Editor")
    st.caption("Edit tracks, notes, and parameters for the current song")
    
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
