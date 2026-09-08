"""Editor session model for multi-MIDI track-role workflow."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Tuple
import uuid
from copy import deepcopy

from notes import Song, Track, Note


TrackRole = Literal["final", "mashup_source", "ignore"]


@dataclass
class MidiSource:
    """A loaded MIDI source with unique ID."""
    id: str
    name: str
    song: Song
    filepath: Optional[str] = None


@dataclass
class TrackMetadata:
    """Metadata for a track in a source."""
    source_id: str
    track_index: int
    role: TrackRole = "ignore"
    key_lo: Optional[int] = None  # Only use notes >= key_lo
    key_hi: Optional[int] = None  # Only use notes <= key_hi


class EditorSession:
    """
    Manages multiple MIDI sources with track role assignments.
    
    Workflow:
    1. Load multiple MIDI sources (from files or demos)
    2. Assign each track a role: final, mashup_source, or ignore
    3. Optionally set key range filters per track
    4. Compose final song from all tracks with role="final"
    5. Get mashup source tracks for pattern generation
    """
    
    def __init__(self):
        self.sources: List[MidiSource] = []
        self.base_source_id: Optional[str] = None
        self.track_metadata: Dict[Tuple[str, int], TrackMetadata] = {}
    
    def add_source(self, name: str, song: Song, filepath: Optional[str] = None) -> str:
        """
        Add a MIDI source to the session.
        
        Returns:
            source_id: Unique ID for this source
        """
        source_id = str(uuid.uuid4())
        source = MidiSource(
            id=source_id,
            name=name,
            song=song,
            filepath=filepath
        )
        self.sources.append(source)
        
        # Initialize track metadata with default "ignore" role
        for track_idx in range(len(song.tracks)):
            key = (source_id, track_idx)
            self.track_metadata[key] = TrackMetadata(
                source_id=source_id,
                track_index=track_idx,
                role="ignore"
            )
        
        # Set as base if it's the first source
        if len(self.sources) == 1:
            self.base_source_id = source_id
        
        return source_id
    
    def remove_source(self, source_id: str) -> bool:
        """Remove a source and its track metadata."""
        source = self.get_source(source_id)
        if source is None:
            return False
        
        self.sources.remove(source)
        
        # Remove track metadata
        keys_to_remove = [k for k in self.track_metadata.keys() if k[0] == source_id]
        for key in keys_to_remove:
            del self.track_metadata[key]
        
        # Clear base if this was it
        if self.base_source_id == source_id:
            self.base_source_id = self.sources[0].id if self.sources else None
        
        return True
    
    def get_source(self, source_id: str) -> Optional[MidiSource]:
        """Get a source by ID."""
        for source in self.sources:
            if source.id == source_id:
                return source
        return None
    
    def set_base_source(self, source_id: str) -> bool:
        """Set which source is the base."""
        if self.get_source(source_id) is not None:
            self.base_source_id = source_id
            return True
        return False
    
    def set_track_role(
        self,
        source_id: str,
        track_index: int,
        role: TrackRole,
        key_lo: Optional[int] = None,
        key_hi: Optional[int] = None
    ) -> bool:
        """Set the role and key range for a track."""
        key = (source_id, track_index)
        if key not in self.track_metadata:
            return False
        
        self.track_metadata[key].role = role
        self.track_metadata[key].key_lo = key_lo
        self.track_metadata[key].key_hi = key_hi
        return True
    
    def get_track_metadata(self, source_id: str, track_index: int) -> Optional[TrackMetadata]:
        """Get metadata for a track."""
        return self.track_metadata.get((source_id, track_index))
    
    def filter_track_notes(self, track: Track, key_lo: Optional[int], key_hi: Optional[int]) -> Track:
        """
        Create a copy of track with notes filtered by key range.
        
        Args:
            track: Original track
            key_lo: Minimum key (inclusive), or None for no lower bound
            key_hi: Maximum key (inclusive), or None for no upper bound
        
        Returns:
            New track with filtered notes
        """
        if key_lo is None and key_hi is None:
            return deepcopy(track)
        
        filtered_notes = []
        for note in track.notes:
            if key_lo is not None and note.key < key_lo:
                continue
            if key_hi is not None and note.key > key_hi:
                continue
            filtered_notes.append(deepcopy(note))
        
        filtered_track = deepcopy(track)
        filtered_track.notes = filtered_notes
        return filtered_track
    
    def compose_final_song(self) -> Song:
        """
        Compose final song from all tracks with role="final".
        
        Returns:
            Song with all final tracks merged (respecting mute and key filters)
        """
        final_tracks = []
        bpm = 120.0
        
        # Get BPM from base source if available
        if self.base_source_id:
            base_source = self.get_source(self.base_source_id)
            if base_source:
                bpm = base_source.song.bpm
        
        # Collect all tracks with role="final"
        for source in self.sources:
            for track_idx, track in enumerate(source.song.tracks):
                metadata = self.get_track_metadata(source.id, track_idx)
                if metadata and metadata.role == "final":
                    # Apply key range filter
                    filtered_track = self.filter_track_notes(
                        track,
                        metadata.key_lo,
                        metadata.key_hi
                    )
                    
                    # Rename track to include source name
                    filtered_track.name = f"{source.name} - {track.name}"
                    final_tracks.append(filtered_track)
        
        return Song(bpm=bpm, tracks=final_tracks)
    
    def get_mashup_sources(self) -> List[Track]:
        """
        Get all tracks with role="mashup_source".
        
        Returns:
            List of tracks to use as mashup/adorn donors
        """
        mashup_tracks = []
        
        for source in self.sources:
            for track_idx, track in enumerate(source.song.tracks):
                metadata = self.get_track_metadata(source.id, track_idx)
                if metadata and metadata.role == "mashup_source":
                    # Apply key range filter
                    filtered_track = self.filter_track_notes(
                        track,
                        metadata.key_lo,
                        metadata.key_hi
                    )
                    
                    # Rename track to include source name
                    filtered_track.name = f"{source.name} - {track.name} (mashup)"
                    mashup_tracks.append(filtered_track)
        
        return mashup_tracks
    
    def get_all_tracks_with_roles(self) -> List[Tuple[MidiSource, Track, TrackMetadata]]:
        """
        Get all tracks from all sources with their metadata.
        
        Returns:
            List of (source, track, metadata) tuples
        """
        result = []
        for source in self.sources:
            for track_idx, track in enumerate(source.song.tracks):
                metadata = self.get_track_metadata(source.id, track_idx)
                if metadata:
                    result.append((source, track, metadata))
        return result
