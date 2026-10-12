"""Audio muy simple con pygame.mixer (solo el mezclador, sin abrir ventana).

Los sonidos se buscan en recursos/sonidos/ (.wav, .ogg o .mp3).
Si pygame no esta instalado o no hay salida de audio, el motor sigue
funcionando y solo avisa una vez.
"""
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")   # sin el saludo de pygame

CARPETA_SONIDOS = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "recursos", "sonidos")
EXTENSIONES = (".wav", ".ogg", ".mp3")

_listo = None      # None = aun no se intento, True/False = resultado
_cache = {}        # ruta -> pygame.mixer.Sound


def _iniciar():
    global _listo
    if _listo is None:
        try:
            import pygame
            pygame.mixer.init()
            _listo = True
        except Exception as error:
            print("Aviso: audio no disponible (%s). Instala pygame: pip install pygame" % error)
            _listo = False
    return _listo


def listar_sonidos():
    """Nombres de los archivos de sonido disponibles, en orden."""
    if not os.path.isdir(CARPETA_SONIDOS):
        return []
    return sorted(n for n in os.listdir(CARPETA_SONIDOS) if n.lower().endswith(EXTENSIONES))


def reproducir(archivo, volumen=1.0, repetir=False):
    """Reproduce un sonido y devuelve su canal (o None si no se pudo)."""
    if not archivo or not _iniciar():
        return None
    ruta = os.path.join(CARPETA_SONIDOS, archivo)
    try:
        if ruta not in _cache:
            import pygame
            _cache[ruta] = pygame.mixer.Sound(ruta)
        canal = _cache[ruta].play(loops=-1 if repetir else 0)
    except Exception as error:
        print("Aviso: no se pudo reproducir '%s': %s" % (archivo, error))
        return None
    if canal is not None:
        canal.set_volume(max(0.0, min(1.0, volumen)))
    return canal


def detener(canal):
    if canal is not None:
        canal.stop()


def sonando(canal):
    return bool(canal is not None and canal.get_busy())


def ajustar_volumen(canal, volumen):
    """Cambia el volumen de un canal que esta sonando."""
    if sonando(canal):
        canal.set_volume(max(0.0, min(1.0, volumen)))
