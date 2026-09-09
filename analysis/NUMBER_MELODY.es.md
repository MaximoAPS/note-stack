# Number Melody — Dígitos a Melodía con Duraciones Aprendidas

## Visión del Producto

**Number Melody** transforma secuencias numéricas (como dígitos de Pi, Fibonacci, fechas, o cualquier cadena numérica) en melodías expresivas con ritmo inteligente. Esta funcionalidad combina:
- **Mapeo determinístico de tono** (dígitos → teclas de piano vía escala/modo)
- **Modelo estadístico de duración** (aprendido de MIDIs de estilo)
- **Integración con adorn existente** (melodía se convierte en pista Solo para jump_adorn)

### Historia de Usuario Ejemplo

1. Usuario pega dígitos de Pi: `314159265358979323846...`
2. Configura afinación: Do mayor, tónica=48 (Do central), rango 2 octavas
3. Carga MIDI(s) de estilo: Joplin "The Entertainer", Albéniz "Asturias"
4. Sistema aprende patrones de duración de saltos (transiciones de intervalo) en estilos
5. Salida: Pista Solo con duraciones musicalmente sensibles
6. Usuario adorna melodía con generadores de patrones existentes

---

## Diseño Técnico

### 1. Mapeo de Tono: Dígitos → Teclas

**Modos soportados (Fase 1)**:
- **Mayor**: 0→1→2→3→4→5→6→7→8→9 mapea a Do Re Mi Fa Sol La Si Do Re Mi
- **Menor Natural**: La Si Do Re Mi Fa Sol La Si Do
- **Pentatónica Mayor**: Do Re Mi Sol La Do Re Mi Sol La
- **Pentatónica Menor**: La Do Re Mi Sol La Do Re Mi Sol
- **Cromática**: Todos los 12 semitonos (0→tónica, 9→tónica+9)

**Envolvente de octava**:
```python
scale_degrees = mode_intervals[digit]  # e.g. [0,2,4,5,7,9,11] para mayor
pitch_class = scale_degrees[digit % len(scale_degrees)]
octave_offset = (digit // len(scale_degrees)) % octave_range
key = tonic + pitch_class + octave_offset * 12
```

#### Modo de Registro jump_predict (Fase 2.0)

**Problema**: El algoritmo de mapeo básico a veces limita el rango de octavas porque la octava se determina mecánicamente. Por ejemplo, con módulo=12, todos los valores 0-11 mapean a una octava, 12-23 a otra, etc. Esto puede evitar que la melodía use el rango completo [min_key, max_key] de manera musicalmente natural.

**Solución**: El modo de registro `jump_predict` usa **desambiguación de octava vía probabilidad de salto**.

**Cómo funciona**:
1. **Dígitos → Clases de Tono**: Igual que modo básico (pair_mod % 12 → PC 0-11)
2. **Encontrar Candidatos**: Para cada clase de tono objetivo, encontrar TODAS las teclas en [min_key, max_key] con esa PC
3. **Elegir Mejor Salto**: Usar histograma de saltos aprendido de MIDIs de estilo para elegir el salto con mayor probabilidad
4. **Modelo de Duración**: Sin cambios, todavía aprendido de MIDIs de estilo

**Ejemplo — PC 3 a PC 7**:
```
Tecla anterior: 40 (Mi)
Clase de tono objetivo: 7 (Sol)
Candidatos en [28, 64]: 31 (Sol, salto=-9), 43 (Sol, salto=+3), 55 (Sol, salto=+15)

Si los MIDIs de estilo prefieren intervalos pequeños:
  → Elige 43 (salto=+3)

Si los MIDIs de estilo prefieren saltos descendentes:
  → Elige 31 (salto=-9)

Si los MIDIs de estilo prefieren intervalos ascendentes grandes:
  → Elige 55 (salto=+15)
```

**Cuándo usar**:
- Entrenamiento multi-estilo con MIDIs clásicos diversos (Chopin, Liszt, Scarlatti)
- Quieres que la melodía abarque múltiples octavas basadas en el movimiento melódico natural del estilo
- Trabajando con rango amplio [min_key, max_key] (ej. 28-64, abarcando 3 octavas)

**Uso CLI**:
```bash
python number_melody.py \
  --digits 314159265358979323846 \
  --tonic 40 \
  --chunk pair_mod \
  --modulus 12 \
  --register jump_predict \
  --min-key 28 \
  --max-key 64 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --style demos/scarlatti-sonata.mid \
  --out pi_jump_predict.mid \
  --bpm 96
```

**UI de Studio**:
1. Selecciona "Register / Registro": **jump_predict**
2. Establece Min Key: **28** (Mi1, inicio rango bajo)
3. Establece Max Key: **64** (Mi4, agudo cómodo)
4. Selecciona múltiples MIDIs de estilo para estadísticas de salto ricas
5. Generar — la melodía abarcará múltiples octavas basadas en preferencias de salto aprendidas

