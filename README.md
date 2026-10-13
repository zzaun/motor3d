# Proyecto motor3d + obj_a_cordenas

Dos proyectos separados:

- **obj_a_cordenas/**: convierte los `.obj` (modelados en Blender) en archivos
  `.txt` de coordenadas locales. Escribe directo en `motor3d/objetos3d/`.
  No necesita librerías externas.
- **motor3d/**: lee esos `.txt` (nunca el `.obj`) y arma una escena de **nodos**
  con cámara, luces y una interfaz al costado izquierdo.

## Instalación

```bash
cd motor3d
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt     # glfw, PyOpenGL y pygame (audio); numpy se usará en la animación
```

## Estructura

```
obj_a_cordenas/                 conversor (solo biblioteca estándar)
├── main.py   config.py
├── objetos3d/                  aquí van los .obj y .mtl
└── conversor/                  lector_obj, procesador, escritor_txt

motor3d/
├── main.py
├── escena.txt                  lo crea el botón GUARDAR
├── objetos3d/                  .txt generados por el conversor
├── recursos/sonidos/           .wav / .ogg / .mp3
├── motor/                      nodos, escena, archivos, entrada, audio, limitador
└── interfaz/                   fuente de píxeles, controles y panel izquierdo
```

El único archivo que se ejecuta es `main.py` (los demás son módulos).

## Flujo de trabajo

1. En Blender exporta cada parte como objeto (File > Export > Wavefront .obj)
   con *Triangulate Faces*, *Write Normals*, *Write Materials* y
   *Objects as OBJ Objects*. Eje: Y arriba (si usas Z arriba, cambia
   `CONVERTIR_Z_ARRIBA` en `obj_a_cordenas/config.py`).
2. Copia los `.obj` y `.mtl` a `obj_a_cordenas/objetos3d/`.
3. `cd obj_a_cordenas && python3 main.py` (o `python3 main.py brazo.obj`).
4. `cd ../motor3d && python3 main.py`.

Se incluyen un `cubo` y un `brazo` (2 partes, con hueso) de ejemplo.

## Árbol de nodos (herencia)

```
node                    id, name
├── nodeGlobal          REJILLA, MODO DE VISION, LIMITE FPS, FONDO, LUZ AMBIENTAL,
│                       MOSTRAR HUESOS, DOS CARAS            (uno solo, id 0)
└── node3D              VISIBLE, EJES, LOCATION, ROTATION, fotogramas_claves
    ├── nodeObjeto3D    geometría y color de caras, COLOR BASICO, ESCALA, HUESO, APUNTA A, PIVOTE
    ├── nodeAudio       ARCHIVO, VOLUMEN, REPETIR, AL INICIAR
    ├── nodeLight       ILUMINACION, COLOR, POWER, SHADOW
    │   ├── nodeLightPoint   RADIUS (m)
    │   │   └── nodeLightSpot  RADIUS + ANGLE + CONCENTRAC.
    │   └── nodeLightSol     (la dirección sale de la ROTATION)
    └── nodeCamera      MODO (orbital/libre), FOV, ORTOGRAFICA, CERCA, LEJOS, ...
```

Cada clase declara sus parámetros en una tabla (`PARAMS` en `motor/nodos.py`).
Esa tabla crea los atributos, dibuja los controles de **NODE CONFIGURACION** y
define lo que se guarda en los `.txt`: para agregar un parámetro nuevo basta
una línea `P(...)` en la clase que corresponda.

Una luz mira hacia su eje -Z local: su ROTATION decide hacia dónde. Como las
luces son `node3D`, también pueden ser hijas de otro nodo.

## Interfaz (columna izquierda, tres bloques siempre visibles)

| Bloque | Color | Contenido |
|---|---|---|
| NODOS | café | lista jerárquica de nodos (nombre + tipo). Al pie: `+ PUNTO`, `+ SOL`, `+ SPOT` y `ELIMINAR NODO` |
| CONFIGURACION GLOBAL | verde | `GUARDAR` y los parámetros del nodeGlobal |
| NODE CONFIGURACION | azul | el nodo seleccionado y SOLO sus parámetros |

Cada bloque tiene su propio scroll (rueda del mouse sobre él). Los botones
`-` / `+` repiten si se mantienen presionados y con Shift avanzan x10.

## Color básico (nodeObjeto3D)

`COLOR BASICO` pinta todo el objeto de un solo color en el modo MATERIAL (en
SOLIDO y ALAMBRE se ignora). Al activarlo aparece una fila de 8 colores
básicos y las filas R, G, B para afinarlo. Si lo apagas vuelve el color de
cada cara.

## Audio (nodeAudio)

Usa `pygame.mixer` (instala `pygame`). Los sonidos van en
`motor3d/recursos/sonidos/` (`.wav`, `.ogg` o `.mp3`; viene un `beep.wav` de
prueba). Se agrega con `+ AUDIO` al pie de NODOS; en NODE CONFIGURACION están
`REPRODUCIR` / `DETENER`, `< ARCHIVO` / `ARCHIVO >` para elegir el sonido, y
VOLUMEN (se oye al instante), REPETIR y AL INICIAR (suena al abrir el motor).
Si pygame no está instalado el motor funciona igual y solo avisa una vez.
Por ahora no es espacial: su LOCATION queda guardada para el sonido 3D.

## Archivos .txt

`objetos3d/<objeto>.txt` (lo genera el conversor):

```
[nodo]                  <- encabezado: información del nodo
tipo = nodeObjeto3D
name = brazo_superior
padre =                 <- nombre del padre (opcional)
location = 2.2 0.5 0
es_hueso = 1
apunta_a = antebrazo    <- el objeto al que apunta pasa a ser su hijo
pivote = 0 -0.5 0
[vertices] / [normales] / [caras] / [uvs]     <- una fila de números por línea
```

El encabezado se puede editar a mano; al volver a convertir el `.obj` se
conservan `padre`, `es_hueso`, `apunta_a` y `pivote`.

`escena.txt` (lo escribe el botón GUARDAR, junto a `main.py`): un bloque
`[nodo]` por cada nodo (global, cámara, luces y objetos) con sus parámetros
actuales. Al arrancar se carga encima de los objetos. La geometría nunca se
toca. Para volver al estado inicial, borra `escena.txt`.

Los nodos se relacionan por **nombre** (`padre = nombre`); los `id` se guardan
pero no se usan como referencia.

## LIMITE FPS

Está en CONFIGURACION GLOBAL (0 = sin límite, por defecto 60). El motor apaga
la sincronía vertical y el límite lo pone `motor/limitador.py`.

## Controles

- `Tab` siguiente nodo, `C` cámara orbital/libre, `1-4` vistas rápidas,
  `Shift+R` reiniciar la pose de los nodos, `Esc` salir.
- Orbital: clic izquierdo orbitar, derecho/central mover, rueda zoom.
- Libre: clic derecho (o izquierdo) mirar, `WASD` mover, `Q/E` bajar/subir.

## Pendiente (próximas fases)

- Seleccionar nodos con clic izquierdo en la escena.
- MODO DE VISION: hoy ALAMBRE y SOLIDO funcionan; MATERIAL muestra el color por
  cara (las texturas con imagen llegan después).
- SHADOW está en la tabla pero todavía no hace nada.
- `fotogramas_claves` existe vacío en node3D: la animación (y el audio sincronizado con ella) vienen después.