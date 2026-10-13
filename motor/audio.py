"""
Audio muy simple con pygame.mixer (solo el mezclador, sin abrir ventana).

Los sonidos se buscan en recursos/sonidos/ (.wav, .ogg o .mp3).
Si pygame no esta instalado o no hay salida de audio, el motor sigue
funcionando y solo avisa una vez.
"""

import os

# Oculta el mensaje de bienvenida de pygame
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# Carpeta donde se almacenan los archivos de audio
CARPETA_SONIDOS = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "recursos",
    "sonidos",
)

# Extensiones de audio soportadas
EXTENSIONES = (
    ".wav",
    ".ogg",
    ".mp3",
)

# Estado de inicializacion del sistema de audio
_listo = None
# Cache de sonidos ya cargados en memoria
_cache = {}

# Inicializa pygame.mixer una sola vez
def _iniciar():
    global _listo
    # Evita inicializaciones repetidas
    if _listo is None:
        try:
            # Importa pygame solo cuando es necesario
            import pygame
            # Inicializa el mezclador de audio
            pygame.mixer.init()
            # Marca el sistema como disponible
            _listo = True

        # Permite continuar sin audio si ocurre algun error
        except Exception as error:
            print(
                "Aviso: audio no disponible (%s). "
                "Instala pygame: pip install pygame"
                % error
            )
            # Marca el sistema como no disponible
            _listo = False
    return _listo


# Devuelve la lista de sonidos disponibles
def listar_sonidos():
    # Devuelve una lista vacia si la carpeta no existe
    if not os.path.isdir(CARPETA_SONIDOS):
        return []

    # Obtiene y ordena los archivos compatibles
    return sorted(
        n
        for n in os.listdir(CARPETA_SONIDOS)
        if n.lower().endswith(EXTENSIONES)
    )


# Reproduce un archivo de sonido
def reproducir(
    archivo,
    volumen=1.0,
    repetir=False,
):
    #Reproduce un sonido y devuelve su canal (o None si no se pudo).
    # Cancela la reproduccion si no hay archivo o audio disponible
    if not archivo or not _iniciar():
        return None

    # Construye la ruta completa del archivo
    ruta = os.path.join(
        CARPETA_SONIDOS,
        archivo,
    )

    try:
        # Carga el sonido solo la primera vez
        if ruta not in _cache:
            import pygame
            _cache[ruta] = pygame.mixer.Sound(ruta)

        # Inicia la reproduccion del sonido
        canal = _cache[ruta].play(
            loops=-1 if repetir else 0
        )

    # Informa errores de carga o reproduccion
    except Exception as error:
        print(
            "Aviso: no se pudo reproducir '%s': %s"
            % (archivo, error)
        )
        return None

    # Ajusta el volumen inicial si existe un canal valido
    if canal is not None:
        canal.set_volume(
            max(
                0.0,
                min(1.0, volumen),
            )
        )
    return canal


# Detiene la reproduccion de un canal
def detener(canal):
    if canal is not None:
        canal.stop()

# Indica si un canal continua reproduciendo audio
def sonando(canal):
    return bool(
        canal is not None
        and
        canal.get_busy()
    )

# Ajusta el volumen de un canal activo
def ajustar_volumen(
    canal,
    volumen,
):
    #Cambia el volumen de un canal que esta sonando.
    # Solo modifica canales actualmente activos
    if sonando(canal):
        canal.set_volume(
            max(
                0.0,
                min(1.0, volumen),
            )
        )