**Detalles Técnicos**:
- Modelo de salto: `Dict[int, int]` mapea salto con signo (semitonos) a contador
- Limitado a ±24 semitonos (±2 octavas) para realismo melódico
- Desempate: Prefiere saltos absolutos más pequeños para conteos iguales (más melódico)
- Primera nota: Siempre usa tónica

---

### 2. Modelo de Duración: Histogramas Condicionados por Salto

**Problema**: Secuencia de notas sin ritmo. Necesitamos predecir duración para cada nota.

**Enfoque (Fase 1 — Modelo Estadístico Práctico)**:

Para cada par de notas consecutivas en la melodía de dígitos:
1. Calcular **salto** (intervalo): `Δkey = key[i] - key[i-1]`
2. Consultar P(duración | salto) de MIDIs de estilo
3. Cuantizar duración a grid musical (0.25, 0.5, 1.0, 2.0 tiempos)

**Entrenamiento**:
- Cargar MIDI(s) de estilo como pistas `mashup_source`
- Para cada par de notas `(n_prev, n_curr)` en estilo:
  - `salto = n_curr.key - n_prev.key`
  - `duracion = n_curr.duration_beats`
  - Registrar `(salto, duracion)` en histograma
- Construir distribución condicional: `P(duration_bin | salto)`
- Opcional: suavizar con contexto (últimos k saltos)

**Predicción**:
- Para cada nota en melodía de dígitos, dada nota previa:
  - `salto = current_key - prev_key`
  - Muestrear duración de `P(duracion | salto)` (o usar moda/mediana)
  - Limitar duración a [0.25, 4.0] tiempos
  - Asignar a nota

**Fallback**:
- Si salto no visto en estilo, usar salto más cercano o moda de duración global (0.5 tiempos)

---

### 3. Integración con Adorn Existente (Futuro)

Una vez generada la pista Number Melody, usuario puede:
- Marcarla como pista Solo en Editor
- Marcar MIDIs de estilo como `mashup_source`
- Ejecutar `jump_adorn` (cuando esté implementado) para añadir bajo/acordes/plucks alrededor de la melodía

Fase 1 genera la pista de melodía lista para edición manual o generadores de patrones existentes.

---

## Implementación Fase 1

**Módulo**: `number_melody.py`

### Funciones

```python
def parse_digit_string(s: str) -> List[int]:
    """Extraer dígitos 0-9 de cadena, ignorar separadores."""
    return [int(c) for c in s if c.isdigit()]

def map_digits_to_keys(
    digits: List[int],
    tonic: int,
    mode: Literal["major", "minor", "pentatonic_major", "pentatonic_minor", "chromatic"],
    octave_range: int = 2
) -> List[int]:
    """Mapear dígitos a teclas de piano usando escala/modo."""
    # Retorna lista de teclas de piano (1-88)
    pass

def build_duration_model(
    style_tracks: List[Track]
) -> Dict[int, List[float]]:
    """
    Construir P(duración | salto) de pistas de estilo.
    
    Returns:
        jump_durations: Dict[salto_semitonos] -> List[duraciones en tiempos]
    """
    # Para cada par de notas en pistas de estilo, registrar (salto, duración)
    pass

def predict_durations(
    keys: List[int],
    duration_model: Dict[int, List[float]],
    default_duration: float = 0.5
) -> List[float]:
    """
    Predecir duración para cada nota dado salto de tecla previo.
    
    Args:
        keys: Teclas de piano para melodía
        duration_model: Salto -> histograma de duraciones
        default_duration: Fallback si salto no en modelo
    
    Returns:
        Lista de duraciones (en tiempos)
    """
    # Para cada tecla, calcular salto desde previa, muestrear duración
    pass

def generate_number_melody(
    digit_string: str,
    tonic: int,
    mode: str,
    style_tracks: List[Track],
    bpm: float = 120.0,
    octave_range: int = 2,
    duration_strategy: Literal["mode", "median", "random"] = "mode"
) -> Track:
    """
    Generar pista de melodía de cadena de dígitos.
    
    Args:
        digit_string: Cadena con dígitos (e.g. "314159265358979")
        tonic: Tecla raíz (e.g. 48 para Do central)
        mode: Modo de escala (major, minor, pentatonic_major, etc.)
        style_tracks: Pistas para aprender duraciones
        bpm: Tempo
        octave_range: Cuántas octavas abarcar
        duration_strategy: Cómo elegir duración del histograma (mode/median/random)
    
    Returns:
        Pista de melodía generada
    """
    # 1. Parsear dígitos
    # 2. Mapear a teclas
    # 3. Construir modelo de duración de pistas de estilo
    # 4. Predecir duraciones
    # 5. Crear objetos Note en tiempos de inicio acumulativos
    # 6. Retornar Track con nombre "Number Melody (Pi)" etc.
    pass
```

