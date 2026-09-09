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
from number_melody import generate_number_melody, generate_pattern_bass, SCALE_MODES
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
    
    st.altair_chart(chart, width='stretch')


def main():
    st.set_page_config(page_title="Note Stack Studio", layout="wide")
    
    st.title("🎹 Note Stack Studio")
    st.caption("Number Melody generator • AI track tools • Piano key synthesis from Desmos")
    
    # Initialize session state
    if 'song' not in st.session_state:
        st.session_state.song = Song(bpm=96, tracks=[])
    
    if 'style_pack' not in st.session_state:
        st.session_state.style_pack = []
    
    # ========== STYLE / TRAINING MIDI LIBRARY (GLOBAL) ==========
    st.subheader("🎼 Style / Training MIDI Library")
    st.caption("Upload or select training MIDIs for the session • Used by Number Melody, Pattern→Base, AI fills, jump_predict, etc. • "
              "Models train from these; if empty, tools fall back to MIDI-GPT, heuristics, or neutral defaults.")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Multi-select from demos folder
        demos_dir = Path("demos")
        demo_files = []
        if demos_dir.exists():
            demo_files = sorted([f.stem for f in demos_dir.glob("*.mid")])
        
        selected_demos = st.multiselect(
            "Pick demo MIDIs",
            demo_files,
            default=[],
            help="Select one or more demo MIDIs to add to the style pack",
            key="style_pack_demos"
        )
    
    with col2:
        if st.button("➕ Add Selected Demos", width='stretch'):
            added = 0
            for demo_name in selected_demos:
                demo_path = demos_dir / f"{demo_name}.mid"
                # Store as dict with name and path
                entry = {'name': demo_name, 'path': str(demo_path), 'source': 'demo'}
                if entry not in st.session_state.style_pack:
                    st.session_state.style_pack.append(entry)
                    added += 1
            if added > 0:
                st.success(f"✓ Added {added} demo(s)")
                st.rerun()
    
    with col3:
        # Upload MIDI
        uploaded_style = st.file_uploader("Upload MIDI", type=["mid", "midi"], key="style_upload")
        if uploaded_style is not None:
            try:
                # Save to temp location
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp_file:
                    tmp_file.write(uploaded_style.read())
                    tmp_path = tmp_file.name
                
                # Add to style pack
                entry = {'name': uploaded_style.name, 'path': tmp_path, 'source': 'upload'}
                if entry not in st.session_state.style_pack:
                    st.session_state.style_pack.append(entry)
                    st.success(f"✓ Added {uploaded_style.name}")
                    st.rerun()
            except Exception as e:
                st.error(f"Error uploading: {str(e)}")
    
    # Display current style pack
    if st.session_state.style_pack:
        st.write(f"**Loaded:** {len(st.session_state.style_pack)} style MIDI(s)")
        
        # Show list with remove buttons
        for idx, entry in enumerate(st.session_state.style_pack):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                source_icon = "📁" if entry['source'] == 'demo' else "📤"
                st.caption(f"{source_icon} {entry['name']}")
            with col2:
                # Count tracks
                try:
                    midi_song = load_midi(entry['path'])
                    st.caption(f"{len(midi_song.tracks)} tracks")
                except:
                    st.caption("N/A")
            with col3:
                if st.button("🗑️", key=f"remove_style_{idx}"):
                    # Clean up temp file if uploaded
                    if entry['source'] == 'upload' and os.path.exists(entry['path']):
                        try:
                            os.unlink(entry['path'])
                        except:
                            pass
                    st.session_state.style_pack.pop(idx)
                    st.rerun()
        
        # Clear all button
        if st.button("🗑️ Clear All Style MIDIs", width='stretch'):
            # Clean up temp files
            for entry in st.session_state.style_pack:
                if entry['source'] == 'upload' and os.path.exists(entry['path']):
                    try:
                        os.unlink(entry['path'])
                    except:
                        pass
            st.session_state.style_pack = []
            st.rerun()
    else:
        st.info("💡 No style MIDIs loaded. Tools will use MIDI-GPT / heuristics / neutral defaults where available.")
    
    st.divider()
    
    # ========== NUMBER SEQUENCE INPUT & SOLO GENERATION (PROMINENT) ==========
    st.subheader("🔢 Number Sequence → Solo / Melody")
    st.caption("Paste digit sequences (Pi, Fibonacci, dates) • Generate Solo melody • Or upload a solo MIDI • "
              "Uses style pack above for duration/jump learning")
    
    # Main digit input and quick controls
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    
    with col1:
        digit_string = st.text_area(
            "Digit String",
            value="314159265358979323846",
            height=60,
            help="Enter any digit sequence (Pi, Fibonacci, dates, etc.)",
            placeholder="31415926535897..."
        )
    
    with col2:
        # Preset buttons
        if st.button("📍 Pi digits", width='stretch'):
            st.session_state.pi_digits = "314159265358979323846264338327950288419716939937510"
            st.rerun()
        
        if 'pi_digits' in st.session_state:
            digit_string = st.session_state.pi_digits
            st.caption("✓ Using Pi")
        
        st.caption("**Quick:**")
        st.caption("• Pi: 3141...")
        st.caption("• e: 2718...")
        st.caption("• Fib: 1123...")
    
    with col3:
        tonic = st.number_input(
            "Tonic",
            min_value=1,
            max_value=88,
            value=40,
            help="Root key (40 = E, 48 = C)",
            key="melody_tonic"
        )
        
        melody_bpm = st.number_input(
            "BPM",
            min_value=40,
            max_value=240,
            value=96,
            help="Tempo",
            key="melody_bpm"
        )
    
    with col4:
        mode = st.selectbox(
            "Mode",
            options=list(SCALE_MODES.keys()),
            index=0,
            help="Scale mode",
            key="melody_mode"
        )
        
        # Upload solo MIDI
        uploaded_solo = st.file_uploader("Or upload Solo MIDI", type=["mid", "midi"], key="solo_upload")
        if uploaded_solo is not None:
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mid") as tmp_file:
                    tmp_file.write(uploaded_solo.read())
                    tmp_path = tmp_file.name
                
                solo_song = load_midi(tmp_path)
                os.unlink(tmp_path)
                
                # Mark first track as Solo
                if solo_song.tracks:
                    solo_song.tracks[0].name = f"🎵 Solo: {uploaded_solo.name}"
                    st.session_state.song.tracks.append(solo_song.tracks[0])
                    st.success(f"✓ Loaded Solo: {uploaded_solo.name}")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Advanced options in expander
    with st.expander("⚙️ Advanced Options (chunking, register, key range, style override)", expanded=False):
        # Chunking and mapping
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chunk_mode = st.radio(
                "Chunk",
                options=["pair_mod", "single"],
                index=0,
                help="pair_mod: pairs → richer | single: one digit → simple",
                key="melody_chunk_mode"
            )
        
        with col2:
            modulus = st.number_input(
                "Modulus",
                min_value=5,
                max_value=24,
                value=12,
                help="12=chromatic, 7=diatonic, 5=pentatonic",
                key="melody_modulus"
            )
        
        with col3:
            register_mode = st.radio(
                "Register",
                options=["basic", "jump_predict"],
                index=0,
                help="basic: original | jump_predict: octave disambiguation",
                key="melody_register_mode"
            )
        
        # Range and octave controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_key = st.number_input(
                "Min Key",
                min_value=1,
                max_value=88,
                value=28,
                help="Lowest note allowed (28 = E1)",
                key="melody_min_key"
            )
        
        with col2:
            max_key = st.number_input(
                "Max Key",
                min_value=1,
                max_value=88,
                value=64,
                help="Highest note allowed (64 = E4)",
                key="melody_max_key"
            )
        
        with col3:
            octave_range = st.number_input(
                "Octaves",
                min_value=1,
                max_value=4,
                value=2,
                help="How many octaves to span (basic mode)",
                key="melody_octave_range"
            )
        
        # Style sources override
        col1, col2 = st.columns([2, 1])
        
        with col1:
            use_global_styles = st.checkbox(
                "Use global style pack",
                value=True,
                help="Use the Style Library MIDIs loaded above. Uncheck to select specific MIDIs for this melody.",
                key="nm_use_global"
            )
            
            if not use_global_styles:
                demos_dir = Path("demos")
                demo_files = []
                if demos_dir.exists():
                    demo_files = sorted([f.stem for f in demos_dir.glob("*.mid")])
                
                selected_demos = st.multiselect(
                    "Style MIDIs (override)",
                    demo_files,
                    default=demo_files[:3] if len(demo_files) >= 3 else demo_files,
                    help="Select multiple MIDIs to learn duration patterns",
                    key="melody_selected_demos"
                )
            else:
                st.caption(f"✓ Using {len(st.session_state.style_pack)} global style MIDI(s)")
        
        with col2:
            duration_strategy = st.radio(
                "Duration",
                options=["mode", "median", "random"],
                index=0,
                help="How to pick duration: mode (most common)",
                key="melody_duration_strategy"
            )
    
    if st.button("🎵 Generate Solo Melody from Numbers", type="primary", width='stretch'):
        try:
            # Determine which style sources to use
            style_tracks = []
            
            if use_global_styles:
                if not st.session_state.style_pack:
                    st.warning("⚠️ No global style MIDIs loaded. Using fallback heuristics.")
                else:
                    # Load from global style pack
                    for entry in st.session_state.style_pack:
                        try:
                            style_song = load_midi(entry['path'])
                            style_tracks.extend(style_song.tracks)
                        except Exception as e:
                            st.warning(f"Could not load {entry['name']}: {str(e)}")
            else:
                if not selected_demos:
                    st.error("⚠️ Select at least one style MIDI / Selecciona al menos un MIDI de estilo")
                    raise ValueError("No style MIDIs selected")
                else:
                    # Load style tracks from local selection
                    for demo_name in selected_demos:
                        demo_path = demos_dir / f"{demo_name}.mid"
                        demo_song = load_midi(str(demo_path))
                        style_tracks.extend(demo_song.tracks)
            
            # Continue only if we have valid data
            if use_global_styles or selected_demos:
                
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
                 "Introduce secuencia de dígitos",
            key="pattern_string"
        )
    
    with col2:
        pattern_mode = st.radio(
            "Mode / Modo",
            options=["offset", "tonic_scale"],
            index=0,
            help="offset: digit + offset | tonic_scale: tonic + scale degree in low octave",
            key="pattern_mode"
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if pattern_mode == "offset":
            bass_offset = st.number_input(
                "Bass Offset",
                min_value=0,
                max_value=40,
                value=10,
                help="Add this to each digit (e.g., 3 + 10 = key 13)",
                key="pattern_bass_offset"
            )
        else:
            bass_tonic = st.number_input(
                "Bass Tonic",
                min_value=1,
                max_value=40,
                value=16,
                help="Root key in bass register (16 = E0, 28 = E1)",
                key="pattern_bass_tonic"
            )
            bass_scale_mode = st.selectbox(
                "Scale Mode",
                options=list(SCALE_MODES.keys()),
                index=4,  # chromatic
                help="Scale mode for tonic_scale",
                key="pattern_bass_scale_mode"
            )
    
    with col2:
        bass_min_key = st.number_input(
            "Min Key",
            min_value=1,
            max_value=88,
            value=28,
            help="Lowest bass note allowed (28 = E1)",
            key="pattern_bass_min_key"
        )
    
    with col3:
        bass_max_key = st.number_input(
            "Max Key",
            min_value=1,
            max_value=88,
            value=42,
            help="Highest bass note allowed (42 = F#2)",
            key="pattern_bass_max_key"
        )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Style sources (defaults to global style_pack, but allow override)
        use_global_bass_styles = st.checkbox(
            "Use global style pack",
            value=True,
            help="Use the Style Library MIDIs loaded above. Uncheck to select specific MIDIs.",
            key="bass_use_global"
        )
        
        if not use_global_bass_styles:
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
        else:
            st.caption(f"✓ Using {len(st.session_state.style_pack)} global style MIDI(s)")
    
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
    
    if st.button("🎸 Generate Pattern Bass / Generar Bajo de Patrón", type="primary", width='stretch'):
        try:
            # Determine which style sources to use
            style_tracks = []
            
            if use_global_bass_styles:
                if not st.session_state.style_pack:
                    st.warning("⚠️ No global style MIDIs loaded. Using fallback heuristics.")
                else:
                    # Load from global style pack
                    for entry in st.session_state.style_pack:
                        try:
                            style_song = load_midi(entry['path'])
                            style_tracks.extend(style_song.tracks)
                        except Exception as e:
                            st.warning(f"Could not load {entry['name']}: {str(e)}")
            else:
                if not selected_bass_styles:
                    st.error("⚠️ Select at least one style MIDI / Selecciona al menos un MIDI de estilo")
                    raise ValueError("No style MIDIs selected")
                else:
                    # Load style tracks from local selection
                    for demo_name in selected_bass_styles:
                        demo_path = demos_dir / f"{demo_name}.mid"
                        demo_song = load_midi(str(demo_path))
                        style_tracks.extend(demo_song.tracks)
            
            # Continue only if we have valid data
            if use_global_bass_styles or selected_bass_styles:
                
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
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    track.name = st.text_input("Track Name", track.name, 
                                              key=f"name_{track_idx}")
                
                with col2:
                    track.mute = st.checkbox("Mute", track.mute, key=f"mute_{track_idx}")
                
                with col3:
                    if len(st.session_state.song.tracks) > 1:
                        if st.button("🗑️ Remove Track", key=f"remove_{track_idx}", width='stretch'):
                            st.session_state.song.tracks.pop(track_idx)
                            st.rerun()
                
                # Loop controls (especially useful for Base tracks)
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    track.loop_enabled = st.checkbox("🔁 Loop", track.loop_enabled, 
                                                    key=f"loop_{track_idx}",
                                                    help="Repeat this track's pattern across the timeline")
                
                with col2:
                    if track.loop_enabled:
                        track.loop_length_beats = st.number_input(
                            "Loop beats",
                            min_value=0.0,
                            max_value=128.0,
                            value=track.loop_length_beats,
                            step=0.5,
                            key=f"loop_len_{track_idx}",
                            help="Loop length in beats (0 = until song end)"
                        )
                        if track.loop_length_beats == 0:
                            st.caption("↻ Until song end")
                        else:
                            st.caption(f"↻ {track.loop_length_beats} beats")
                
                with col3:
                    if track.loop_enabled:
                        st.caption("💡 Track will repeat its pattern across the song timeline")
                
                # FX Calibration (add effects on demand)
                st.write("**🎛️ FX / Efectos**")
                
                # Initialize active effects for this track in session state
                if f"active_fx_{track_idx}" not in st.session_state:
                    st.session_state[f"active_fx_{track_idx}"] = set()
                
                active_fx = st.session_state[f"active_fx_{track_idx}"]
                
                # Add effect button and selector
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    available_effects = []
                    if "intensity" not in active_fx:
                        available_effects.append("Intensity")
                    if "delay" not in active_fx:
                        available_effects.append("Delay")
                    if "hold" not in active_fx:
                        available_effects.append("Hold")
                    
                    if available_effects:
                        effect_to_add = st.selectbox(
                            "Select effect",
                            available_effects,
                            key=f"fx_select_{track_idx}",
                            label_visibility="collapsed"
                        )
                
                with col2:
                    if available_effects and st.button("➕ Agregar efecto / Add effect", key=f"add_fx_{track_idx}", width='stretch'):
                        # Add the selected effect
                        effect_key = effect_to_add.lower()
                        active_fx.add(effect_key)
                        st.session_state[f"active_fx_{track_idx}"] = active_fx
                        st.rerun()
                
                with col3:
                    if st.button("🔄 Piano Defaults", key=f"fx_reset_{track_idx}",
                               help="Reset FX to piano defaults: I=1.0, hold=0.8s, delay=on",
                               width='stretch'):
                        # Set piano defaults
                        track.intensity = 1.0
                        track.hold_seconds = 0.8
                        track.delay = True
                        # Activate all effects to show piano defaults
                        st.session_state[f"active_fx_{track_idx}"] = {"intensity", "delay", "hold"}
                        st.success("✓ Piano defaults set")
                        st.rerun()
                
                # Display active effects with their controls
                if active_fx:
                    st.caption(f"**Active effects:** {', '.join(sorted(active_fx)).title()}")
                    
                    # Intensity effect
                    if "intensity" in active_fx:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            track.intensity = st.slider(
                                "Intensity (harmonic multiplier)",
                                0.1, 5.0, 
                                track.intensity, 0.1,
                                key=f"intensity_{track_idx}",
                                help="1.0=melody, 2.0=bass/rich"
                            )
                            st.caption("1.0=melody, 2.0=bass")
                        with col2:
                            if st.button("🗑️", key=f"remove_intensity_{track_idx}", help="Remove Intensity effect"):
                                active_fx.discard("intensity")
                                st.session_state[f"active_fx_{track_idx}"] = active_fx
                                st.rerun()
                    
                    # Delay effect
                    if "delay" in active_fx:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            track.delay = st.checkbox(
                                "Delay (30/160s echo)",
                                track.delay,
                                key=f"delay_{track_idx}",
                                help="Enable 30/160s delay voice"
                            )
                            st.caption("Echo at 30/160s")
                        with col2:
                            if st.button("🗑️", key=f"remove_delay_{track_idx}", help="Remove Delay effect"):
                                active_fx.discard("delay")
                                st.session_state[f"active_fx_{track_idx}"] = active_fx
                                st.rerun()
                    
                    # Hold effect
                    if "hold" in active_fx:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            track.hold_seconds = st.slider(
                                "Hold (sustain duration in seconds)",
                                0.1, 5.0,
                                track.hold_seconds, 0.1,
                                key=f"hold_{track_idx}",
                                help="Note sustain duration"
                            )
                            st.caption("0.5=short, 0.8=piano, 2.0=long")
                        with col2:
                            if st.button("🗑️", key=f"remove_hold_{track_idx}", help="Remove Hold effect"):
                                active_fx.discard("hold")
                                st.session_state[f"active_fx_{track_idx}"] = active_fx
                                st.rerun()
                else:
                    st.caption("💡 No effects active. Add effects above to calibrate this track's sound.")
                
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
                
                # Insert silence/rest
                st.write("**Insert Silence / Rest**")
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    rest_duration = st.selectbox(
                        "Rest duration",
                        options=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0],
                        index=1,  # 0.5 default
                        format_func=format_duration_label,
                        key=f"rest_dur_{track_idx}",
                        help="Duration of silence to insert"
                    )
                
                with col2:
                    if st.button("➕ Insert Rest at End", key=f"insert_rest_end_{track_idx}"):
                        # Find current end beat
                        if track.notes:
                            end_beat = max(n.start_beat + n.duration_beats for n in track.notes)
                        else:
                            end_beat = 0.0
                        
                        # Don't add a note - just shift the timeline by creating a marker
                        # Actually, to insert silence, we don't add notes - the gap IS the silence
                        # But we can add it to the cluster state for visual feedback
                        st.success(f"✓ Rest of {format_duration_label(rest_duration)} beats marked at end ({end_beat:.1f})")
                        st.caption("💡 Rests are gaps between notes - paste new clusters to continue after the gap")
                
                with col3:
                    rest_position = st.number_input(
                        "At beat",
                        min_value=0.0,
                        value=0.0,
                        step=0.5,
                        key=f"rest_pos_{track_idx}",
                        help="Insert rest at specific beat position"
                    )
                    if st.button("➕ Insert Rest Here", key=f"insert_rest_pos_{track_idx}"):
                        # Find notes after this position and shift them
                        shifted_count = 0
                        for note in track.notes:
                            if note.start_beat >= rest_position:
                                note.start_beat += rest_duration
                                shifted_count += 1
                        
                        if shifted_count > 0:
                            st.success(f"✓ Inserted {format_duration_label(rest_duration)} beat rest at {rest_position:.1f} (shifted {shifted_count} notes)")
                            # Clear cluster cache
                            if f"clusters_{track_idx}" in st.session_state:
                                del st.session_state[f"clusters_{track_idx}"]
                            st.rerun()
                        else:
                            st.info(f"No notes after beat {rest_position:.1f} to shift")
                
                st.caption("💡 **Rests are gaps** — no note means silence. Insert rest shifts later notes or marks end position.")
                
                st.write("---")
                
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
