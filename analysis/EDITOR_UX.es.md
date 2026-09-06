# Editor UX — Note Stack Multi-MIDI / Track-Role Workflow

## Visión del Producto

Note Stack Editor permite a Maximo y otros usuarios crear música compleja utilizando:
- **Múltiples archivos MIDI** como fuentes (bases, samples, estilos)
- **Asignación de roles por pista**: final, mashup_source, ignore
- **Generación de pistas AI** condicionadas por rangos de teclas
- **Edición por nota** con interfaz visual
- **FX por pista** (intensidad, delay, etc.)

### Flujo Ideal del Usuario

1. **Subir múltiples MIDIs** (demos locales o archivos propios)
2. **Seleccionar MIDI base** — la fuente principal para la estructura
3. **Marcar rol de cada pista**:
   - `final` → va a la canción compuesta / salida Play
   - `mashup_source` → usado para entrenar/alimentar mashup / adorn / AI (donantes)
   - `ignore` → descartado
4. **Cargar MIDIs adicionales** de mashup/estilo y asignar sus pistas igual
5. **Agregar pistas AI** condicionadas por rango de teclas:
   - Bass (teclas 1-28)
   - Chord base (teclas 29-52)
   - Adorn plucks (teclas 45-72)
   - Harmony / solo lines
6. **Editar/eliminar notas individuales** (ya existe parcialmente — mantener/mejorar)
7. **FX por pista** (wire fx.py existente por pista si es factible; FX global existe hoy)
8. **Editor completo en UI** — no enterrado solo en botones one-shot de Adorn/Mashup

---

## Roadmap de Implementación

### Phase 1: Editor Foundation (Actual — Usable MVP)

**Objetivo**: Maximo puede usar el workflow multi-MIDI/track-role básico inmediatamente.

**Entregables**:

1. **Modelo de sesión** (`editor_session.py`):
   - Biblioteca de fuentes MIDI cargadas (id, nombre, Song con pistas)
   - Metadatos por pista: `source_id`, `role` ∈ {final, mashup_source, ignore}, filtros opcionales `key_lo`/`key_hi`
   - Componer `Song` para Play desde todas las pistas con role=final (respetando mute)

2. **Sección UI "Editor"** (workflow principal):
   - Subidor multi-archivo + selector de demos para agregar fuentes
   - Radio/select: cual fuente es **base**
   - Tabla/expanders: cada pista de cada fuente con dropdown de rol + mute + intensidad + filtro de rango de teclas
   - Botones:
     - **Compose Final** → construye song de sesión desde pistas finales
     - **Run Adorn/Mashup** → usa pistas mashup_source como donantes y lógica base final solo/base
   - Panel **Add AI Track**:
     - Tipo: bass | chords | adorn_pluck | adorn_harmony
     - key_lo–key_hi
     - Fuente donante/estilo
     - Generate → agrega nueva Track con role=final
     - (usa helpers de jump/decorate existentes filtrados por key range; si falta modelo AI completo, usa mejor heurística jump existente y etiquetarla claramente como V1)
   - Mantener editor de tabla de notas existente + delete range en song compuesto
   - FX por pista: al menos intensidad/mute/delay ya; si es fácil, guardar overrides wet por nombre de pista para path de render futuro

3. **Preservar MIDIs multi-pista** estilo Madonna:
   - Verificar que load mantiene pistas separadas
   - Editor puede configurar R→final solo, L→ignore o mashup_source

4. **Smoke test**: app imports; test unitario básico para compose-from-roles si es práctico

5. **Docs actualizados**:
   - README (inglés) con sección "Editor" corta apuntando a nuevo UX
   - Este documento (es+en)

6. **PR abierto** con resumen claro

**Restricciones**:
- NO cambiar fórmulas synth Desmos base
- NO commit secrets; sin pass.txt
- Preferir refactor incremental de app.py sobre reescritura total
- Etiquetas UI en español OK junto con captions en inglés si ayuda a Maximo

---

### Phase 2: Specialist Models + Visual Editor (Planificado)

**No bloquear Phase 1** — solo documentar:

1. **Modelos especialistas reales** / entrenamiento de style packs en UI
2. **Editor piano-roll visual** (timeline interactivo drag-drop)
3. **FX wet por pista** en render estéreo (wire completo fx.py per-track)
4. **Importar NBS** en UI (NetherBeatmap Studio format)
5. **Automación de parámetros** (intensity, hold curves over time)

---

### Phase 3: Collaboration + Export (Futuro)

1. **Guardar/cargar proyectos** (JSON serialization de session)
2. **Compartir presets** de FX y style packs
3. **Export stems** (WAV per-track para mezcla externa)
4. **Live mode** (performance MIDI input en tiempo real)

---

## Criterios de Éxito Phase 1

✅ Usuario puede:
- Subir 2+ MIDIs
- Marcar roles de pistas
- Componer final desde pistas marcadas
- Correr adorn usando pistas mashup
- Agregar pista AI/heurística condicionada por key-range
- Editar/eliminar notas
- Play/download

✅ PR abierto
✅ Docs escritos
✅ Smoke test pasa

---

## Notas Técnicas

### Data Model

```python
# editor_session.py (nuevo)
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
# pattern_generators.py (nuevo)
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

## Referencias

- **Desmos Piano Song**: https://www.desmos.com/calculator/iilldhgqnk
- **MAESTRO Dataset**: https://magenta.tensorflow.org/datasets/maestro
- **Note Stack Repo**: https://github.com/MaximoAPS/note-stack

---

**Autor**: Cloud Agent + Maximo
**Fecha**: Sep 2026
**Versión**: 1.0 (Phase 1 Foundation)
