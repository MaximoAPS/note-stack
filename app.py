"""Note Stack V1 - Studio UI: Piano synthesis Streamlit app."""

import streamlit as st
import numpy as np
import os
from pathlib import Path
import io
import pandas as pd
import altair as alt
import tempfile
from typing import List, Tuple, Dict
from dataclasses import dataclass
from collections import defaultdict

from notes import Song, Track, Note
from synth import synthesize_song, export_wav
from midi_io import load_midi, export_midi
from number_melody import (
    generate_number_melody, 
    generate_pattern_bass, 
    generate_pattern_bass_from_solo,
    SCALE_MODES
)
from pattern_generators import PATTERN_GENERATORS


# ========== CLUSTER BADGE HELPERS ==========

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
    
    # Group by start_beat
    groups = defaultdict(list)
    for note in notes:
        groups[note.start_beat].append(note)
    
    # Create clusters
    clusters = []
    for start_beat in sorted(groups.keys()):
        group_notes = groups[start_beat]
        # Use the most common duration in the cluster
        durations = [n.duration_beats for n in group_notes]
        duration = max(set(durations), key=durations.count)
        # Collect all keys
        keys = [n.key for n in group_notes]
        # Use first velocity
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
                velocity=max(1, cluster.velocity)  # Ensure velocity ≥ 1
            ))
    return notes


def parse_cluster_string(cluster_str: str, default_duration: float = 0.5) -> Tuple[List[NoteCluster], List[str]]:
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
        
        # Parse keys in this cluster (comma-separated)
        key_strs = part.split(',')
        keys = []
        for k in key_strs:
            try:
                key_val = int(k.strip())
                keys.append(key_val)
                
                # Warn about very low or very high keys
                if key_val < 20:
                    warnings.append(f"⚠️ Key {key_val} is very low (near bottom of piano, barely audible)")
                elif key_val > 80:
                    warnings.append(f"⚠️ Key {key_val} is very high (top of piano)")
            except ValueError:
                continue
        
        if keys:
            # Ensure velocity is at least 1
            clusters.append(NoteCluster(
                start_beat=current_beat,
                duration_beats=default_duration,
                keys=keys,
                velocity=100
            ))
            current_beat += default_duration
    
    return clusters, warnings


def format_duration_label(duration: float) -> str:
    """Format duration as fraction like '1/4', '1/2', '1', '2'."""
    if duration >= 1.0:
        if duration == int(duration):
            return str(int(duration))
        else:
            return f"{duration:.2f}"
    else:
        # Try common fractions
        if abs(duration - 0.25) < 0.01:
            return "1/4"
        elif abs(duration - 0.5) < 0.01:
            return "1/2"
        elif abs(duration - 0.75) < 0.01:
            return "3/4"
        else:
            return f"{duration:.2f}"


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
    
    # Guard against empty or invalid data
    if df.empty or df['start'].isna().all() or not np.isfinite(df['start']).any():
        st.write("No valid notes to display")
        return
    
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
    
    st.altair_chart(chart, width='stretch')


