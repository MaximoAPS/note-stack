"""Note Stack V1 - Studio UI: Piano synthesis Streamlit app."""

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
from number_melody import generate_number_melody, SCALE_MODES
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
    st.set_page_config(page_title="Note Stack Studio", layout="wide")
    
    st.title("🎹 Note Stack Studio")
    st.caption("Number Melody generator • AI track tools • Piano key synthesis from Desmos")
    
    # Initialize session state
    if 'song' not in st.session_state:
        st.session_state.song = Song(bpm=96, tracks=[])
    
    # ========== NUMBER MELODY PANEL (PROMINENT) ==========
    st.subheader("🔢 Number Melody — Transform digits into music")
    st.caption("Paste Pi, Fibonacci, dates → Generate melody with durations learned from style MIDIs • "
              "**pair_mod chunking** for rich variation • **jump_predict** for octave disambiguation • Multi-style training")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        digit_string = st.text_area(
            "Digit String / Secuencia de dígitos",
            value="314159265358979323846",
            height=80,
            help="Enter any digit sequence (Pi, Fibonacci, dates, etc.) | "
                 "Introduce cualquier secuencia de dígitos"
        )
    
    with col2:
        # Preset buttons
        if st.button("📍 Pi (preset)", use_container_width=True):
            st.session_state.pi_digits = "314159265358979323846264338327950288419716939937510"
            st.rerun()
        
        if 'pi_digits' in st.session_state:
            digit_string = st.session_state.pi_digits
            st.caption("✓ Pi digits loaded")
        
        st.write("**Examples:**")
        st.caption("• Pi: 3141592...")
        st.caption("• e: 2718281...")
        st.caption("• Fibonacci: 1123...")
    
    with col3:
        tonic = st.number_input(
            "Tonic / Tónica",
            min_value=1,
            max_value=88,
            value=40,
            help="Root key (40 = E, 48 = C) | Tecla raíz"
        )
        
        mode = st.selectbox(
            "Mode / Modo",
            options=list(SCALE_MODES.keys()),
            index=0,
            help="Scale mode | Modo escala"
        )
    
    # Chunking and mapping
    col1, col2, col3 = st.columns(3)
    
    with col1:
        chunk_mode = st.radio(
            "Chunk / Agrupación",
            options=["pair_mod", "single"],
            index=0,
            help="pair_mod: pairs → richer | single: one digit → simple"
        )
    
    with col2:
        modulus = st.number_input(
            "Modulus / Módulo",
            min_value=5,
            max_value=24,
            value=12,
            help="12=chromatic, 7=diatonic, 5=pentatonic"
        )
    
    with col3:
        register_mode = st.radio(
            "Register / Registro",
            options=["basic", "jump_predict"],
            index=0,
            help="basic: original | jump_predict: octave disambiguation"
        )
    
    # Range and octave controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_key = st.number_input(
            "Min Key",
            min_value=1,
            max_value=88,
            value=28,
            help="Lowest note allowed (28 = E1)"
        )
    
    with col2:
        max_key = st.number_input(
            "Max Key",
            min_value=1,
            max_value=88,
            value=64,
            help="Highest note allowed (64 = E4)"
        )
    
    with col3:
        octave_range = st.number_input(
            "Octaves / Octavas",
            min_value=1,
            max_value=4,
            value=2,
            help="How many octaves to span (basic mode)"
        )
    
    # Style sources
    col1, col2 = st.columns([2, 1])
    
    with col1:
        demos_dir = Path("demos")
        demo_files = []
        if demos_dir.exists():
            demo_files = sorted([f.stem for f in demos_dir.glob("*.mid")])
        
        selected_demos = st.multiselect(
            "Style MIDIs (multi-select for richer patterns) / MIDIs de estilo",
            demo_files,
            default=demo_files[:3] if len(demo_files) >= 3 else demo_files,
            help="Select multiple MIDIs to learn duration patterns | "
                 "Selecciona múltiples MIDIs para aprender patrones"
        )
    
    with col2:
        duration_strategy = st.radio(
            "Duration / Duración",
            options=["mode", "median", "random"],
            index=0,
            help="How to pick duration: mode (most common) | "
                 "Cómo elegir duración: mode (más común)"
        )
        
        melody_bpm = st.number_input(
            "BPM",
            min_value=40,
            max_value=240,
            value=96,
            help="Tempo (96 = calm default)"
        )
    
    if st.button("🎵 Generate Number Melody / Generar Melodía Numérica", type="primary", use_container_width=True):
        try:
            if not selected_demos:
                st.error("⚠️ Select at least one style MIDI / Selecciona al menos un MIDI de estilo")
            else:
                # Load style tracks
                style_tracks = []
                for demo_name in selected_demos:
                    demo_path = demos_dir / f"{demo_name}.mid"
                    demo_song = load_midi(str(demo_path))
                    style_tracks.extend(demo_song.tracks)
                
                # Generate melody
                with st.spinner("Generating melody... / Generando melodía..."):
                    melody_track = generate_number_melody(
                        digit_string=digit_string,
                        tonic=tonic,
                        mode=mode,
                        style_tracks=style_tracks,
                        bpm=melody_bpm,
                        octave_range=octave_range,
                        chunk_mode=chunk_mode,
                        modulus=modulus,
                        min_key=min_key,
                        max_key=max_key,
                        register_mode=register_mode,
                        duration_strategy=duration_strategy
                    )
                
                # Update song BPM
                st.session_state.song.bpm = melody_bpm
                
                # Mark as Solo track
                melody_track.name = f"🎵 Solo: {melody_track.name}"
                
                # Add to song
                st.session_state.song.tracks.append(melody_track)
                
                # Show key range
                if melody_track.notes:
                    keys = [n.key for n in melody_track.notes]
                    key_range = f"{min(keys)}-{max(keys)}"
                else:
                    key_range = "N/A"
                
                st.success(f"✓ Generated {len(melody_track.notes)} notes "
                         f"(key range: {key_range}). Track added as Solo.")
                st.rerun()
        
        except Exception as e:
            st.error(f"Error generating melody: {str(e)}")
    
    st.divider()
    
    # ========== TRACKS STUDIO ==========
    st.subheader("🎛️ Tracks Studio")
    st.caption("Add tracks • Assign roles (Solo/Base/Adorn) • Generate AI fills • Edit notes • Set FX")
    
    # Play controls and BPM
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    
    with col1:
        if st.button("▶ Play", type="primary", use_container_width=True):
            with st.spinner("Synthesizing..."):
                # Filter unmuted tracks
                active_tracks = [t for t in st.session_state.song.tracks if not t.mute]
                if not active_tracks:
                    st.warning("⚠️ All tracks muted. Unmute at least one track to play.")
                else:
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
        if st.button("Download WAV", use_container_width=True):
            with st.spinner("Exporting WAV..."):
                wav_path = "/tmp/note_stack_export.wav"
                export_wav(wav_path, st.session_state.song)
                
                with open(wav_path, 'rb') as f:
                    st.download_button(
                        label="💾 Save WAV",
                        data=f.read(),
                        file_name="note_stack.wav",
                        mime="audio/wav",
                        use_container_width=True
                    )
    
    with col3:
        if st.button("Download MIDI", use_container_width=True):
            with st.spinner("Exporting MIDI..."):
                midi_path = "/tmp/note_stack_export.mid"
                export_midi(midi_path, st.session_state.song)
                
                with open(midi_path, 'rb') as f:
                    st.download_button(
                        label="💾 Save MIDI",
                        data=f.read(),
                        file_name="note_stack.mid",
                        mime="audio/midi",
                        use_container_width=True
                    )
    
    with col4:
        if st.button("➕ Add Empty Track", use_container_width=True):
            new_track = Track(name=f"Track {len(st.session_state.song.tracks) + 1}")
            st.session_state.song.tracks.append(new_track)
            st.rerun()
    
    with col5:
        st.session_state.song.bpm = st.slider("BPM", 40, 240, 
                                              int(st.session_state.song.bpm), 1)
    
    # Track list with AI generation
    st.write("---")
    
    if not st.session_state.song.tracks:
        st.info("💡 No tracks yet. Generate a Number Melody above or add an empty track to get started!")
    else:
        for track_idx, track in enumerate(st.session_state.song.tracks):
            # Determine track role from name prefix
            role_emoji = "🎵" if "Solo" in track.name else "🎸" if "Base" in track.name else "✨" if "Adorn" in track.name else "🎹"
            
            with st.expander(f"{role_emoji} {track.name}" + (" (MUTED)" if track.mute else ""), 
                            expanded=(track_idx == 0 and len(st.session_state.song.tracks) <= 3)):
                
                # Track controls
                col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
                
                with col1:
                    track.name = st.text_input("Track Name", track.name, 
                                              key=f"name_{track_idx}")
                
                with col2:
                    track.mute = st.checkbox("Mute", track.mute, key=f"mute_{track_idx}")
                
                with col3:
                    track.intensity = st.number_input("Intensity", 0.1, 5.0, 
                                                     track.intensity, 0.1, 
                                                     key=f"intensity_{track_idx}",
                                                     help="Harmonic intensity (FX)")
                
                with col4:
                    track.delay = st.checkbox("Delay", track.delay, 
                                             key=f"delay_{track_idx}",
                                             help="Enable delay FX")
                
                with col5:
                    track.hold_seconds = st.number_input("Hold (s)", 0.1, 5.0, 
                                                        track.hold_seconds, 0.1,
                                                        key=f"hold_{track_idx}",
                                                        help="Note sustain duration")
                
                with col6:
                    if len(st.session_state.song.tracks) > 1:
                        if st.button("🗑️", key=f"remove_{track_idx}"):
                            st.session_state.song.tracks.pop(track_idx)
                            st.rerun()
                
                # AI Fill buttons
                st.write("**🤖 AI Fill Track** (V1 heuristics)")
                col1, col2, col3, col4 = st.columns(4)
                
                # Collect mashup source tracks (exclude current track)
                mashup_sources = [t for i, t in enumerate(st.session_state.song.tracks) 
                                 if i != track_idx and "Solo" not in t.name]
                
                with col1:
                    if st.button("Bass Line", key=f"gen_bass_{track_idx}", 
                               help="Generate bass (keys 1-28) from other tracks",
                               use_container_width=True):
                        if mashup_sources:
                            try:
                                gen_func = PATTERN_GENERATORS["bass_line"]
                                new_notes = gen_func(
                                    mashup_sources, 
                                    st.session_state.song.bpm,
                                    key_lo=1,
                                    key_hi=28
                                )
                                track.notes = new_notes
                                track.name = "🎸 Base: Bass Line"
                                st.success(f"✓ Generated {len(new_notes)} bass notes")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.warning("⚠️ Need other tracks as source")
                
                with col2:
                    if st.button("Chord Base", key=f"gen_chords_{track_idx}",
                               help="Generate chords (keys 29-52) from other tracks",
                               use_container_width=True):
                        if mashup_sources:
                            try:
                                gen_func = PATTERN_GENERATORS["chord_base"]
                                new_notes = gen_func(
                                    mashup_sources,
                                    st.session_state.song.bpm,
                                    key_lo=29,
                                    key_hi=52
                                )
                                track.notes = new_notes
                                track.name = "🎸 Base: Chords"
                                st.success(f"✓ Generated {len(new_notes)} chord notes")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.warning("⚠️ Need other tracks as source")
                
                with col3:
                    if st.button("Adorn Pluck", key=f"gen_pluck_{track_idx}",
                               help="Generate sparse plucks (keys 45-72)",
                               use_container_width=True):
                        if mashup_sources:
                            try:
                                gen_func = PATTERN_GENERATORS["adorn_pluck"]
                                new_notes = gen_func(
                                    mashup_sources,
                                    st.session_state.song.bpm,
                                    key_lo=45,
                                    key_hi=72
                                )
                                track.notes = new_notes
                                track.name = "✨ Adorn: Pluck"
                                st.success(f"✓ Generated {len(new_notes)} pluck notes")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.warning("⚠️ Need other tracks as source")
                
                with col4:
                    if st.button("Harmony Line", key=f"gen_harmony_{track_idx}",
                               help="Harmonize melody (keys 45-72)",
                               use_container_width=True):
                        if mashup_sources:
                            try:
                                gen_func = PATTERN_GENERATORS["harmony_line"]
                                new_notes = gen_func(
                                    mashup_sources,
                                    st.session_state.song.bpm,
                                    key_lo=45,
                                    key_hi=72
                                )
                                track.notes = new_notes
                                track.name = "✨ Adorn: Harmony"
                                st.success(f"✓ Generated {len(new_notes)} harmony notes")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.warning("⚠️ Need other tracks as source")
                
                st.write("---")
                
                # Timeline chart
                render_timeline_chart(track, st.session_state.song.bpm)
                
                # Notes editor with data_editor
                st.write("**📝 Edit Notes**")
                
                if track.notes:
                    notes_data = []
                    for i, note in enumerate(track.notes):
                        notes_data.append({
                            'Index': i,
                            'Key': note.key,
                            'Start Beat': round(note.start_beat, 2),
                            'Duration': round(note.duration_beats, 2),
                            'Velocity': note.velocity
                        })
                    
                    df = pd.DataFrame(notes_data)
                    
                    # Editable table
                    edited_df = st.data_editor(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        num_rows="dynamic",  # Allow adding/deleting rows
                        column_config={
                            "Index": st.column_config.NumberColumn("Index", disabled=True),
                            "Key": st.column_config.NumberColumn(
                                "Piano Key",
                                min_value=1,
                                max_value=88,
                                step=1,
                                required=True
                            ),
                            "Start Beat": st.column_config.NumberColumn(
                                "Start Beat",
                                min_value=0.0,
                                step=0.25,
                                required=True
                            ),
                            "Duration": st.column_config.NumberColumn(
                                "Duration (beats)",
                                min_value=0.25,
                                step=0.25,
                                required=True
                            ),
                            "Velocity": st.column_config.NumberColumn(
                                "Velocity",
                                min_value=1,
                                max_value=127,
                                step=1,
                                required=True
                            )
                        },
                        key=f"notes_editor_{track_idx}"
                    )
                    
                    # Apply button
                    col1, col2, col3 = st.columns([1, 1, 2])
                    
                    with col1:
                        if st.button("✅ Apply Edits", key=f"apply_{track_idx}",
                                   type="primary"):
                            # Rebuild notes from edited_df
                            new_notes = []
                            for _, row in edited_df.iterrows():
                                if pd.notna(row['Key']) and pd.notna(row['Start Beat']) and pd.notna(row['Duration']):
                                    new_notes.append(Note(
                                        key=int(row['Key']),
                                        start_beat=float(row['Start Beat']),
                                        duration_beats=float(row['Duration']),
                                        velocity=int(row['Velocity'])
                                    ))
                            
                            track.notes = new_notes
                            st.success(f"✓ Applied edits: {len(new_notes)} notes")
                            st.rerun()
                    
                    with col2:
                        # Delete range
                        beat_range = st.text_input(
                            "Delete beats (e.g., 4-8)",
                            key=f"del_range_{track_idx}",
                            placeholder="4-8"
                        )
                        
                        if st.button("🗑️ Delete Range", key=f"del_range_btn_{track_idx}"):
                            try:
                                if "-" in beat_range:
                                    start_beat, end_beat = map(float, beat_range.split("-"))
                                    original_count = len(track.notes)
                                    track.notes = [n for n in track.notes 
                                                 if not (start_beat <= n.start_beat < end_beat)]
                                    deleted = original_count - len(track.notes)
                                    st.success(f"✓ Deleted {deleted} notes in range {start_beat}-{end_beat}")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Invalid range format: {str(e)}")
                    
                    with col3:
                        st.caption(f"Total: {len(track.notes)} notes")
                
                else:
                    st.write("No notes in this track. Generate AI fill or add notes manually.")
                    
                    # Add note manually
                    st.write("**Add Note**")
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                    
                    with col1:
                        new_key = st.number_input("Key", 1, 88, 49, 1,
                                                 key=f"new_key_{track_idx}")
                    
                    with col2:
                        new_start = st.number_input("Start", 0.0, 1000.0, 0.0, 0.25,
                                                   key=f"new_start_{track_idx}")
                    
                    with col3:
                        new_duration = st.number_input("Duration", 0.25, 100.0, 1.0, 0.25,
                                                      key=f"new_duration_{track_idx}")
                    
                    with col4:
                        new_velocity = st.number_input("Velocity", 1, 127, 100, 1,
                                                      key=f"new_velocity_{track_idx}")
                    
                    with col5:
                        if st.button("➕", key=f"add_note_{track_idx}"):
                            track.notes.append(Note(
                                key=new_key,
                                start_beat=new_start,
                                duration_beats=new_duration,
                                velocity=new_velocity
                            ))
                            st.rerun()
    
    st.divider()
    
    # ========== LEGACY TOOLS (COLLAPSED) ==========
    with st.expander("🗂️ Legacy Tools: Load MIDI / Presets", expanded=False):
        st.write("**Load demo presets or upload MIDI files**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Load Piano Song Preset"):
                st.session_state.song = create_piano_song_preset()
                st.success("✓ Loaded Piano Song (Desmos)")
                st.rerun()
            
            # MIDI upload
            uploaded_file = st.file_uploader("Upload MIDI file", type=["mid", "midi"])
            if uploaded_file is not None:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        tmp_path = tmp_file.name
                    
                    st.session_state.song = load_midi(tmp_path)
                    os.unlink(tmp_path)
                    
                    st.success(f"✓ Loaded {uploaded_file.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error loading MIDI: {str(e)}")
        
        with col2:
            # Demo selector
            demos_dir = Path("demos")
            if demos_dir.exists():
                demo_files = sorted([f.stem for f in demos_dir.glob("*.mid")])
                if demo_files:
                    selected_demo = st.selectbox("MAESTRO Demos", demo_files)
                    
                    if st.button("Load Demo"):
                        demo_path = demos_dir / f"{selected_demo}.mid"
                        st.session_state.song = load_midi(str(demo_path))
                        st.success(f"✓ Loaded {selected_demo}")
                        st.rerun()


if __name__ == "__main__":
    main()
