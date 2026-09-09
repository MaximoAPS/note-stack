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
    max_key: Optional[int] = None,
    min_key: Optional[int] = None,
    jump_model: Optional[Dict[int, int]] = None,
    register_mode: Literal["basic", "jump_predict"] = "basic"
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
        min_key: Optional minimum key to clamp to (default: tonic)
        jump_model: Optional jump histogram for jump_predict mode
        register_mode: "basic" (original algorithm) or "jump_predict" (octave disambiguation)
    
    Returns:
        List of piano keys (1-88)
    
    Mapping logic:
        - basic mode (default): Original algorithm
          - single mode: Each value 0-9 maps to scale degree, wrapping across octaves
          - pair_mod mode with modulus=12: Each value 0-11 maps to chromatic offset from tonic
          - pair_mod mode with other modulus: Each value maps to scale degree if modulus matches scale length
        - jump_predict mode: Octave disambiguation via jump likelihood
          - Requires chunk_mode="pair_mod" and modulus=12
          - Each value is pitch class (0-11)
          - Pick octave from [min_key, max_key] that maximizes jump likelihood
    """
    if mode not in SCALE_MODES:
        raise ValueError(f"Unknown mode: {mode}. Available: {list(SCALE_MODES.keys())}")
    
    scale_degrees = SCALE_MODES[mode]
    keys = []
    
    # Determine default min_key and max_key if not specified
    if min_key is None:
        min_key = tonic
    
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
    
    # jump_predict mode: Use jump model for octave disambiguation
    if register_mode == "jump_predict":
        if chunk_mode != "pair_mod" or modulus != 12:
            raise ValueError("jump_predict mode requires chunk_mode='pair_mod' and modulus=12")
        
        if jump_model is None:
            raise ValueError("jump_predict mode requires jump_model")
        
        # First note: use tonic
        prev_key = tonic
        
        for value in values:
            pitch_class = value % 12
            
            # Predict best jump to reach this pitch class
            key = predict_jump_for_pitch_class(
                prev_key=prev_key,
                target_pc=pitch_class,
                min_key=min_key,
                max_key=max_key,
                jump_model=jump_model
            )
            
            keys.append(key)
            prev_key = key
        
        return keys
    
    # basic mode: Original algorithm
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
) -> Dict[int, int]:
    """
    Build jump histogram from style tracks for octave disambiguation.
    
    For each consecutive note pair in style tracks, record the signed jump
    (interval in semitones). This creates a statistical model of preferred
    melodic intervals for the jump_predict register mode.
    
    Args:
        style_tracks: List of tracks to learn from
    
    Returns:
        Dictionary mapping jump (in semitones) to count of occurrences
        
    Example:
        {
            0: 45,   # Repeated notes: 45 times
            1: 12,   # Half step up: 12 times
            -1: 8,   # Half step down: 8 times
            2: 15,   # Whole step up: 15 times
            4: 6,    # Major third up: 6 times (e.g. PC 3→7 could be +4 or -8)
            -8: 3,   # Major sixth down: 3 times (alternative for 3→7)
        }
    """
    jump_counts: Dict[int, int] = defaultdict(int)
    
    for track in style_tracks:
        if len(track.notes) < 2:
            continue
        
        # Sort notes by start time
        sorted_notes = sorted(track.notes, key=lambda n: n.start_beat)
        
        for i in range(1, len(sorted_notes)):
            prev_note = sorted_notes[i - 1]
            curr_note = sorted_notes[i]
            
            # Calculate signed jump (interval in semitones)
            jump = curr_note.key - prev_note.key
            
            # Clamp to reasonable melodic range (-24 to +24, within 2 octaves)
            if -24 <= jump <= 24:
                jump_counts[jump] += 1
    
    return dict(jump_counts)


def predict_jump_for_pitch_class(
    prev_key: int,
    target_pc: int,
    min_key: int,
    max_key: int,
    jump_model: Dict[int, int]
) -> int:
    """
    Predict best jump to reach target pitch class from previous key.
    
    Given a target pitch class (0-11) and previous key, find all candidate
    keys in [min_key, max_key] with that pitch class, then pick the one
    whose jump from prev_key has the highest likelihood in the jump model.
    
    Args:
        prev_key: Previous piano key (1-88)
        target_pc: Target pitch class (0-11)
        min_key: Minimum allowed key
        max_key: Maximum allowed key
        jump_model: Jump histogram from build_jump_model()
    
    Returns:
        Best piano key with target_pc that maximizes jump likelihood
        
    Example:
        >>> # PC 7 from key 40 (E) can be 43 (+3), 55 (+15), 31 (-9), etc.
        >>> # If jump_model prefers small intervals, picks 43 (+3)
        >>> # If jump_model prefers -8/-9, might pick 31 (-9)
        >>> predict_jump_for_pitch_class(40, 7, 28, 64, {3: 20, -9: 5, 15: 2})
        43
    """
    # Find all candidate keys with target pitch class in [min_key, max_key]
    candidates = []
    
    # Start from min_key and find first key with target PC
    first_candidate = min_key
    while first_candidate <= max_key:
        if (first_candidate - 1) % 12 == target_pc:  # Piano key 1 = A (PC 9)
            break
        first_candidate += 1
    
    # Generate all candidates by adding octaves
    key = first_candidate
    while key <= max_key:
        if (key - 1) % 12 == target_pc:
            candidates.append(key)
        key += 12
    
    if not candidates:
        # Fallback: if no candidates in range, clamp to range
        # and find closest key with target PC
        for offset in range(-12, 13):
            test_key = prev_key + offset
            if min_key <= test_key <= max_key and (test_key - 1) % 12 == target_pc:
                return test_key
        # Ultimate fallback: clamp prev_key to range
        return max(min_key, min(max_key, prev_key))
    
    # Score each candidate by jump likelihood
    best_key = candidates[0]
    best_score = -1
    
    for candidate_key in candidates:
        jump = candidate_key - prev_key
        score = jump_model.get(jump, 0)
        
        # Prefer smaller absolute jumps as tiebreaker (more melodic)
        # Add small bonus inversely proportional to absolute jump
        tiebreaker = 1.0 / (1.0 + abs(jump) * 0.1)
        total_score = score + tiebreaker
        
        if total_score > best_score:
            best_score = total_score
            best_key = candidate_key
    
    return best_key


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
    min_key: Optional[int] = None,
    max_key: Optional[int] = None,
    register_mode: Literal["basic", "jump_predict"] = "basic",
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
        octave_range: How many octaves to span (1-4)
        chunk_mode: "single" (one digit → scale degree) or "pair_mod" (digit pairs % modulus)
        modulus: For pair_mod, modulus to apply (12=chromatic, 7=diatonic, 5=pentatonic)
        min_key: Optional minimum key to clamp to (default: tonic)
        max_key: Optional maximum key to clamp to (default: comfortable register ~64)
        register_mode: "basic" (original) or "jump_predict" (octave disambiguation via jump model)
        duration_strategy: How to pick duration from histogram (mode/median/random)
        intensity: Track intensity parameter (default 1.0)
        hold_seconds: Track hold parameter (default 0.8)
        track_name: Custom track name (default auto-generated)
    
    Returns:
        Generated melody Track with notes
    
    Example:
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
        ...     bpm=96.0
        ... )
        >>> len(track.notes)
        7
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
    
    # 3. Build jump model if using jump_predict mode
    jump_model = None
    if register_mode == "jump_predict":
        jump_model = build_jump_model(style_tracks)
    
    # 4. Map values to keys
    keys = map_values_to_keys(
        values=values,
        tonic=tonic,
        mode=mode,
        chunk_mode=chunk_mode,
        modulus=modulus,
        octave_range=octave_range,
        min_key=min_key,
        max_key=max_key,
        jump_model=jump_model,
        register_mode=register_mode
    )
    
    # 5. Build duration model from style tracks
    duration_model = build_duration_model(style_tracks)
    
    # 6. Predict durations
    durations = predict_durations(keys, duration_model, strategy=duration_strategy)
    
    # 7. Create Note objects
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
    
    # 8. Create and return Track
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
        register_label = f", {register_mode}" if register_mode != "basic" else ""
        track_name = f"Number Melody ({seq_name}, {mode}, {chunk_label}{register_label})"
    
    return Track(
        name=track_name,
        intensity=intensity,
        hold_seconds=hold_seconds,
        delay=True,  # Delay adds nice space to melodies
        notes=notes
    )


def choose_offset_for_solo(
    pattern_digits: List[int],
    solo_track: Track,
    min_key: int,
    max_key: int
) -> int:
    """
    Choose offset that harmonizes pattern with solo track.
    
    Strategy: Find offset that maximizes consonance (pitch class compatibility)
    and keeps pattern in the target register under the solo.
    
    Args:
        pattern_digits: List of pattern digits (e.g., [3, 1, 4, 1, 5])
        solo_track: Solo track to harmonize with
        min_key: Minimum allowed key for bass
        max_key: Maximum allowed key for bass
    
    Returns:
        Best offset value (0-40)
        
    Algorithm:
        1. Extract pitch classes from solo (mod 12)
        2. For each candidate offset (0-40):
           - Map pattern digits to keys
           - Score based on:
             a. Consonance: How many pattern pitch classes are consonant with solo
             b. Register: Prefer offsets that keep pattern in [min_key, max_key]
        3. Return offset with best combined score
    """
    if not solo_track.notes or not pattern_digits:
        # Fallback: middle of bass range
        return (min_key + max_key) // 2 - min(pattern_digits)
    
    # Extract pitch classes from solo (mod 12)
    # Piano key 1 = A (pitch class 9)
    solo_pitch_classes = set()
    for note in solo_track.notes:
        pc = (note.key - 1) % 12
        solo_pitch_classes.add(pc)
    
    # Consonant intervals (unison, thirds, fourths, fifths, sixths, octave)
    CONSONANT_INTERVALS = {0, 3, 4, 5, 7, 8, 9, 12}
    
    best_offset = 10
    best_score = -1
    
    # Try offsets from 0 to 40
    for offset in range(0, 41):
        # Map pattern digits to keys with this offset
        pattern_keys = []
        for digit in pattern_digits:
            key = digit + offset
            key = max(min_key, min(max_key, key))
            pattern_keys.append(key)
        
        # Score 1: Consonance with solo
        consonance_score = 0
        for pattern_key in pattern_keys:
            pattern_pc = (pattern_key - 1) % 12
            
            # Check intervals with all solo pitch classes
            for solo_pc in solo_pitch_classes:
                interval = abs(pattern_pc - solo_pc)
                # Consider both upward and downward intervals
                interval = min(interval, 12 - interval)
                
                if interval in CONSONANT_INTERVALS:
                    consonance_score += 1
        
        # Score 2: Register fitness (prefer middle of bass range)
        avg_key = sum(pattern_keys) / len(pattern_keys)
        target_center = (min_key + max_key) / 2
        register_score = 1.0 / (1.0 + abs(avg_key - target_center) * 0.5)
        
        # Combined score (weighted)
        total_score = consonance_score + register_score * 5.0
        
        if total_score > best_score:
            best_score = total_score
            best_offset = offset
    
    return best_offset


def generate_pattern_bass_from_solo(
    pattern_string: str,
    solo_track: Track,
    style_tracks: List[Track],
    bpm: float = 96.0,
    offset_mode: Literal["manual", "auto"] = "auto",
    manual_offset: int = 10,
    min_key: int = 28,
    max_key: int = 42,
    duration_strategy: Literal["mode", "median", "random"] = "mode",
    intensity: float = 2.0,
    hold_seconds: float = 2.0,
    loop_pattern: bool = True,
    track_name: Optional[str] = None
) -> Track:
    """
    Generate ordered bass track from pattern that harmonizes under a Solo track.
    
    This is the evolved Pattern → Base feature that considers Solo for:
    - Auto-choosing offset to harmonize with solo pitch classes
    - Stretching/looping pattern timing to match solo span
    
    Args:
        pattern_string: Pattern sequence (e.g., "3-1-4-1-5")
        solo_track: Solo track to harmonize with (required for auto offset and timing)
        style_tracks: Tracks to learn durations from (can be from multiple MIDIs)
        bpm: Tempo (default 96)
        offset_mode: "manual" (use manual_offset) or "auto" (choose offset from solo)
        manual_offset: For manual mode, add this to each digit
        min_key: Minimum bass key (default 28 = E1)
        max_key: Maximum bass key (default 42 = F#2)
        duration_strategy: How to pick duration from histogram (mode/median/random)
        intensity: Track intensity parameter (default 2.0 for bass)
        hold_seconds: Track hold parameter (default 2.0 for bass sustain)
        loop_pattern: If True, loop pattern to fill solo span; if False, stretch timing
        track_name: Custom track name (default auto-generated)
    
    Returns:
        Generated bass Track with ordered pattern notes harmonized under solo
    
    Example:
        >>> # Solo track exists with span 0-16 beats
        >>> # Pattern "3-1-4-1-5" auto-harmonized under solo
        >>> style_songs = [load_midi("demos/chopin-etude.mid")]
        >>> style_tracks = []
        >>> for song in style_songs:
        ...     style_tracks.extend(song.tracks)
        >>> solo = Track(name="Solo", notes=[...])
        >>> track = generate_pattern_bass_from_solo(
        ...     "3-1-4-1-5",
        ...     solo_track=solo,
        ...     style_tracks=style_tracks,
        ...     offset_mode="auto",  # Auto-choose offset from solo
        ...     min_key=28,
        ...     max_key=42,
        ...     bpm=96.0
        ... )
        >>> len(track.notes) >= 5  # At least one pattern iteration
        True
    """
    # 1. Parse pattern string (supports dash or comma separators)
    pattern_string = pattern_string.replace(",", "-")
    digits = []
    for part in pattern_string.split("-"):
        part = part.strip()
        if part.isdigit():
            digits.append(int(part))
    
    if not digits:
        # No valid digits found, return empty track
        return Track(
            name=track_name or "Pattern Bass from Solo (empty)",
            intensity=intensity,
            hold_seconds=hold_seconds,
            notes=[]
        )
    
    # 2. Choose offset (manual or auto from solo)
    if offset_mode == "auto":
        bass_offset = choose_offset_for_solo(digits, solo_track, min_key, max_key)
    else:
        bass_offset = manual_offset
    
    # 3. Map pattern digits to bass keys
    keys = []
    for digit in digits:
        key = digit + bass_offset
        # Clamp to bass range
        key = max(min_key, min(max_key, key))
        keys.append(key)
    
    # 4. Build duration model from style tracks
    duration_model = build_duration_model(style_tracks)
    
    # 5. Predict durations for one pattern iteration
    durations = predict_durations(keys, duration_model, strategy=duration_strategy)
    
    # 6. Determine solo span for timing
    if solo_track.notes:
        solo_start = min(n.start_beat for n in solo_track.notes)
        solo_end = max(n.start_beat + n.duration_beats for n in solo_track.notes)
        solo_span = solo_end - solo_start
    else:
        # No solo notes, use default span
        solo_span = sum(durations)
    
    # 7. Create notes with timing stretched/looped to match solo span
    notes = []
    current_beat = 0.0
    pattern_duration = sum(durations)
    
    if loop_pattern and pattern_duration > 0:
        # Loop pattern to fill solo span
        iterations_needed = max(1, int(solo_span / pattern_duration) + 1)
        
        for iteration in range(iterations_needed):
            for key, duration in zip(keys, durations):
                if current_beat >= solo_span:
                    break
                
                # Clamp duration to not exceed solo span
                actual_duration = min(duration, solo_span - current_beat)
                if actual_duration <= 0:
                    break
                
                note = Note(
                    key=key,
                    start_beat=current_beat,
                    duration_beats=actual_duration,
                    velocity=100
                )
                notes.append(note)
                current_beat += actual_duration
            
            if current_beat >= solo_span:
                break
    else:
        # Single pattern iteration, stretch timing to fit solo span if needed
        if solo_span > pattern_duration and pattern_duration > 0:
            # Stretch: multiply all durations proportionally
            stretch_factor = solo_span / pattern_duration
            stretched_durations = [d * stretch_factor for d in durations]
        else:
            stretched_durations = durations
        
        for key, duration in zip(keys, stretched_durations):
            note = Note(
                key=key,
                start_beat=current_beat,
                duration_beats=duration,
                velocity=100
            )
            notes.append(note)
            current_beat += duration
    
    # 8. Create and return Track
    if track_name is None:
        # Auto-generate name
        pattern_prefix = pattern_string[:15].replace(" ", "")
        offset_label = f"auto@{bass_offset}" if offset_mode == "auto" else f"offset{bass_offset}"
        track_name = f"Pattern Bass from Solo ({pattern_prefix}, {offset_label})"
    
    return Track(
        name=track_name,
        intensity=intensity,
        hold_seconds=hold_seconds,
        delay=False,  # Bass typically doesn't use delay
        notes=notes
    )


def generate_pattern_bass(
    pattern_string: str,
    style_tracks: List[Track],
    bpm: float = 96.0,
    mode: Literal["offset", "tonic_scale"] = "offset",
    bass_offset: int = 10,
    tonic: Optional[int] = None,
    scale_mode: str = "chromatic",
    min_key: int = 28,
    max_key: int = 42,
    duration_strategy: Literal["mode", "median", "random"] = "mode",
    use_jump_predict: bool = False,
    intensity: float = 2.0,
    hold_seconds: float = 2.0,
    track_name: Optional[str] = None
) -> Track:
    """
    Generate bass track from ordered pattern sequence (e.g., Pi digits "3-1-4-1-5").
    
    This addresses the use case where the user wants a bass line that follows a specific
    ordered pattern of degrees/digits, not arbitrary bass notes extracted from donors.
    
    Args:
        pattern_string: Pattern sequence (e.g., "3-1-4-1-5" or "3,1,4,1,5")
        style_tracks: Tracks to learn durations from (can be from multiple MIDIs)
        bpm: Tempo (default 96)
        mode: "offset" (digit + offset) or "tonic_scale" (tonic + scale degree)
        bass_offset: For offset mode, add this to each digit (e.g., 3 + 10 = key 13)
        tonic: For tonic_scale mode, root key in bass register (e.g., 16 for E0)
        scale_mode: For tonic_scale mode, scale to use (default chromatic)
        min_key: Minimum bass key (default 28 = E1)
        max_key: Maximum bass key (default 42 = F#2)
        duration_strategy: How to pick duration from histogram (mode/median/random)
        use_jump_predict: Use jump model for duration/jump prediction within bass range
        intensity: Track intensity parameter (default 2.0 for bass)
        hold_seconds: Track hold parameter (default 2.0 for bass sustain)
        track_name: Custom track name (default auto-generated)
    
    Returns:
        Generated bass Track with ordered pattern notes
    
    Example:
        >>> # Pi pattern "3-1-4-1-5" with offset mode
        >>> style_songs = [load_midi("demos/chopin-etude.mid")]
        >>> style_tracks = []
        >>> for song in style_songs:
        ...     style_tracks.extend(song.tracks)
        >>> track = generate_pattern_bass(
        ...     "3-1-4-1-5",
        ...     style_tracks=style_tracks,
        ...     mode="offset",
        ...     bass_offset=10,  # 3→13, 1→11, 4→14, 1→11, 5→15
        ...     min_key=28,
        ...     max_key=42,
        ...     bpm=96.0
        ... )
        >>> len(track.notes)
        5
    """
    # 1. Parse pattern string (supports dash or comma separators)
    pattern_string = pattern_string.replace(",", "-")
    digits = []
    for part in pattern_string.split("-"):
        part = part.strip()
        if part.isdigit():
            digits.append(int(part))
    
    if not digits:
        # No valid digits found, return empty track
        return Track(
            name=track_name or "Pattern Bass (empty)",
            intensity=intensity,
            hold_seconds=hold_seconds,
            notes=[]
        )
    
    # 2. Map pattern digits to bass keys
    keys = []
    
    if mode == "offset":
        # Simple offset mode: digit + bass_offset
        for digit in digits:
            key = digit + bass_offset
            # Clamp to bass range
            key = max(min_key, min(max_key, key))
            keys.append(key)
    
    elif mode == "tonic_scale":
        # Tonic + scale degree mode
        if tonic is None:
            tonic = min_key  # Default to min_key if not specified
        
        if scale_mode not in SCALE_MODES:
            scale_mode = "chromatic"
        
        scale_degrees = SCALE_MODES[scale_mode]
        
        for digit in digits:
            # Map digit to scale degree
            degree_idx = digit % len(scale_degrees)
            semitone_offset = scale_degrees[degree_idx]
            key = tonic + semitone_offset
            
            # Clamp to bass range
            key = max(min_key, min(max_key, key))
            keys.append(key)
    
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'offset' or 'tonic_scale'.")
    
    # 3. Build duration model from style tracks
    duration_model = build_duration_model(style_tracks)
    
    # 4. Optionally use jump model for more sophisticated duration prediction
    jump_model = None
    if use_jump_predict:
        jump_model = build_jump_model(style_tracks)
        
        # Refine keys using jump prediction within bass range
        # This allows the AI to pick octave jumps within [min_key, max_key]
        # based on learned jump patterns from style MIDIs
        refined_keys = []
        prev_key = keys[0] if keys else min_key
        refined_keys.append(prev_key)
        
        for i in range(1, len(keys)):
            target_pc = (keys[i] - 1) % 12  # Pitch class of intended key
            
            # Find best jump to reach this pitch class within bass range
            best_key = predict_jump_for_pitch_class(
                prev_key=prev_key,
                target_pc=target_pc,
                min_key=min_key,
                max_key=max_key,
                jump_model=jump_model
            )
            
            refined_keys.append(best_key)
            prev_key = best_key
        
        keys = refined_keys
    
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
        # Auto-generate name
        pattern_prefix = pattern_string[:15].replace(" ", "")
        mode_label = "offset" if mode == "offset" else f"{scale_mode}"
        jump_label = ", jump" if use_jump_predict else ""
        track_name = f"Pattern Bass ({pattern_prefix}, {mode_label}{jump_label})"
    
    return Track(
        name=track_name,
        intensity=intensity,
        hold_seconds=hold_seconds,
        delay=False,  # Bass typically doesn't use delay
        notes=notes
    )


def main():
    """CLI for number melody generation."""
    parser = argparse.ArgumentParser(
        description="Generate melody from digit string with learned durations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single style, pair_mod with chromatic (modulus 12):
  python number_melody.py --digits 314159265358979 --tonic 48 \\
    --chunk pair_mod --modulus 12 --style demos/chopin-etude.mid \\
    --out pi_chromatic.mid --bpm 96 --max-key 60

  # Multiple styles with jump_predict (octave disambiguation):
  python number_melody.py --digits 314159265358979 --tonic 40 \\
    --chunk pair_mod --modulus 12 --register jump_predict \\
    --min-key 28 --max-key 64 \\
    --style demos/chopin-etude.mid --style demos/liszt-preludio.mid \\
    --style demos/scarlatti-sonata.mid --out pi_jump_predict.mid --bpm 96

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
        "--min-key",
        type=int,
        default=None,
        help="Minimum key to clamp to (default: tonic)"
    )
    parser.add_argument(
        "--max-key",
        type=int,
        default=None,
        help="Maximum key to clamp to (default: auto, typically ~64 for comfortable register)"
    )
    parser.add_argument(
        "--register",
        choices=["basic", "jump_predict"],
        default="basic",
        help="Register mode: 'basic' (original) or 'jump_predict' (octave disambiguation, default: basic)"
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
    print(f"  Register mode={args.register}")
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
        min_key=args.min_key,
        max_key=args.max_key,
        register_mode=args.register,
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