---

## Prueba CLI

**Modo básico**:
```bash
python number_melody.py \
  --digits 314159265358979323846 \
  --tonic 48 \
  --mode major \
  --chunk pair_mod \
  --modulus 12 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --out /tmp/pi_melody.mid \
  --bpm 96
```

**Modo jump_predict (desambiguación de octava)**:
```bash
python number_melody.py \
  --digits 314159265358979323846 \
  --tonic 40 \
  --chunk pair_mod \
  --modulus 12 \
  --register jump_predict \
  --min-key 28 \
  --max-key 64 \
  --style demos/chopin-etude.mid \
  --style demos/liszt-preludio.mid \
  --style demos/scarlatti-sonata.mid \
  --out /tmp/pi_jump_predict.mid \
  --bpm 96
```

**Esperado**: Archivos MIDI con melodías con duraciones variadas aprendidas de patrones de estilo. El modo jump_predict debe producir melodías que abarcan múltiples octavas dentro de [min_key, max_key] basadas en el movimiento melódico natural del estilo.

---

## Integración UI (Streamlit)

Añadir panel en `app.py`:

**Sección "Number Melody"**:
- Área de texto: Pegar cadena de dígitos
- **Selector de modo chunk**: pair_mod (por defecto) o single
- **Entrada módulo**: 12 (cromático), 7 (diatónico), 5 (pentatónico)
- **Selector modo registro**: basic (original) o jump_predict (desambiguación octava)
- Entrada numérica: Tónica (1-88, default 40)
- Dropdown: Modo (major, minor, pentatonic_major, pentatonic_minor, chromatic)
- **Entrada numérica: Min key (default 28 para inicio rango bajo)**
- **Entrada numérica: Max key (default 64 para registro cómodo)**
- Entrada numérica: Rango de octavas (1-4, default 2, usado en modo básico)
- **Multi-selección: MIDIs de estilo demo (selecciona múltiples para patrones más ricos)**
- Radio: Estrategia de duración (mode, median, random)
- **Entrada numérica: BPM (default 96 para tempo más calmado)**
- Botón: "Generate Melody"

**Al Generar**:
- Cargar MIDI(s) de estilo como lista de Track
- Llamar `generate_number_melody()`
- Añadir pista generada a sesión
- Mostrar éxito + preview de timeline
- Botón: "Adorn this melody" (si editor_session + pattern_generators disponible)

---

## Roadmap Fase 2+ (Solo Documentar)

### Modelo de Duración Deep Learning

**Arquitectura**:
- **Entrada**: Embeddings de secuencia de saltos (últimos k saltos)
- **CNN**: Patches locales (contexto ±2 tiempos) para patrones de ritmo
- **Transformer (estilo GPT-2)**: Modelado de secuencia para dependencias largas
- **Salida**: Distribución de duración (categórica sobre {0.25, 0.5, 1.0, 2.0, 4.0})

**Entrenamiento**:
- Recopilar secuencias salto→duración de MAESTRO + paquetes de estilo de usuario
- Entrenar en millones de transiciones de notas
- Fine-tune por paquete de estilo (Romántico vs Jazz vs Pop)

### Chunking Multi-Dígito

- Codificaciones base-N: Tratar pares/tríos de dígitos como alfabeto más grande
- Espacio de tono más rico: 100 símbolos → mapeos más expresivos

### Plantillas de Ritmo

- Aprender patrones de ritmo a nivel de compás de estilo (no solo nota a nota)
- Aplicar plantilla de ritmo a melodía de dígitos (cuantizar a estructura de compás)

### Integración con Jump Adorn

- Una vez implementado `jump_adorn` (mencionado en editor-ui-phase1):
  - Number Melody genera pista Solo
  - Usuario marca MIDIs de estilo como `mashup_source`
  - `jump_adorn` genera bajo/acordes/decoración alrededor de Solo

---

## Criterios de Éxito

✅ **Fase 1 Usable**:
- Usuario puede pegar dígitos de Pi, configurar afinación, elegir MIDI de estilo
- Sistema genera pista de melodía con duraciones no uniformes aprendidas de estilo
- Prueba CLI pasa
- Panel UI funciona en Streamlit
- Melodía se carga en sesión como pista reproducible
- Documentación completa (EN + ES)
- PR abierto

---

## Referencias

- **IntervalEmbedder** (futuro): Embeddings de tokens de salto para modelo profundo
- **jump_adorn** (futuro): Adornar melodía con bajo/acordes condicionados en patrones de salto
- **Editor Session** (cursor/editor-ui-phase1-1259): Roles de pistas, flujo de mashup_source
- **MAESTRO Dataset**: https://magenta.tensorflow.org/datasets/maestro

---

**Autor**: Cloud Agent + Maximo  
**Fecha**: Sep 2026  
**Versión**: 1.0 (Fase 1 Modelo Estadístico de Duración)
