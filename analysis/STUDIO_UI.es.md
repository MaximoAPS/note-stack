# Interfaz de Usuario del Estudio (Studio UI)

## Resumen

La **Studio UI** proporciona un flujo de trabajo de extremo a extremo para crear composiciones de piano expresivas con el generador Number Melody, herramientas AI de pistas, y edición interactiva de notas.

## Flujo de Trabajo Recomendado

### 0. Configurar Biblioteca de Estilo (Nuevo)

**Style / Training MIDI Library** es una sección global en la parte superior de Studio que gestiona MIDIs de entrenamiento para toda la sesión.

**Pasos:**
1. **Selecciona demos**: Elige uno o más MIDIs de demostración de la lista
2. **Haz clic en "➕ Add Selected Demos"**: Añádelos al paquete de estilo
3. **O sube MIDIs**: Usa el cargador "Upload MIDI" para añadir tus propios archivos
4. **Ver cargados**: La lista muestra todos los MIDIs de estilo con conteo de pistas
5. **Eliminar entradas**: Haz clic en 🗑️ para eliminar MIDIs individuales, o "🗑️ Clear All" para todos

**Uso:**
- Number Melody, Pattern → Base, AI fills, y jump_predict **usan automáticamente** estos MIDIs de estilo
- Si está vacío, las herramientas usan MIDI-GPT, heurísticas, o valores predeterminados neutrales
- Puedes sobrescribir con selección local en opciones avanzadas

**Beneficio:** Carga MIDIs de estilo **una vez** en la parte superior; todos los generadores los usan.

### 1. Generar una Melodía Numérica (Solo)

**Number Sequence → Solo / Melody** transforma secuencias de dígitos (Pi, Fibonacci, fechas) en melodías con duraciones aprendidas de MIDIs de estilo.

**Pasos:**
1. Pega una secuencia de dígitos (ej. Pi: `314159265358979...`)
2. Configura **Tonic** (tónica): 40 = E, 48 = C medio
3. Configura **BPM**: 96 (calmado), 120 (moderado), 160 (rápido)
4. Elige **Mode** (modo): major, minor, pentatonic, chromatic
5. **O sube un Solo MIDI**: Usa el cargador "Or upload Solo MIDI"
6. Haz clic en **"🎵 Generate Solo Melody from Numbers"**

**Opciones avanzadas** (en expansor "⚙️ Advanced Options"):
- **Chunk Mode**: `pair_mod` (recomendado) o `single`
- **Modulus**: 12 (cromático), 7 (diatónico), 5 (pentatónico)
- **Register**: `basic` o `jump_predict` (desambiguación de octava)
- **Key range**: min/max keys, octave span
- **Override style pack**: Selecciona MIDIs específicos en lugar del paquete global

**Resultado:** Una pista "🎵 Solo" se añade a la canción con la melodía generada.

### 2. Generar Bajo de Patrón (Pattern → Base)

**Pattern → Base** genera líneas de bajo que siguen una secuencia ordenada específica. A diferencia de "AI Fill Bass" (que extrae notas graves arbitrarias de donantes), Pattern → Base restringe el bajo para seguir tu secuencia de dígitos en orden.

**Pasos:**
1. Introduce el patrón: `3-1-4-1-5` (dígitos de Pi)
2. Elige el modo:
   - **Offset**: Cada dígito + offset (ej. 3+10=13, 1+10=11, 4+10=14...)
   - **Tonic+Scale**: Mapea dígitos a grados de escala en octava baja (ej. tónica E0=16, cromática)