def render_all_tracks_combined_chart(song: Song, include_muted: bool = False):
    """Render a combined timeline chart showing all tracks together.
    
    Args:
        song: The song containing all tracks
        include_muted: If True, include muted tracks (shown faded)
    """
    # Collect all notes from all tracks
    chart_data = []
    
    for track in song.tracks:
        # Skip muted tracks if not including them
        if track.mute and not include_muted:
            continue
        
        for note in track.notes:
            chart_data.append({
                'start': note.start_beat,
                'end': note.start_beat + note.duration_beats,
                'key': note.key,
                'velocity': note.velocity,
                'track': track.name,
                'muted': track.mute
            })
    
    # Guard against empty data
    if not chart_data:
        st.info("No notes to display. Add tracks with notes to see the combined timeline.")
        return
    
    df = pd.DataFrame(chart_data)
    
    # Create combined timeline chart with color by track
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('start:Q', title='Beat'),
        x2='end:Q',
        y=alt.Y('key:Q', scale=alt.Scale(domain=[1, 88]), title='Piano Key'),
        color=alt.Color('track:N', title='Track', legend=alt.Legend(orient='right')),
        opacity=alt.condition(
            alt.datum.muted == True,
            alt.value(0.3),
            alt.value(1.0)
        ),
        tooltip=['track:N', 'key:Q', 'start:Q', 'end:Q', 'velocity:Q']
    ).properties(
        height=300
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
        if st.button("📍 Pi (preset)", width='stretch'):
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
    
    if st.button("🎵 Generate Number Melody / Generar Melodía Numérica", type="primary", width='stretch'):
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
    
    # ========== PATTERN → BASE PANEL ==========
    st.subheader("🎸 Pattern → Base — Ordered bass from digit pattern")
    st.caption("Enter a pattern sequence (e.g., Pi digits `3-1-4-1-5`) to generate a bass line "
              "with those pitches in order • AI assigns durations from style MIDIs • "
              "Digits are degrees/offsets, not literal piano keys 1-5")
    st.caption("Los dígitos son grados de patrón, no teclas crudas 1-5 • "
              "Ejemplo Pi `31415` → bajo con esos tonos relativos en orden")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        pattern_string = st.text_input(
            "Pattern String / Cadena de Patrón",
            value="3-1-4-1-5",
            help="Enter digit sequence (e.g., 3-1-4-1-5 or 3,1,4,1,5) | "
                 "Introduce secuencia de dígitos"
        )
    
    with col2:
        pattern_mode = st.radio(
            "Mode / Modo",
            options=["offset", "tonic_scale"],
            index=0,
            help="offset: digit + offset | tonic_scale: tonic + scale degree in low octave"
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if pattern_mode == "offset":
            bass_offset = st.number_input(
                "Bass Offset",
                min_value=0,
                max_value=40,
                value=10,
                help="Add this to each digit (e.g., 3 + 10 = key 13)"
            )
        else:
            bass_tonic = st.number_input(
                "Bass Tonic",
                min_value=1,
                max_value=40,
                value=16,
                help="Root key in bass register (16 = E0, 28 = E1)"
            )
            bass_scale_mode = st.selectbox(
                "Scale Mode",
                options=list(SCALE_MODES.keys()),
                index=4,  # chromatic
                help="Scale mode for tonic_scale"
            )
    
    with col2:
        bass_min_key = st.number_input(
            "Min Key",
            min_value=1,
            max_value=88,
            value=28,
            help="Lowest bass note allowed (28 = E1)"
        )
    
    with col3:
        bass_max_key = st.number_input(
            "Max Key",
            min_value=1,
            max_value=88,
            value=42,
            help="Highest bass note allowed (42 = F#2)"
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Style sources
        demos_dir = Path("demos")
        demo_files = []
        if demos_dir.exists():
            demo_files = sorted([f.stem for f in demos_dir.glob("*.mid")])
        
        selected_bass_styles = st.multiselect(
            "Style MIDIs / MIDIs de estilo",
            demo_files,
            default=demo_files[:2] if len(demo_files) >= 2 else demo_files,
            help="Select MIDIs to learn durations | Selecciona MIDIs para aprender duraciones",
            key="pattern_bass_styles"
        )
    
    with col2:
        bass_duration_strategy = st.radio(
            "Duration / Duración",
            options=["mode", "median", "random"],
            index=0,
            help="How to pick duration: mode (most common)",
            key="pattern_bass_duration"
        )
    
    with col3:
        use_bass_jump_predict = st.checkbox(
            "Use Jump Predict",
            value=False,
            help="Use jump model for octave/jump within bass range (advanced)",
            key="pattern_bass_jump"
        )
        
        pattern_bass_bpm = st.number_input(
            "BPM",
            min_value=40,
            max_value=240,
            value=96,
            help="Tempo",
            key="pattern_bass_bpm"
        )
    
    if st.button("🎸 Generate Pattern Bass / Generar Bajo de Patrón", type="primary", use_container_width=True):
        try:
            if not selected_bass_styles:
                st.error("⚠️ Select at least one style MIDI / Selecciona al menos un MIDI de estilo")
            else:
                # Load style tracks
                style_tracks = []
                for demo_name in selected_bass_styles:
                    demo_path = demos_dir / f"{demo_name}.mid"
                    demo_song = load_midi(str(demo_path))
                    style_tracks.extend(demo_song.tracks)
                
                # Generate pattern bass
                with st.spinner("Generating pattern bass... / Generando bajo de patrón..."):
                    if pattern_mode == "offset":
                        bass_track = generate_pattern_bass(
                            pattern_string=pattern_string,
                            style_tracks=style_tracks,
                            bpm=pattern_bass_bpm,
                            mode="offset",
                            bass_offset=bass_offset,
                            min_key=bass_min_key,
                            max_key=bass_max_key,
                            duration_strategy=bass_duration_strategy,
                            use_jump_predict=use_bass_jump_predict
                        )
                    else:
                        bass_track = generate_pattern_bass(
                            pattern_string=pattern_string,
                            style_tracks=style_tracks,
                            bpm=pattern_bass_bpm,
                            mode="tonic_scale",
                            tonic=bass_tonic,
                            scale_mode=bass_scale_mode,
                            min_key=bass_min_key,
                            max_key=bass_max_key,
                            duration_strategy=bass_duration_strategy,
                            use_jump_predict=use_bass_jump_predict
                        )
                
                # Update song BPM
                st.session_state.song.bpm = pattern_bass_bpm
                
                # Mark as Base track
                bass_track.name = f"🎸 Base: {bass_track.name}"
                
                # Add to song
                st.session_state.song.tracks.append(bass_track)
                
                # Show key range
                if bass_track.notes:
                    keys = [n.key for n in bass_track.notes]
                    key_range = f"{min(keys)}-{max(keys)}"
                else:
                    key_range = "N/A"
                
                st.success(f"✓ Generated {len(bass_track.notes)} bass notes "
                         f"(key range: {key_range}). Track added as Base.")
                st.rerun()
        
        except Exception as e:
            st.error(f"Error generating pattern bass: {str(e)}")
    
    st.divider()
    
    # ========== FILL BASE FROM SOLO ==========
    with st.expander("🎸🎵 Fill Base from Solo — Ordered pattern harmonized under Solo", expanded=False):
        st.caption("Given an existing Solo track, pick notes in a fixed order (pattern) and fill a Base track with those pitches "
                  "harmonized under the Solo • AI can auto-choose offset to fit with Solo pitch classes • "
                  "Timing stretches/loops to match Solo span")
        st.caption("Requiere una pista Solo existente • Patrón ordenado armonizado bajo Solo • "
                  "IA puede elegir offset automático para armonizar")
        
        # Check if we have a Solo track
        solo_tracks = [t for t in st.session_state.song.tracks if "Solo" in t.name or "solo" in t.name.lower()]
        
        if not solo_tracks:
            st.warning("⚠️ No Solo track found. Generate a Number Melody first (it will be marked as Solo).")
            st.caption("No se encontró pista Solo. Genera una Number Melody primero.")
        else:
            st.success(f"✓ Found {len(solo_tracks)} Solo track(s): {', '.join(t.name for t in solo_tracks[:3])}")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                solo_pattern_string = st.text_input(
                    "Pattern String / Cadena de Patrón",
                    value="3-1-4-1-5",
                    help="Enter digit sequence (e.g., 3-1-4-1-5) | Introduce secuencia de dígitos",
                    key="solo_pattern_string"
                )
            
            with col2:
                solo_offset_mode = st.radio(
                    "Offset Mode / Modo Offset",
                    options=["Auto from Solo", "Manual"],
                    index=0,
                    help="Auto: AI picks offset to harmonize with Solo | Manual: specify offset",
                    key="solo_offset_mode"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if solo_offset_mode == "Manual":
                    solo_manual_offset = st.number_input(
                        "Manual Offset",
                        min_value=0,
                        max_value=40,
                        value=10,
                        help="Add this to each digit (e.g., 3 + 10 = key 13)",
                        key="solo_manual_offset"
                    )
                else:
                    st.caption("**Offset:** Auto-chosen by AI")
                    st.caption("AI will pick offset that harmonizes with Solo pitch classes")
            
            with col2:
                solo_min_key = st.number_input(
                    "Min Key",
                    min_value=1,
                    max_value=88,
                    value=28,
                    help="Lowest bass note allowed (28 = E1)",
                    key="solo_min_key"
                )
            
            with col3:
                solo_max_key = st.number_input(
                    "Max Key",
                    min_value=1,
                    max_value=88,
                    value=42,
                    help="Highest bass note allowed (42 = F#2)",
                    key="solo_max_key"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Style sources for duration learning
                demos_dir = Path("demos")
                demo_files = []
                if demos_dir.exists():
                    demo_files = sorted([f.stem for f in demos_dir.glob("*.mid")])
                
                selected_solo_bass_styles = st.multiselect(
                    "Style MIDIs / MIDIs de estilo",
                    demo_files,
                    default=demo_files[:2] if len(demo_files) >= 2 else demo_files,
                    help="Select MIDIs to learn durations | Selecciona MIDIs para aprender duraciones",
                    key="solo_bass_styles"
                )
            
            with col2:
                solo_duration_strategy = st.radio(
                    "Duration / Duración",
                    options=["mode", "median", "random"],
                    index=0,
                    help="How to pick duration: mode (most common)",
                    key="solo_duration_strategy"
                )
            
            with col3:
                solo_loop_pattern = st.checkbox(
                    "Loop Pattern",
                    value=True,
                    help="Loop pattern to fill Solo span (if unchecked, stretches timing)",
                    key="solo_loop_pattern"
                )
            
            if st.button("🎸 Fill Base from Solo / Llenar Bajo desde Solo", 
                        type="primary", 
                        use_container_width=True,
                        key="fill_base_from_solo_btn"):
                try:
                    if not selected_solo_bass_styles:
                        st.warning("💡 No style MIDIs selected. Using fallback durations (0.5 beats).")
                        style_tracks = []
                    else:
                        # Load style tracks
                        style_tracks = []
                        for demo_name in selected_solo_bass_styles:
                            demo_path = demos_dir / f"{demo_name}.mid"
                            demo_song = load_midi(str(demo_path))
                            style_tracks.extend(demo_song.tracks)
                    
                    # Use first solo track found
                    primary_solo = solo_tracks[0]
                    
                    # Generate pattern bass from solo
                    with st.spinner("Generating bass from Solo pattern... / Generando bajo desde patrón Solo..."):
                        if solo_offset_mode == "Auto from Solo":
                            bass_track = generate_pattern_bass_from_solo(
                                pattern_string=solo_pattern_string,
                                solo_track=primary_solo,
                                style_tracks=style_tracks if style_tracks else [],
                                bpm=st.session_state.song.bpm,
                                offset_mode="auto",
                                min_key=solo_min_key,
                                max_key=solo_max_key,
                                duration_strategy=solo_duration_strategy,
                                loop_pattern=solo_loop_pattern
                            )
                        else:
                            bass_track = generate_pattern_bass_from_solo(
                                pattern_string=solo_pattern_string,
                                solo_track=primary_solo,
                                style_tracks=style_tracks if style_tracks else [],
                                bpm=st.session_state.song.bpm,
                                offset_mode="manual",
                                manual_offset=solo_manual_offset,
                                min_key=solo_min_key,
                                max_key=solo_max_key,
                                duration_strategy=solo_duration_strategy,
                                loop_pattern=solo_loop_pattern
                            )
                    
                    # Mark as Base track
                    bass_track.name = f"🎸 Base: {bass_track.name}"
                    
                    # Add to song
                    st.session_state.song.tracks.append(bass_track)
                    
                    # Show key range
                    if bass_track.notes:
                        keys = [n.key for n in bass_track.notes]
                        key_range = f"{min(keys)}-{max(keys)}"
                    else:
                        key_range = "N/A"
                    
                    st.success(f"✓ Generated {len(bass_track.notes)} bass notes harmonized under Solo "
                             f"(key range: {key_range}). Track added as Base.")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Error generating bass from solo: {str(e)}")
    
    st.divider()
    
    # ========== TRACKS STUDIO ==========
    st.subheader("🎛️ Tracks Studio")
    st.caption("Add tracks • Assign roles (Solo/Base/Adorn) • Generate AI fills • Edit notes • Set FX")
    
    # Play controls and BPM
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
    
    with col1:
        if st.button("▶ Play", type="primary", width='stretch'):
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
                    # Store in session state so it persists across reruns
                    st.session_state.last_audio = audio_bytes.read()
                    audio_bytes.seek(0)
        
        # Display last played audio if available
        if 'last_audio' in st.session_state:
            st.audio(st.session_state.last_audio, format='audio/wav')
    
    with col2:
        if st.button("Download WAV", width='stretch'):
            with st.spinner("Exporting WAV..."):
                wav_path = "/tmp/note_stack_export.wav"
                export_wav(wav_path, st.session_state.song)
                
                with open(wav_path, 'rb') as f:
                    st.download_button(
                        label="💾 Save WAV",
                        data=f.read(),
                        file_name="note_stack.wav",
                        mime="audio/wav",
                        width='stretch'
                    )
    
    with col3:
        if st.button("Download MIDI", width='stretch'):
            with st.spinner("Exporting MIDI..."):
                midi_path = "/tmp/note_stack_export.mid"
                export_midi(midi_path, st.session_state.song)
                
                with open(midi_path, 'rb') as f:
                    st.download_button(
                        label="💾 Save MIDI",
                        data=f.read(),
                        file_name="note_stack.mid",
                        mime="audio/midi",
                        width='stretch'
                    )
    
    with col4:
        if st.button("➕ Add Empty Track", width='stretch'):
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
        # ========== ALL TRACKS COMBINED CHART ==========
        st.subheader("🎼 All Tracks — Song Overview")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption("Combined timeline showing all tracks together")
        with col2:
            show_muted = st.checkbox("Show muted tracks", value=False, key="show_muted_combined")
        
        render_all_tracks_combined_chart(st.session_state.song, include_muted=show_muted)
        
        st.write("---")
        st.subheader("📋 Individual Tracks")
        
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
                               width='stretch'):
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
                               width='stretch'):
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
                               width='stretch'):
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
                               width='stretch'):
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
                
                # ========== CLUSTER BADGE EDITOR ==========
                st.write("**📝 Edit Notes: Cluster Badges**")
                
                # Paste/Import cluster string
                st.write("**Paste Cluster String**")
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    cluster_input = st.text_input(
                        "Cluster string (e.g., 35-35,36-38-35)",
                        key=f"cluster_input_{track_idx}",
                        placeholder="35-35,36-38-35",
                        help="Syntax: dash (-) separates clusters, comma (,) separates keys within a cluster"
                    )
                
                with col2:
                    default_duration = st.selectbox(
                        "Default duration",
                        options=[0.25, 0.5, 0.75, 1.0, 2.0],
                        index=1,  # 0.5 default
                        format_func=format_duration_label,
                        key=f"default_dur_{track_idx}"
                    )
                
                with col3:
                    if st.button("📥 Paste", key=f"paste_cluster_{track_idx}"):
                        if cluster_input.strip():
                            try:
                                new_clusters, warnings = parse_cluster_string(cluster_input, default_duration)
                                
                                # Show warnings about unusual keys
                                if warnings:
                                    for warning in warnings:
                                        st.warning(warning)
                                
                                if new_clusters:
                                    # Append to existing notes
                                    existing_clusters = notes_to_clusters(track.notes)
                                    
                                    # Offset new clusters to start after existing
                                    if existing_clusters:
                                        last_end = max(c.start_beat + c.duration_beats for c in existing_clusters)
                                        for nc in new_clusters:
                                            nc.start_beat += last_end
                                    
                                    all_clusters = existing_clusters + new_clusters
                                    track.notes = clusters_to_notes(all_clusters)
                                    st.success(f"✓ Pasted {len(new_clusters)} clusters")
                                    st.rerun()
                                else:
                                    st.error("No valid clusters found")
                            except Exception as e:
                                st.error(f"Error parsing: {str(e)}")
                        else:
                            st.warning("Enter a cluster string")
                
                st.caption("**Syntax:** `35-35,36-38-35` → [35] then [35,36] then [38] then [35], each " + format_duration_label(default_duration) + " beat(s)")
                st.caption("💡 **Note:** Paste uses **piano keys 1–88** (middle C = 40). Very low keys (<20) are barely audible.")
                
                st.write("---")
                
                # Display clusters as badges
                if track.notes:
                    clusters = notes_to_clusters(track.notes)
                    
                    # Initialize session state for cluster edits
                    if f"clusters_{track_idx}" not in st.session_state:
                        st.session_state[f"clusters_{track_idx}"] = clusters
                    
                    st.write(f"**Cluster Badges** ({len(clusters)} clusters, {len(track.notes)} notes)")
                    
                    # Display and edit each cluster
                    for cluster_idx, cluster in enumerate(st.session_state[f"clusters_{track_idx}"]):
                        cols = st.columns([3, 1, 1, 1, 1])
                        
                        with cols[0]:
                            # Display keys as comma-separated
                            keys_str = ",".join(map(str, cluster.keys))
                            new_keys_str = st.text_input(
                                f"Cluster {cluster_idx}",
                                value=keys_str,
                                key=f"cluster_keys_{track_idx}_{cluster_idx}",
                                label_visibility="collapsed"
                            )
                            
                            # Parse keys on change
                            try:
                                new_keys = [int(k.strip()) for k in new_keys_str.split(',') if k.strip()]
                                st.session_state[f"clusters_{track_idx}"][cluster_idx].keys = new_keys
                            except:
                                pass
                        
                        with cols[1]:
                            # Duration selector
                            duration_options = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
                            try:
                                current_idx = duration_options.index(cluster.duration_beats)
                            except ValueError:
                                duration_options.append(cluster.duration_beats)
                                duration_options.sort()
                                current_idx = duration_options.index(cluster.duration_beats)
                            
                            new_duration = st.selectbox(
                                "Duration",
                                options=duration_options,
                                index=current_idx,
                                format_func=format_duration_label,
                                key=f"cluster_dur_{track_idx}_{cluster_idx}",
                                label_visibility="collapsed"
                            )
                            st.session_state[f"clusters_{track_idx}"][cluster_idx].duration_beats = new_duration
                        
                        with cols[2]:
                            # Insert button
                            if st.button("➕", key=f"insert_{track_idx}_{cluster_idx}",
                                       help="Insert cluster before this one"):
                                new_cluster = NoteCluster(
                                    start_beat=cluster.start_beat,
                                    duration_beats=0.5,
                                    keys=[49],
                                    velocity=100
                                )
                                st.session_state[f"clusters_{track_idx}"].insert(cluster_idx, new_cluster)
                                st.rerun()
                        
                        with cols[3]:
                            # Delete button
                            if st.button("🗑️", key=f"delete_{track_idx}_{cluster_idx}",
                                       help="Delete this cluster"):
                                st.session_state[f"clusters_{track_idx}"].pop(cluster_idx)
                                st.rerun()
                        
                        with cols[4]:
                            # Display beat position
                            st.caption(f"@{cluster.start_beat:.1f}")
                    
                    st.write("---")
                    
                    # Apply clusters button
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        if st.button("✅ Apply Changes", key=f"apply_clusters_{track_idx}",
                                   type="primary"):
                            # Reassign start_beats sequentially
                            current_beat = 0.0
                            for c in st.session_state[f"clusters_{track_idx}"]:
                                c.start_beat = current_beat
                                current_beat += c.duration_beats
                            
                            # Convert to notes
                            track.notes = clusters_to_notes(st.session_state[f"clusters_{track_idx}"])
                            
                            # Clear session state to refresh
                            del st.session_state[f"clusters_{track_idx}"]
                            
                            st.success(f"✓ Applied {len(track.notes)} notes")
                            st.rerun()
                    
                    with col2:
                        if st.button("🔄 Refresh from Track", key=f"refresh_clusters_{track_idx}"):
                            st.session_state[f"clusters_{track_idx}"] = notes_to_clusters(track.notes)
                            st.rerun()
                    
                    # Advanced table editor (collapsed)
                    with st.expander("🔧 Advanced Table Editor", expanded=False):
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
                        
                        edited_df = st.data_editor(
                            df,
                            width='stretch',
                            hide_index=True,
                            num_rows="dynamic",
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
                            key=f"notes_table_{track_idx}"
                        )
                        
                        col1, col2, col3 = st.columns([1, 1, 2])
                        
                        with col1:
                            if st.button("✅ Apply Table", key=f"apply_table_{track_idx}"):
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
                                if f"clusters_{track_idx}" in st.session_state:
                                    del st.session_state[f"clusters_{track_idx}"]
                                st.success(f"✓ Applied table: {len(new_notes)} notes")
                                st.rerun()
                        
                        with col2:
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
                                        if f"clusters_{track_idx}" in st.session_state:
                                            del st.session_state[f"clusters_{track_idx}"]
                                        st.success(f"✓ Deleted {deleted} notes in range {start_beat}-{end_beat}")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Invalid range format: {str(e)}")
                
                else:
                    st.write("No notes in this track yet.")
                    st.caption("Use 'Paste Cluster String' above or 'AI Fill Track' buttons to add notes.")
    
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
