"""Test synthesis by rendering Piano Song melody track."""

import sys
from notes import Song, Track, Note
from synth import export_wav


def test_piano_song_melody():
    """Render melody track of Piano Song to verify synthesis works."""
    bpm = 160
    
    # Track 1: Melody only
    tempo_list = [i * 0.5 for i in range(0, 30)] + [15, 16]
    notes = [57,54,49,54,57,54,49,54,57,52,49,52,57,52,49,52,
             57,53,49,53,57,53,49,53,57,53,49,53,57,62]
    
    track_notes = []
    for i, key in enumerate(notes):
        start_sec = tempo_list[i]
        end_sec = tempo_list[i + 1]
        duration_sec = end_sec - start_sec
        
        start_beat = start_sec * bpm / 60
        duration_beats = duration_sec * bpm / 60
        
        track_notes.append(Note(key=key, start_beat=start_beat, 
                               duration_beats=duration_beats))
    
    melody_track = Track(name="Melody", intensity=1.0, delay=True, 
                        hold_seconds=0.8, notes=track_notes)
    
    song = Song(bpm=bpm, tracks=[melody_track])
    
    # Export to WAV
    output_path = "/tmp/test_piano_song_melody.wav"
    print(f"Rendering melody to {output_path}...")
    export_wav(output_path, song)
    
    # Check file was created and has reasonable size
    import os
    if not os.path.exists(output_path):
        print("ERROR: WAV file was not created")
        sys.exit(1)
    
    file_size = os.path.getsize(output_path)
    print(f"WAV file created: {file_size} bytes")
    
    # Check duration (should be at least 1 second)
    import wave
    with wave.open(output_path, 'rb') as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        duration = frames / rate
        print(f"Duration: {duration:.2f} seconds")
        
        if duration < 1.0:
            print(f"ERROR: Duration {duration:.2f}s is less than 1 second")
            sys.exit(1)
    
    print("✓ Synthesis test passed!")
    return True


if __name__ == "__main__":
    test_piano_song_melody()