3. Establece rango de bajo: min=28 (E1), max=42 (F#2)
4. Usa el paquete de estilo global (o sobrescribe en opciones avanzadas)
5. Haz clic en **"🎸 Generate Pattern Bass"**

**Resultado:** Una pista "🎸 Base" se añade con el patrón `13-11-14-11-15` y ritmos aprendidos.

**Loop para pistas Base:** Después de generar, puedes activar **🔁 Loop** en la pista para repetir el patrón a través de la línea de tiempo de la canción (ver sección 5).

**Casos de uso:**
- Bajo de Pi: `3-1-4-1-5-9-2-6-5-3-5-8-9-7-9`
- Bajo de Fibonacci: `1-1-2-3-5-8`
- Secuencias personalizadas: `5-3-1-2-4-6-5-3`

La IA asigna duraciones basadas en los patrones de salto en tus MIDIs de estilo, creando una línea de bajo musicalmente fluida que sigue tu secuencia de tonos exacta.

**Nota:** Los dígitos son grados de patrón/offsets, **no** teclas crudas de piano 1-5. Ejemplo: Pi `31415` con offset 10 → bajo con teclas 13, 11, 14, 11, 15.

### 3. Añadir Pistas AI

En el **Tracks Studio**, cada pista tiene botones de **AI Fill Track** para generar contenido basado en otras pistas:

- **Bass Line** (teclas 1-28): Extrae notas graves de otras pistas (arbitrario, no ordenado por patrón)
- **Chord Base** (teclas 29-52): Extrae agrupaciones de notas / acordes
- **Adorn Pluck** (teclas 45-72): Crea patrones decorativos dispersos
- **Harmony Line** (teclas 45-72): Armoniza la melodía con transposición de intervalos

**Ejemplo:**
1. Abre la pista Solo generada
2. Haz clic en "Bass Line" → Genera una pista Base de bajo (extrae notas graves arbitrarias)
3. **O** usa "Pattern → Base" arriba para bajo ordenado por secuencia de dígitos
4. Haz clic en "Chord Base" → Genera una pista Base de acordes
5. Haz clic en "Adorn Pluck" → Genera ornamentación

**Nota:** Para líneas de bajo que siguen una secuencia de dígitos específica en orden (como Pi `3-1-4-1-5`), usa **Pattern → Base** en lugar de AI Fill Bass.

### 4. Loop de Pista (Nuevo)

Para pistas Base (y otras), ahora puedes activar **🔁 Loop** para repetir el patrón de la pista a través de la línea de tiempo de la canción.

**Controles:**
- **🔁 Loop**: Checkbox para activar el loop
- **Loop beats**: Longitud del loop en beats (0 = hasta el final de la canción)

**Ejemplo:**
1. Genera una pista Base con Pattern → Base (ej. 4 beats de patrón)
2. Activa **🔁 Loop** en la pista
3. Establece **Loop beats** a 0 (hasta el final) o un valor específico (ej. 16 beats)
4. Al reproducir/exportar, la pista se repite automáticamente

**Uso típico:** Líneas de bajo repetitivas, patrones de acordes, ostinatos.

### 5. Editar Notas

Cada pista ahora tiene un **Editor de Badges de Clusters** que muestra las notas como badges horizontales:

#### Insertar Silencios / Reposos (Nuevo)

Ahora puedes insertar silencios (reposos) con duración específica:

**Controles:**
- **Rest duration**: Selecciona duración del silencio (1/4, 1/2, 1, 2... beats)
- **➕ Insert Rest at End**: Marca el final de la pista para pegar más clusters después de un silencio
- **➕ Insert Rest Here**: Inserta silencio en una posición específica (desplaza notas posteriores)

**Ejemplo:**
1. Tienes notas en beats 0-4
2. Inserta reposo de 2 beats en beat 2
3. Las notas después de beat 2 se desplazan a beat 4+

**💡 Nota:** Los silencios son **gaps** (huecos) — ausencia de notas = silencio. No hay notas "mudas" falsas.

#### Editor de Badges de Clusters

El editor de badges organiza las notas en **clusters** (grupos de teclas simultáneas) con chips de duración:

- Cada **badge** = un cluster: teclas simultáneas + duración (1/4, 1/2, 1, 2... beats)
- **Editar teclas**: Cambia los números directamente en el badge (separadas por comas)
- **Cambiar duración**: Usa el desplegable para seleccionar fracciones comunes
- **Insertar cluster**: Haz clic en ➕ para insertar un nuevo cluster antes del actual
- **Eliminar cluster**: Haz clic en 🗑️ para eliminar
- **Aplicar cambios**: Haz clic en "✅ Apply Changes" para actualizar las notas

**Pegar Cadenas de Clusters:**

Puedes pegar secuencias de clusters directamente usando esta sintaxis:

**Sintaxis:**
- Guión (`-`) separa clusters secuenciales
- Coma (`,`) separa teclas dentro de un cluster (notas simultáneas)
- Ejemplo: `35-35,36-38-35` crea cuatro clusters:
  1. Tecla 35
  2. Teclas 35 y 36 juntas (acorde)
  3. Tecla 38
  4. Tecla 35
- Duración predeterminada: 1/2 beat (personalizable antes de pegar)

**Pasos para pegar:**
1. Escribe o pega la cadena de clusters (ej. `35-35,36-38-35`)
2. Selecciona la duración predeterminada (1/4, 1/2, 1, 2 beats)
3. Haz clic en "📥 Paste"
4. Los clusters se añaden al final de la pista

**Ejemplo de flujo de trabajo:**
```
35-35,36-38-35
```
Con duración 1/2 genera:
- Beat 0.0: [35]
- Beat 0.5: [35, 36]
- Beat 1.0: [38]
- Beat 1.5: [35]

#### Editor de Tabla Avanzada

La **tabla de datos interactiva** tradicional sigue disponible en un expansor "🔧 Advanced Table Editor":

- **Añadir filas**: Haz clic en la última fila vacía
- **Editar valores**: Cambia Key (tecla), Start Beat (inicio), Duration (duración), Velocity (velocidad)
- **Eliminar filas**: Selecciona y elimina
- **Eliminar rango de beats**: Introduce "4-8" y haz clic en "🗑️ Delete Range"
- **Aplicar cambios**: Haz clic en "✅ Apply Table"

Usa el editor de badges para flujo rápido y el editor de tabla para control preciso de timing y velocity.

### 6. Calibrar FX por Pista (Mejorado)

Cada pista ahora tiene una sección **🎛️ FX Calibration** con controles claros y valores predeterminados de piano:

**Controles:**
- **Intensity** (0.1-5.0): Multiplicador de intensidad armónica
  - 1.0 = melodía (predeterminado piano)
  - 2.0 = bajo/rico
- **Delay**: Activa eco de 30/160 segundos para sonido más espacioso
  - On = predeterminado piano para melodías
  - Off = para bajos/ritmo directo
- **Hold** (0.1-5.0s): Duración de sustain de nota
  - 0.8s = predeterminado piano (equilibrado)
  - 0.5s = corto (staccato)
  - 2.0s = largo (legato)
- **🔄 Piano Defaults**: Botón para restablecer a valores predeterminados de piano (I=1.0, Hold=0.8s, Delay=On)

**Roles y FX sugeridos:**
- **Solo (Melodía)**: I=1.0, Delay=On, Hold=0.8s (predeterminado piano)
- **Base (Bajo)**: I=2.0, Delay=Off, Hold=2.0s (rico y sostenido)
- **Base (Acordes)**: I=1.5, Delay=Off, Hold=1.5s (medio)
- **Adorn**: I=1.0, Delay=On, Hold=0.5s (ligero)

**Mute**: Silencia la pista temporalmente sin borrar notas

### 7. Reproducir y Exportar

- **▶ Play**: Sintetiza y reproduce la canción completa
- **Download WAV**: Exporta audio estéreo de 16-bit 44.1kHz
- **Download MIDI**: Exporta archivo MIDI con todas las pistas

## Roles de Pista

Las pistas se identifican por prefijos de nombre:

- **🎵 Solo**: Melodías principales (ej. Number Melody generada)
- **🎸 Base**: Bajos y acordes de acompañamiento
- **✨ Adorn**: Ornamentación y armonías
- **🎹 Other**: Pistas genéricas

Los generadores AI asignan automáticamente estos prefijos según el tipo de contenido generado.

## Controles de BPM

El **BPM** (beats por minuto) controla el tempo global:
- **96 BPM** (predeterminado): Tempo calmado
- **120 BPM**: Tempo moderado
- **160 BPM**: Tempo rápido (como Piano Song de Desmos)

Cuando generas Number Melody, el BPM se actualiza automáticamente al valor especificado.

## Herramientas Legacy

Las características avanzadas están colapsadas en **"🗂️ Legacy Tools"**:
- Cargar preset de Piano Song (Desmos)
- Subir archivos MIDI
- Cargar demos de MAESTRO

Estas son útiles para experimentación avanzada pero no son necesarias para el flujo de trabajo básico de Studio.

## Modelo de Síntesis

El motor de síntesis implementa el modelo de timbre de piano del gráfico de Desmos:
- **64 armónicos** por nota
- **Envolvente dependiente de tecla**: Las teclas altas decaen más rápido
- **Micro-desafinación**: ±3.5 centavos por armónico para timbre orgánico
- **Efecto Haas**: Estéreo con retardo de ~15ms para amplitud espacial
- **Filtro paso bajo maestro**: Suavizado ~13 kHz
- **Normalización de picos**: 0.89

## Consejos de Uso

1. **Comienza simple**: Genera una Number Melody y escúchala antes de añadir más pistas
2. **Pattern → Base para secuencias ordenadas**: Si quieres un bajo que siga Pi `3-1-4-1-5` exactamente, usa Pattern → Base, no AI Fill Bass
3. **Selección de estilo múltiple**: Usa 3+ MIDIs de demostración para patrones de duración más ricos
4. **pair_mod es mejor**: El modo `pair_mod` con módulo 12 da la mayor variación de tono
5. **Roles de pista**: Mantén 1-2 pistas Solo, 2-3 pistas Base, 1-2 pistas Adorn para mezcla equilibrada
6. **Edita después de generar**: Los generadores AI son heurísticos V1; ajusta notas manualmente para perfeccionar
7. **Exporta temprano y a menudo**: Descarga WAV/MIDI después de cada iteración para comparar versiones

## Limitaciones Actuales (Fase 1)

- **Generadores AI**: Heurísticos basados en reglas, no modelos de aprendizaje profundo
- **Sin editor de piano-roll visual**: Usa tabla de datos por ahora
- **Sin FX por pista en render estéreo**: Intensidad y Delay funcionan; FX avanzados pendientes
- **Sin importación NBS en UI**: Solo MIDI por ahora

Estas características están planificadas para fases futuras. Ver `EDITOR_UX.md` para la visión completa del producto.

## Solución de Problemas

**"Todas las pistas silenciadas"**: Desmarca "Mute" en al menos una pista  
**"Sin notas generadas"**: Asegúrate de que otras pistas tengan notas antes de generar AI  
**"Melodía demasiado alta"**: Reduce `max_key` a 60 o menos  
**"Duración de nota silenciosa"**: Verifica que Velocity sea 50-127  
**"Error al cargar MIDI"**: Verifica que el archivo sea .mid o .midi válido  

## Más Información

- **Documentación técnica de Number Melody**: `analysis/NUMBER_MELODY.md` (EN), `NUMBER_MELODY.es.md` (ES)
- **Visión del producto Editor UX**: `analysis/EDITOR_UX.md` (EN), `EDITOR_UX.es.md` (ES)
- **README principal**: `README.md` (EN)

---

**¡Disfruta creando música con Note Stack Studio! 🎹✨**
