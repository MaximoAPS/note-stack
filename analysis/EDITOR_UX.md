# Editor UX — Note Stack Multi-MIDI / Track-Role Workflow

## Product Vision

Note Stack Editor enables Maximo and other users to create complex music using:
- **Multiple MIDI files** as sources (bases, samples, styles)
- **Track role assignment**: final, mashup_source, ignore
- **AI track generation** conditioned on key ranges
- **Per-note editing** with visual interface
- **Per-track FX** (intensity, delay, etc.)

### Ideal User Flow

1. **Upload multiple MIDIs** (local demos or own files)
2. **Pick one as base** — the primary source for structure
3. **Mark each track's role**:
   - `final` → goes to composed song / Play output
   - `mashup_source` → used to train/feed mashup / adorn / AI (donors)
   - `ignore` → discarded
4. **Load additional mashup/style MIDIs** and assign their tracks the same way
5. **Add AI tracks** conditioned on key range:
   - Bass (keys 1-28)
   - Chord base (keys 29-52)
   - Adorn plucks (keys 45-72)
   - Harmony / solo lines
6. **Edit/delete individual notes** (already partly there — keep/improve)
7. **Per-track FX** (wire existing fx.py per track if feasible; global FX exists today)
8. **Full editor in UI** — not buried in one-shot Adorn/Mashup buttons only

---

## Implementation Roadmap

### Phase 1: Editor Foundation (Current — Usable MVP)

**Goal**: Maximo can use the multi-MIDI/track-role basic workflow immediately.

**Deliverables**:

1. **Session model** (`editor_session.py`):
   - Library of loaded MIDI sources (id, name, Song with tracks)
   - Per-track metadata: `source_id`, `role` ∈ {final, mashup_source, ignore}, optional `key_lo`/`key_hi` filters
   - Compose `Song` for Play from all tracks with role=final (respecting mute)

2. **UI section "Editor"** (primary workflow):
   - Multi-file uploader + demos picker to add sources
   - Radio/select: which source is **base**
   - Table/expanders: every track from every source with role dropdown + mute + intensity + key-range filter
   - Buttons:
     - **Compose Final** → build session song from final tracks
     - **Run Adorn/Mashup** → use mashup_source tracks as donors and base final solo/base logic
   - **Add AI Track** panel:
     - Type: bass | chords | adorn_pluck | adorn_harmony
     - key_lo–key_hi
     - Donor/style source
     - Generate → appends new Track with role=final
     - (use existing jump/decorate helpers filtered by key range; if full AI model missing, use best existing jump heuristic and label clearly as V1)
   - Keep existing note table editor + delete range on composed song
   - Per-track FX: at least intensity/mute/delay already; if easy, store wet overrides per track name for future render path

3. **Preserve multi-track MIDIs** Madonna-style:
   - Verify load keeps tracks separate
   - Editor can set R→final solo, L→ignore or mashup_source

4. **Smoke test**: app imports; basic unit test for compose-from-roles if practical

5. **Updated docs**:
   - README (English) with short "Editor" section pointing to new UX
   - This document (es+en)

6. **PR opened** with clear summary

**Constraints**:
- Do NOT change Desmos base synth formulas
- Do NOT commit secrets; no pass.txt
- Prefer incremental refactor of app.py over total rewrite
- Spanish UI labels OK alongside English captions if helpful for Maximo

---

### Phase 2: Specialist Models + Visual Editor (Planned)

**Do not block Phase 1** — document only:

1. **True specialist models** / style pack training UI
2. **Piano-roll visual editor** (interactive drag-drop timeline)
3. **Per-track wet FX** in stereo render (full per-track fx.py wire)
4. **NBS import** in UI (NetherBeatmap Studio format)
5. **Parameter automation** (intensity, hold curves over time)

---

### Phase 3: Collaboration + Export (Future)

1. **Save/load projects** (JSON serialization of session)
2. **Share presets** for FX and style packs
3. **Export stems** (per-track WAV for external mixing)
4. **Live mode** (real-time MIDI input performance)

---

## Phase 1 Success Criteria

✅ User can:
- Upload 2+ MIDIs
- Mark track roles
- Compose final from marked tracks
- Run adorn using mashup tracks
- Add key-range-conditioned AI/heuristic track
- Edit/delete notes
- Play/download

✅ PR opened
✅ Docs written
✅ Smoke test passes

---

## Technical Notes

### Data Model

```python
# editor_session.py (new)
@dataclass
class MidiSource:
    id: str  # uuid
    name: str
    song: Song  # from notes.py
    filepath: Optional[str]

@dataclass
class TrackMetadata:
    source_id: str
    track_index: int  # index in source.song.tracks
    role: Literal["final", "mashup_source", "ignore"]
    key_lo: Optional[int] = None  # filter: only use notes >= key_lo
    key_hi: Optional[int] = None  # filter: only use notes <= key_hi

class EditorSession:
    sources: List[MidiSource]
    base_source_id: Optional[str]  # which source is "base"
    track_metadata: Dict[tuple[str, int], TrackMetadata]  # (source_id, track_idx) -> meta
    
    def compose_final_song(self) -> Song:
        # Merge all tracks with role="final", respecting mute + key filters
        pass
    
    def get_mashup_sources(self) -> List[Track]:
        # Get all tracks with role="mashup_source"
        pass
```

### Pattern Generators (Phase 1 Heuristics)

```python
# pattern_generators.py (new)
def generate_bass_pattern(
    donor_tracks: List[Track],
    key_range: tuple[int, int],
    num_beats: float,
    bpm: float
) -> Track:
    """Generate bass line from donor tracks, filtered to key range."""
    # V1: Extract lowest notes from donors in range, thin out to beat grid
    pass

def generate_chord_pattern(
    donor_tracks: List[Track],
    key_range: tuple[int, int],
    num_beats: float,
    bpm: float
) -> Track:
    """Generate chord pattern from donor tracks."""
    # V1: Extract note clusters from donors, quantize to grid
    pass

def generate_adorn_pluck(
    donor_tracks: List[Track],
    key_range: tuple[int, int],
    num_beats: float,
    bpm: float
) -> Track:
    """Generate adorn/pluck decoration."""
    # V1: Extract sparse high notes from donors, rhythm variation
    pass
```

### UI Components

- **Sources Panel**: List of loaded MIDIs with add/remove
- **Base Selector**: Radio button to pick base source
- **Track Roles Table**: Per-track dropdowns for role assignment
- **Compose Button**: Build final song from role=final tracks
- **AI Track Panel**: Form to generate new tracks
- **Note Editor**: Existing table editor (keep/improve)

---

## References

- **Desmos Piano Song**: https://www.desmos.com/calculator/iilldhgqnk
- **MAESTRO Dataset**: https://magenta.tensorflow.org/datasets/maestro
- **Note Stack Repo**: https://github.com/MaximoAPS/note-stack

---

**Author**: Cloud Agent + Maximo
**Date**: Sep 2026
**Version**: 1.0 (Phase 1 Foundation)
