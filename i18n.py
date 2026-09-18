"""Tiny EN/ES string table for the Studio UI. Default language is English."""

from typing import Dict

LANGS = ("en", "es")

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        "lang_label": "Language",
        "caption": "Number Melody generator • AI track tools • Piano key synthesis from Desmos",
        "key_legend": (
            "Piano keys are 1–88 (A0–C8), not MIDI note numbers. "
            "Middle C = key 40. A4 = key 49 (440 Hz). MIDI note = piano key + 20."
        ),
        "style_title": "Style / Training MIDI Library — Load & train optional AI models",
        "style_caption": (
            "Upload MIDIs freely → Train once. Generators use trained models if available, "
            "otherwise MidiGPT (built-in piano prior) / heuristics."
        ),
        "style_upload": "Upload Style MIDIs",
        "add_uploads": "Add uploads to pack",
        "demos": "Classical Demos",
        "add_demos": "Add selected demos",
        "add_all_demos": "Add all classical demos",
        "train": "Train models from style pack",
        "clear_pack": "Clear pack",
        "not_trained": "Not trained — MidiGPT fallback is active",
        "trained": "Trained on {n} track(s)",
        "melody_title": "Number Sequence → Solo / Melody",
        "melody_caption": "Paste digit sequences (Pi, Fibonacci, dates) • Generate Solo • Or upload a solo MIDI",
        "digits": "Digit String",
        "generate_solo": "Generate Solo Melody from Numbers",
        "pattern_title": "Pattern → Base — Ordered bass from a digit pattern",
        "pattern_caption": (
            "Digits are pattern degrees/offsets, not raw piano keys 1–5. "
            "Example Pi `31415` → bass with those relative tones in order."
        ),
        "generate_bass": "Generate Pattern Bass",
        "fill_solo_title": "Fill Base from Solo — Ordered pattern harmonized under Solo",
        "studio_title": "Tracks Studio",
        "studio_caption": "Add tracks • Assign roles (Solo/Base/Adorn) • Generate AI fills • Edit notes • Set FX",
        "role": "Role",
        "role_help": "Used by Fill Base / AI tools. Independent from the display name.",
        "play": "Play",
        "prepare_wav": "Prepare WAV",
        "prepare_midi": "Prepare MIDI",
        "add_track": "Add Empty Track",
        "ai_fill": "AI Fill Track (V1 heuristics + MidiGPT fallback)",
        "loop": "Loop",
        "loop_help": "Repeat this pattern until the song ends (song end = last non-looped track).",
        "loop_beats": "Pattern cycle (beats)",
        "loop_beats_help": "0 = use the written notes as the cycle. The cycle repeats until the song ends.",
        "no_tracks": "No tracks yet. Generate a Number Melody above or add an empty track.",
    },
    "es": {
        "lang_label": "Idioma",
        "caption": "Generador Number Melody • Herramientas AI • Síntesis de piano Desmos",
        "key_legend": (
            "Las teclas de piano son 1–88 (A0–C8), no números MIDI. "
            "Do central = tecla 40. A4 = tecla 49 (440 Hz). Nota MIDI = tecla de piano + 20."
        ),
        "style_title": "Biblioteca MIDI de estilo — Cargar y entrenar modelos opcionales",
        "style_caption": (
            "Cargá MIDIs libremente → Entrená una vez. Los generadores usan modelos entrenados "
            "si existen; si no, MidiGPT (prior de piano) / heurísticas."
        ),
        "style_upload": "Subir MIDIs de estilo",
        "add_uploads": "Agregar archivos al pack",
        "demos": "Demos clásicos",
        "add_demos": "Agregar demos seleccionados",
        "add_all_demos": "Agregar todos los demos",
        "train": "Entrenar modelos con el pack",
        "clear_pack": "Vaciar pack",
        "not_trained": "Sin entrenar — se usa MidiGPT de respaldo",
        "trained": "Entrenado con {n} pista(s)",
        "melody_title": "Secuencia numérica → Solo / Melodía",
        "melody_caption": "Pegá dígitos (Pi, Fibonacci, fechas) • Generá Solo • O subí un MIDI de solo",
        "digits": "Cadena de dígitos",
        "generate_solo": "Generar melodía Solo desde números",
        "pattern_title": "Patrón → Base — Bajo ordenado desde un patrón de dígitos",
        "pattern_caption": (
            "Los dígitos son grados/offsets, no teclas crudas 1–5. "
            "Ejemplo Pi `31415` → bajo con esos tonos relativos en orden."
        ),
        "generate_bass": "Generar bajo de patrón",
        "fill_solo_title": "Llenar Base desde Solo — Patrón armonizado bajo el Solo",
        "studio_title": "Estudio de pistas",
        "studio_caption": "Agregar pistas • Roles (Solo/Base/Adorn) • AI fills • Editar notas • FX",
        "role": "Rol",
        "role_help": "Lo usan Fill Base / AI. No depende del nombre visible.",
        "play": "Reproducir",
        "prepare_wav": "Preparar WAV",
        "prepare_midi": "Preparar MIDI",
        "add_track": "Agregar pista vacía",
        "ai_fill": "AI Fill (heurísticas V1 + MidiGPT)",
        "loop": "Loop",
        "loop_help": "Repite el patrón hasta que termina la canción (fin = última pista sin loop).",
        "loop_beats": "Ciclo del patrón (beats)",
        "loop_beats_help": "0 = usar las notas escritas como ciclo. Se repite hasta el final de la canción.",
        "no_tracks": "Todavía no hay pistas. Generá un Number Melody o agregá una pista vacía.",
    },
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    table = STRINGS.get(lang, STRINGS["en"])
    text = table.get(key) or STRINGS["en"].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
