"""Limitador de fotogramas (LIMITE FPS de la configuracion global).

Se llama una vez al final de cada cuadro. Si el cuadro termino antes de
tiempo, espera lo que falta: primero con time.sleep (no gasta CPU) y los
ultimos instantes con un bucle corto, porque sleep no es muy preciso.
"""
import time


class LimitadorFPS:
    def __init__(self):
        self._inicio = time.perf_counter()

    def esperar(self, limite):
        """limite = fotogramas por segundo; 0 o menos = sin limite."""
        if limite and limite > 0:
            objetivo = 1.0 / limite
            while True:
                restante = objetivo - (time.perf_counter() - self._inicio)
                if restante <= 0:
                    break
                if restante > 0.002:
                    time.sleep(restante - 0.001)
        self._inicio = time.perf_counter()
