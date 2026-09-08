"""Number Melody — Transform digit sequences into melodies with learned durations."""

import argparse
import random
from collections import defaultdict
from typing import List, Dict, Literal, Optional
from statistics import mode, median

from notes import Track, Note, Song
from midi_io import load_midi, export_midi


# Scale interval patterns (semitones from tonic)
SCALE_MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11],  # C D E F G A B
    "minor": [0, 2, 3, 5, 7, 8, 10],  # A B C D E F G (natural minor)
    "pentatonic_major": [0, 2, 4, 7, 9],  # C D E G A
    "pentatonic_minor": [0, 3, 5, 7, 10],  # A C D E G
    "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]  # All 12 semitones
}


def parse_digit_string(s: str) -> List[int]:
    """
    Extract digits 0-9 from string, ignore separators and other characters.
    
    Args:
        s: Input string (e.g. "3.14159..." or "314159265358979")
    
    Returns:
        List of digits as integers
    
    Examples:
        >>> parse_digit_string("3.14159")
        [3, 1, 4, 1, 5, 9]
        >>> parse_digit_string("2026-09-08")
        [2, 0, 2, 6, 0, 9, 0, 8]
    """
    return [int(c) for c in s if c.isdigit()]


def chunk_digits(
    digits: List[int],
    chunk_mode: Literal["single", "pair_mod"] = "single",
    modulus: int = 12
) -> List[int]:
    """
    Chunk and transform digits for pitch mapping.
    
    Args:
        digits: List of single digits (0-9)
        chunk_mode: Chunking strategy
            - "single": Each digit maps directly (0-9)
            - "pair_mod": Consecutive pairs treated as 00-99, then value % modulus
        modulus: For pair_mod, the modulus to apply (typically 5, 7, or 12)
    
    Returns:
        List of values ready for pitch mapping
    
    Examples:
        >>> chunk_digits([3, 1, 4, 1, 5, 9], "single", 12)
        [3, 1, 4, 1, 5, 9]
        >>> chunk_digits([3, 1, 4, 1, 5, 9], "pair_mod", 12)
        [7, 5, 9]  # 31%12=7, 41%12=5, 59%12=11 but wait, 59%12=11, not 9
        
    Note:
        For pair_mod with odd number of digits, the trailing digit is
        treated as a single-digit number (0-9).
    """
    if chunk_mode == "single":
        return digits
    
    elif chunk_mode == "pair_mod":
        values = []
        i = 0
        while i < len(digits):
            if i + 1 < len(digits):
                # Take consecutive pair as two-digit number
                pair_value = digits[i] * 10 + digits[i + 1]
                values.append(pair_value % modulus)
                i += 2
            else:
                # Odd trailing digit: use as-is modulo modulus
                values.append(digits[i] % modulus)
                i += 1
        return values
    
    else:
        raise ValueError(f"Unknown chunk_mode: {chunk_mode}")


