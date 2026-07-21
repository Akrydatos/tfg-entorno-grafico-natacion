# tfg-entorno-grafico-natacion
# TFG - Entorno gráfico para natación

Este proyecto permite analizar un vídeo de natación mediante dos herramientas principales:

- `visualizador_pose.py`, para detectar el instante de contacto del nadador con el agua.
- `interpretacio.py`, para revisar el vídeo fotograma a fotograma.

## Instrucciones de uso

### 1. Ejecutar el análisis inicial
Primero, abre la terminal en la carpeta del proyecto y ejecuta:

```bash
python visualizador_pose.py
```

Al iniciar, se abrirá una ventana con el vídeo en pausa. En esa ventana deberás marcar la línea de referencia del agua con los puntos que consideres necesarios para aproximarte lo máximo posible a la superficie del agua o al punto donde se producirá el contacto del nadador con ella.

Cuando la línea esté correctamente definida, pulsa `Enter` para continuar.

A continuación, el vídeo se reproducirá automáticamente y, en la terminal, se mostrará el frame de contacto, el ángulo y la distancia calculada.

### 2. Revisar el vídeo frame a frame
Después, ejecuta:

```bash
python interpretacio.py
```

Este segundo archivo permite recorrer el vídeo fotograma a fotograma.

- Pulsa `D` para avanzar un frame.
- Pulsa `A` para retroceder un frame.

### 3. Cerrar las ventanas
Para cerrar correctamente las dos ventanas de visualización, pulsa `Q`.

**Importante:** para finalizar la visualización de forma correcta, es necesario pulsar `Q` en las ventanas del programa.

## Requisitos
Antes de ejecutar el proyecto, asegúrate de tener instalado el entorno virtual y las dependencias necesarias.

## Estructura general
- `visualizador_pose.py`: análisis inicial del vídeo y cálculo del frame de contacto.
- `interpretacio.py`: visualización y navegación frame a frame.
- `README.md`: documentación del proyecto.

## Observaciones
El proyecto está orientado al análisis visual y a la interpretación del gesto técnico en natación, facilitando la revisión del vídeo de manera precisa y ordenada.