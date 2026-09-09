# Interfaz de Usuario del Estudio (Studio UI)

## Resumen

La **Studio UI** proporciona un flujo de trabajo de extremo a extremo para crear composiciones de piano expresivas con el generador Number Melody, herramientas AI de pistas, y edición interactiva de notas.

## Flujo de Trabajo Recomendado

### 1. Generar una Melodía Numérica

**Number Melody** transforma secuencias de dígitos (Pi, Fibonacci, fechas) en melodías con duraciones aprendidas de MIDIs de estilo.

**Pasos:**
1. Pega una secuencia de dígitos (ej. Pi: `314159265358979...`)
2. Elige **Chunk Mode**: `pair_mod` (recomendado) para variación rica
3. Establece **Modulus**: 12 (cromático), 7 (diatónico), 5 (pentatónico)
4. Configura **Tonic** (tónica): 40 = E, 48 = C medio
5. Selecciona **múltiples MIDIs de estilo** (3+ para patrones más ricos)
6. Haz clic en **"🎵 Generar Melodía Numérica"**

**Resultado:** Una pista "Solo" se añade a la canción con la melodía generada.

### 2. Añadir Pistas AI

En el **Tracks Studio**, cada pista tiene botones de **AI Fill Track** para generar contenido basado en otras pistas:

- **Bass Line** (teclas 1-28): Extrae notas graves de otras pistas
- **Chord Base** (teclas 29-52): Extrae agrupaciones de notas / acordes
- **Adorn Pluck** (teclas 45-72): Crea patrones decorativos dispersos
- **Harmony Line** (teclas 45-72): Armoniza la melodía con transposición de intervalos

**Ejemplo:**
1. Abre la pista Solo generada
2. Haz clic en "Bass Line" → Genera una pista Base de bajo
3. Haz clic en "Chord Base" → Genera una pista Base de acordes
4. Haz clic en "Adorn Pluck" → Genera ornamentación

### 3. Editar Notas

Cada pista ahora tiene un **Editor de Badges de Clusters** que muestra las notas como badges horizontales:

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

### 4. Configurar FX por Pista

Cada pista tiene controles de efectos:

- **Intensity** (0.1-5.0): Multiplicador de intensidad armónica (1.0 = melodía, 2.0 = bajo)
- **Delay**: Activa eco de 30/160 segundos para sonido más rico
- **Hold** (0.1-5.0s): Duración de sustain (0.5 = corto, 2.0 = largo)
- **Mute**: Silencia la pista temporalmente

### 5. Reproducir y Exportar

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
2. **Selección de estilo múltiple**: Usa 3+ MIDIs de demostración para patrones de duración más ricos
3. **pair_mod es mejor**: El modo `pair_mod` con módulo 12 da la mayor variación de tono
4. **Roles de pista**: Mantén 1-2 pistas Solo, 2-3 pistas Base, 1-2 pistas Adorn para mezcla equilibrada
5. **Edita después de generar**: Los generadores AI son heurísticos V1; ajusta notas manualmente para perfeccionar
6. **Exporta temprano y a menudo**: Descarga WAV/MIDI después de cada iteración para comparar versiones

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