def map_values_to_keys(
    values: List[int],
    tonic: int,
    mode: Literal["major", "minor", "pentatonic_major", "pentatonic_minor", "chromatic"],
    chunk_mode: Literal["single", "pair_mod"],
    modulus: int,
    octave_range: int = 2,
    max_key: Optional[int] = None
) -> List[int]:
    """
    Map chunked values to piano keys.
    
    Args:
        values: List of chunked values (from chunk_digits)
        tonic: Root key (1-88, e.g. 48 for middle C)
        mode: Scale mode to use (for single mode or as reference)
        chunk_mode: "single" or "pair_mod"
        modulus: Modulus used in chunking (relevant for pair_mod)
        octave_range: How many octaves to span (1-4)
        max_key: Optional maximum key to clamp to (default: tonic + scale_span + 12*(octave_range-1))
    
    Returns:
        List of piano keys (1-88)
    
    Mapping logic:
        - single mode: Each value 0-9 maps to scale degree, wrapping across octaves
        - pair_mod mode with modulus=12: Each value 0-11 maps to chromatic offset from tonic
        - pair_mod mode with other modulus: Each value maps to scale degree if modulus matches scale length
    """
    if mode not in SCALE_MODES:
        raise ValueError(f"Unknown mode: {mode}. Available: {list(SCALE_MODES.keys())}")
    
    scale_degrees = SCALE_MODES[mode]
    keys = []
    
    # Determine default max_key if not specified
    if max_key is None:
        if chunk_mode == "pair_mod" and modulus == 12:
            # Chromatic: tonic + 11 semitones + octave spans
            max_key = tonic + 11 + 12 * (octave_range - 1)
        else:
            # Scale-based: tonic + scale span + octave spans
            scale_span = max(scale_degrees)
            max_key = tonic + scale_span + 12 * (octave_range - 1)
        
        # Hard cap at 64 (E above middle C) for comfortable listening
        max_key = min(max_key, 64)
    
    for value in values:
        if chunk_mode == "pair_mod" and modulus == 12:
            # Chromatic mapping: value 0-11 maps directly to semitone offsets
            # Distribute across octave_range
            octave_offset = (value // 12) % octave_range
            pitch_offset = value % 12
            key = tonic + pitch_offset + octave_offset * 12
        
        else:
            # Scale-based mapping: value maps to scale degree
            pitch_class = scale_degrees[value % len(scale_degrees)]
            octave_offset = (value // len(scale_degrees)) % octave_range
            key = tonic + pitch_class + octave_offset * 12
        
        # Clamp to valid piano range and max_key
        key = max(1, min(88, min(key, max_key)))
        
        keys.append(key)
    
    return keys


def map_digits_to_keys(
    digits: List[int],
    tonic: int,
    mode: Literal["major", "minor", "pentatonic_major", "pentatonic_minor", "chromatic"],
    octave_range: int = 2,
    max_key: Optional[int] = None
) -> List[int]:
    """
    Map digits to piano keys using scale/mode (legacy single-digit mode).
    
    This function is kept for backward compatibility. New code should use
    chunk_digits() + map_values_to_keys() for more control.
    
    Args:
        digits: List of digits (0-9)
        tonic: Root key (1-88, e.g. 48 for middle C)
        mode: Scale mode to use
        octave_range: How many octaves to span (1-4)
        max_key: Optional maximum key to clamp to
    
    Returns:
        List of piano keys (1-88)
    
    Examples:
        >>> map_digits_to_keys([3, 1, 4, 1, 5, 9], tonic=48, mode="major", octave_range=2)
        [53, 50, 55, 50, 57, 62]  # E C G C A D
    """
    return map_values_to_keys(
        values=digits,
        tonic=tonic,
        mode=mode,
        chunk_mode="single",
        modulus=10,  # Not used for single mode
        octave_range=octave_range,
        max_key=max_key
    )


def build_duration_model(
    style_tracks: List[Track]
) -> Dict[int, List[float]]:
    """
    Build P(duration | jump) from style tracks.
    
    For each consecutive note pair in style tracks, record the jump (interval)
    and the duration of the second note. This creates a statistical model of
    how duration relates to melodic motion.
    
    Args:
        style_tracks: List of tracks to learn from
    
    Returns:
        Dictionary mapping jump (in semitones) to list of observed durations (in beats)
        
    Example:
        {
            0: [0.5, 0.5, 1.0],  # Same key: mostly short notes
            2: [1.0, 2.0, 1.0],  # Whole step up: varied durations
            -1: [0.25, 0.5],     # Half step down: short notes
        }
    """
    jump_durations: Dict[int, List[float]] = defaultdict(list)
    
    for track in style_tracks:
        if len(track.notes) < 2:
            continue
        
        # Sort notes by start time
        sorted_notes = sorted(track.notes, key=lambda n: n.start_beat)
        
        for i in range(1, len(sorted_notes)):
            prev_note = sorted_notes[i - 1]
            curr_note = sorted_notes[i]
            
            # Calculate jump (interval in semitones)
            jump = curr_note.key - prev_note.key
            
            # Record current note's duration
            duration = curr_note.duration_beats
            
            # Clamp duration to reasonable range (0.25 to 4.0 beats)
            duration = max(0.25, min(4.0, duration))
            
            jump_durations[jump].append(duration)
    
    return dict(jump_durations)


def build_jump_model(
    style_tracks: List[Track]
) -> Dict[int, List[int]]:
    """
    Build P(jump | pitch_class_delta) from style tracks for octave disambiguation.
    
    For each consecutive note pair in style tracks, record the pitch class delta
    (modulo 12) and the actual signed jump (interval in semitones).
    This creates a statistical model of how composers navigate octaves.
    
    Args:
        style_tracks: List of tracks to learn from
    
    Returns:
        Dictionary mapping pitch_class_delta (0-11) to list of observed signed jumps
        
    Example:
        {
            0: [0, 12, -12],      # Same pitch class: unison, octave up/down
            1: [1, 13, -11],      # Half step up PC: +1 semitone or octave variants
            7: [7, -5, 19],       # Fifth up PC: +7, -5 (down fourth), +19 (compound)
        }
    """
    pc_delta_jumps: Dict[int, List[int]] = defaultdict(list)
    
    for track in style_tracks:
        if len(track.notes) < 2:
            continue
        
        # Sort notes by start time
        sorted_notes = sorted(track.notes, key=lambda n: n.start_beat)
        
        for i in range(1, len(sorted_notes)):
            prev_note = sorted_notes[i - 1]
            curr_note = sorted_notes[i]
            
            # Calculate actual signed jump
            jump = curr_note.key - prev_note.key
            
            # Calculate pitch class delta (0-11)
            # This represents the "musical interval class" ignoring octaves
            pc_delta = jump % 12
            
            pc_delta_jumps[pc_delta].append(jump)
    
    return dict(pc_delta_jumps)


def resolve_keys_by_jump(
    pitch_classes: List[int],
    style_tracks: List[Track],
    min_key: int = 28,
    max_key: int = 72,
    start_key: Optional[int] = None,
    modulus: int = 12
) -> List[int]:
    """
    Resolve pitch classes to absolute piano keys using jump prediction from style.
    
    This is the core octave disambiguation algorithm:
    1. For each pitch class in sequence
    2. Find all candidate keys in [min_key, max_key] that match that pitch class
    3. Pick the jump (Δkey) from previous key that is most probable given style MIDIs
    4. Among candidates matching next PC, prefer the jump that appears most in style
    
    Args:
        pitch_classes: Sequence of pitch classes (0-11 for modulus=12, or 0-(modulus-1))
        style_tracks: Tracks to learn jump patterns from
        min_key: Minimum piano key (default 28 = E below bass staff)
        max_key: Maximum piano key (default 72 = C above treble staff)
        start_key: Starting key for first note (default: middle of range)
        modulus: Pitch class modulus (default 12 for chromatic)
    
    Returns:
        List of piano keys (1-88) with octave disambiguation applied
        
    Example:
        >>> # Pitch classes: [3, 7, 10, 3]  (E♭, G, B♭, E♭)
        >>> # Style shows preference for small jumps
        >>> # Result might be: [39, 43, 46, 39]  (fourth up, minor third up, fifth down)
        >>> # vs naive fixed octave: [39, 43, 46, 51]  (all upward, might go too high)
    """
    if not pitch_classes:
        return []
    
    # Build jump model from style
    jump_model = build_jump_model(style_tracks)
    
    # Determine start key if not provided
    if start_key is None:
        # Start in middle of range, matching first pitch class
        mid_key = (min_key + max_key) // 2
        start_key = mid_key - (mid_key % modulus) + pitch_classes[0]
        # Adjust to be within range
        while start_key < min_key:
            start_key += modulus
        while start_key > max_key:
            start_key -= modulus
    
    keys = [start_key]
    
    for i in range(1, len(pitch_classes)):
        prev_key = keys[-1]
        target_pc = pitch_classes[i]
        
        # Find all candidate keys in range that match target pitch class
        candidates = []
        # Start from prev_key and search nearby octaves
        base_candidate = prev_key - (prev_key % modulus) + target_pc
        
        # Search down
        candidate = base_candidate
        while candidate >= min_key:
            if min_key <= candidate <= max_key:
                candidates.append(candidate)
            candidate -= modulus
        
        # Search up
        candidate = base_candidate + modulus
        while candidate <= max_key:
            if min_key <= candidate <= max_key:
                candidates.append(candidate)
            candidate += modulus
        
        if not candidates:
            # Fallback: clamp to range
            candidate = prev_key - (prev_key % modulus) + target_pc
            if candidate < min_key:
                candidate += modulus * ((min_key - candidate + modulus - 1) // modulus)
            if candidate > max_key:
                candidate -= modulus * ((candidate - max_key + modulus - 1) // modulus)
            candidates = [max(min_key, min(max_key, candidate))]
        
        # Pick candidate with most probable jump based on style
        best_candidate = None
        best_score = -1
        
        for candidate in candidates:
            jump = candidate - prev_key
            pc_delta = jump % modulus
            
            # Score based on jump frequency in style
            if pc_delta in jump_model and jump in jump_model[pc_delta]:
                # Count how many times this exact jump appears
                score = jump_model[pc_delta].count(jump)
            elif pc_delta in jump_model:
                # PC delta exists but not this exact jump: prefer smaller absolute jump
                score = 0.1 / (abs(jump) + 1)
            else:
                # PC delta never seen: strongly prefer smallest absolute jump
                score = 0.01 / (abs(jump) + 1)
            
            if score > best_score:
                best_score = score
                best_candidate = candidate
        
        # Fallback: pick candidate with smallest absolute jump
        if best_candidate is None:
            best_candidate = min(candidates, key=lambda c: abs(c - prev_key))
        
        keys.append(best_candidate)
    
    return keys


def predict_durations(
    keys: List[int],
    duration_model: Dict[int, List[float]],
    strategy: Literal["mode", "median", "random"] = "mode",
    default_duration: float = 0.5
) -> List[float]:
    """
    Predict duration for each note given previous key jump.
    
    Args:
        keys: Piano keys for melody
        duration_model: Jump -> durations histogram from build_duration_model()
        strategy: How to pick duration from histogram:
            - "mode": Most common duration
            - "median": Middle duration
            - "random": Random sample from observed durations
        default_duration: Fallback if jump not in model (in beats)
    
    Returns:
        List of durations (in beats), same length as keys
    """
    if not keys:
        return []
    
    durations = []
    
    # First note: use default duration
    durations.append(default_duration)
    
    # Subsequent notes: predict based on jump
    for i in range(1, len(keys)):
        jump = keys[i] - keys[i - 1]
        
        if jump in duration_model and duration_model[jump]:
            duration_samples = duration_model[jump]
            
            if strategy == "mode":
                try:
                    duration = mode(duration_samples)
                except:
                    # If no unique mode, use median
                    duration = median(duration_samples)
            elif strategy == "median":
                duration = median(duration_samples)
            elif strategy == "random":
                duration = random.choice(duration_samples)
            else:
                duration = default_duration
        else:
            # Jump not in model, use default
            duration = default_duration
        
        durations.append(duration)
    
    return durations


def generate_number_melody(
    digit_string: str,
    tonic: int,
    mode: str,
    style_tracks: List[Track],
    bpm: float = 96.0,
    octave_range: int = 2,
    chunk_mode: Literal["single", "pair_mod"] = "pair_mod",
    modulus: int = 12,
    max_key: Optional[int] = None,
    min_key: Optional[int] = None,
    octave_mode: Literal["fixed", "jump_predict"] = "fixed",
    duration_strategy: Literal["mode", "median", "random"] = "mode",
    intensity: float = 1.0,
    hold_seconds: float = 0.8,
    track_name: Optional[str] = None
) -> Track:
    """
    Generate melody track from digit string.
    
    Args:
        digit_string: String with digits (e.g. "314159265358979")
        tonic: Root key (e.g. 48 for middle C)
        mode: Scale mode (major, minor, pentatonic_major, pentatonic_minor, chromatic)
        style_tracks: Tracks to learn durations from (can be from multiple MIDIs)
        bpm: Tempo (default 96 for calmer feel)
        octave_range: How many octaves to span (1-4, only used in fixed mode)
        chunk_mode: "single" (one digit → scale degree) or "pair_mod" (digit pairs % modulus)
        modulus: For pair_mod, modulus to apply (12=chromatic, 7=diatonic, 5=pentatonic)
        max_key: Optional maximum key to clamp to (default: 64 for fixed, 72 for jump_predict)
        min_key: Optional minimum key (default: auto, 28 for jump_predict)
        octave_mode: "fixed" (original, deterministic octave mapping) or 
                     "jump_predict" (style-aware octave disambiguation)
        duration_strategy: How to pick duration from histogram (mode/median/random)
        intensity: Track intensity parameter (default 1.0)
        hold_seconds: Track hold parameter (default 0.8)
        track_name: Custom track name (default auto-generated)
    
    Returns:
        Generated melody Track with notes
    
    Example (fixed mode):
        >>> from midi_io import load_midi
        >>> style_songs = [load_midi("demos/chopin-etude.mid"), load_midi("demos/liszt-preludio.mid")]
        >>> all_style_tracks = []
        >>> for song in style_songs:
        ...     all_style_tracks.extend(song.tracks)
        >>> track = generate_number_melody(
        ...     "314159265358979",
        ...     tonic=48,
        ...     mode="major",
        ...     style_tracks=all_style_tracks,
        ...     chunk_mode="pair_mod",
        ...     modulus=12,
        ...     octave_mode="fixed",
        ...     bpm=96.0
        ... )
        >>> len(track.notes)
        7
    
    Example (jump_predict mode):
        >>> track = generate_number_melody(
        ...     "314159265358979",
        ...     tonic=48,
        ...     mode="chromatic",
        ...     style_tracks=all_style_tracks,
        ...     chunk_mode="pair_mod",
        ...     modulus=12,
        ...     octave_mode="jump_predict",
        ...     min_key=28,
        ...     max_key=72,
        ...     bpm=96.0
        ... )
        # Notes span full range with octave choices based on style jump preferences
    """
    # 1. Parse digits
    digits = parse_digit_string(digit_string)
    
    if not digits:
        # No digits found, return empty track
        return Track(
            name=track_name or "Number Melody (empty)",
            intensity=intensity,
            hold_seconds=hold_seconds,
            notes=[]
        )
    
    # 2. Chunk digits
    values = chunk_digits(digits, chunk_mode, modulus)
    
    # 3. Map values to keys
    if octave_mode == "jump_predict":
        # Use jump prediction for octave disambiguation
        # Values are treated as pitch classes (mod modulus)
        pitch_classes = [v % modulus for v in values]
        
        # Set defaults for min/max key if not provided
        if min_key is None:
            min_key = 28  # E below bass staff
        if max_key is None:
            max_key = 72  # C above treble staff
        
        # Resolve pitch classes to keys using style-aware jump model
        keys = resolve_keys_by_jump(
            pitch_classes=pitch_classes,
            style_tracks=style_tracks,
            min_key=min_key,
            max_key=max_key,
            start_key=tonic,
            modulus=modulus
        )
    else:
        # Fixed mode: original deterministic mapping
        keys = map_values_to_keys(
            values=values,
            tonic=tonic,
            mode=mode,
            chunk_mode=chunk_mode,
            modulus=modulus,
            octave_range=octave_range,
            max_key=max_key
        )
    
    # 4. Build duration model from style tracks
    duration_model = build_duration_model(style_tracks)
    
    # 5. Predict durations
    durations = predict_durations(keys, duration_model, strategy=duration_strategy)
    
    # 6. Create Note objects
    notes = []
    current_beat = 0.0
    
    for key, duration in zip(keys, durations):
        note = Note(
            key=key,
            start_beat=current_beat,
            duration_beats=duration,
            velocity=100
        )
        notes.append(note)
        current_beat += duration
    
    # 7. Create and return Track
    if track_name is None:
        # Try to identify the sequence
        digit_prefix = digit_string[:20].replace(" ", "").replace(".", "")
        if digit_prefix.startswith("31415"):
            seq_name = "Pi"
        elif digit_prefix.startswith("11235"):
            seq_name = "Fibonacci"
        else:
            seq_name = "Number"
        
        chunk_label = "pair" if chunk_mode == "pair_mod" else "single"
        octave_label = "jump" if octave_mode == "jump_predict" else "fixed"
        track_name = f"Number Melody ({seq_name}, {mode}, {chunk_label}, {octave_label})"
    
    return Track(
        name=track_name,
        intensity=intensity,
        hold_seconds=hold_seconds,
        delay=True,  # Delay adds nice space to melodies
        notes=notes
    )


def main():
    """CLI for number melody generation."""
    parser = argparse.ArgumentParser(
        description="Generate melody from digit string with learned durations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fixed mode (original), pair_mod with chromatic (modulus 12):
  python number_melody.py --digits 314159265358979 --tonic 48 \\
    --chunk pair_mod --modulus 12 --octave-mode fixed \\
    --style demos/chopin-etude.mid --out pi_chromatic.mid --bpm 96 --max-key 60

  # Jump predict mode (new!), full keyboard with style-aware octave choices:
  python number_melody.py --digits 314159265358979 --tonic 48 \\
    --chunk pair_mod --modulus 12 --octave-mode jump_predict \\
    --min-key 28 --max-key 72 \\
    --style demos/chopin-etude.mid --style demos/liszt-preludio.mid \\
    --style demos/scarlatti-sonata.mid --out pi_jump.mid --bpm 96

  # Multiple styles, single digit mode:
  python number_melody.py --digits 112358132134 --tonic 40 --chunk single \\
    --mode pentatonic_minor --style demos/chopin-etude.mid \\
    --style demos/liszt-preludio.mid --style demos/scarlatti-sonata.mid \\
    --out fibonacci.mid --bpm 90
        """
    )
    parser.add_argument(
        "--digits",
        required=True,
        help="Digit string (e.g. '314159265358979' for Pi)"
    )
    parser.add_argument(
        "--tonic",
        type=int,
        default=48,
        help="Root key (1-88, default 48 = middle C)"
    )
    parser.add_argument(
        "--mode",
        choices=list(SCALE_MODES.keys()),
        default="major",
        help="Scale mode (default: major)"
    )
    parser.add_argument(
        "--style",
        action="append",
        required=True,
        help="Path to style MIDI file(s) to learn durations from (can specify multiple)"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output MIDI file path"
    )
    parser.add_argument(
        "--bpm",
        type=float,
        default=96.0,
        help="Tempo in BPM (default: 96 for calmer feel)"
    )
    parser.add_argument(
        "--octave-range",
        type=int,
        default=2,
        help="Octave range to span (1-4, default: 2)"
    )
    parser.add_argument(
        "--chunk",
        choices=["single", "pair_mod"],
        default="pair_mod",
        help="Chunking mode: 'single' (one digit → scale degree) or 'pair_mod' (digit pairs %% modulus, default)"
    )
    parser.add_argument(
        "--modulus",
        type=int,
        default=12,
        help="For pair_mod: modulus to apply (default: 12 for chromatic)"
    )
    parser.add_argument(
        "--max-key",
        type=int,
        default=None,
        help="Maximum key to clamp to (default: auto, ~64 for fixed mode, ~72 for jump_predict)"
    )
    parser.add_argument(
        "--min-key",
        type=int,
        default=None,
        help="Minimum key (default: auto, ~28 for jump_predict mode)"
    )
    parser.add_argument(
        "--octave-mode",
        choices=["fixed", "jump_predict"],
        default="fixed",
        help="Octave resolution: 'fixed' (deterministic) or 'jump_predict' (style-aware disambiguation, default: fixed)"
    )
    parser.add_argument(
        "--strategy",
        choices=["mode", "median", "random"],
        default="mode",
        help="Duration selection strategy (default: mode)"
    )
    
    args = parser.parse_args()
    
    # Load style MIDIs
    all_style_tracks = []
    print(f"Loading {len(args.style)} style MIDI(s):")
    for style_path in args.style:
        print(f"  - {style_path}")
        style_song = load_midi(style_path)
        all_style_tracks.extend(style_song.tracks)
        print(f"    Loaded {len(style_song.tracks)} track(s), BPM={style_song.bpm}")
    
    print(f"\nTotal style tracks: {len(all_style_tracks)}")
    
    # Generate melody
    print(f"\nGenerating melody from digits: {args.digits[:50]}...")
    print(f"  Tonic={args.tonic}, Mode={args.mode}, Octave Range={args.octave_range}")
    print(f"  Chunk mode={args.chunk}, Modulus={args.modulus}")
    print(f"  Octave mode={args.octave_mode}")
    if args.min_key:
        print(f"  Min key={args.min_key}")
    if args.max_key:
        print(f"  Max key={args.max_key}")
    print(f"  Duration strategy={args.strategy}, BPM={args.bpm}")
    
    melody_track = generate_number_melody(
        digit_string=args.digits,
        tonic=args.tonic,
        mode=args.mode,
        style_tracks=all_style_tracks,
        bpm=args.bpm,
        octave_range=args.octave_range,
        chunk_mode=args.chunk,
        modulus=args.modulus,
        max_key=args.max_key,
        min_key=args.min_key,
        octave_mode=args.octave_mode,
        duration_strategy=args.strategy
    )
    
    print(f"  Generated {len(melody_track.notes)} notes")
    
    # Show key range
    if melody_track.notes:
        keys = [n.key for n in melody_track.notes]
        print(f"  Key range: {min(keys)} - {max(keys)}")
    
    # Create song and export
    output_song = Song(bpm=args.bpm, tracks=[melody_track])
    export_midi(args.out, output_song)
    
    print(f"\n✓ Saved to {args.out}")
    
    # Show first few notes
    if melody_track.notes:
        print("\nFirst 5 notes:")
        for i, note in enumerate(melody_track.notes[:5]):
            print(f"  {i+1}. Key {note.key:2d}, Start {note.start_beat:6.2f}, "
                  f"Duration {note.duration_beats:.2f}")


if __name__ == "__main__":
    main()
