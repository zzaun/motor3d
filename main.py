"""motor3d: visor/motor 3D con glfw + OpenGL, basado en nodos.

Lee los .txt de objetos3d/ (generados por obj_a_cordenas), arma la escena de
nodos y la muestra con la interfaz al costado izquierdo:
  NODOS (cafe) / CONFIGURACION GLOBAL (verde) / NODE CONFIGURACION (azul).

Uso:  python3 main.py
"""
import os
import sys

import glfw
from OpenGL.GL import *  # noqa: F401,F403

from motor.escena import Escena
from motor.entrada import Entrada
from motor.limitador import LimitadorFPS
from motor.archivos import cargar_escena
from motor.preparar_objetos3d import preparar_objetos3d

# Interfaz propia de botones (sin dependencias extra)
from interfaz.panel_nodos import PanelNodos
from interfaz.interfaz import ANCHO as ANCHO_PANEL

BASE = os.path.dirname(os.path.abspath(__file__))
CARPETA_OBJETOS = os.path.join(BASE, "objetos3d")
RUTA_ESCENA = os.path.join(BASE, "escena.txt")    # lo escribe el boton GUARDAR
ANCHO_VENTANA, ALTO_VENTANA = 1280, 800


def luces_iniciales(escena):
    """Luces por defecto (solo si todavia no hay un escena.txt guardado)."""
    sol = escena.agregar_luz("nodeLightSol")
    sol.power = 0.9
    punto = escena.agregar_luz("nodeLightPoint")
    punto.color = [1.0, 0.85, 0.6]
    punto.power = 0.7
    punto.radius = 12.0


def crear_escena():
    escena = Escena()
    preparar_objetos3d(CARPETA_OBJETOS, escena)

    if os.path.isfile(RUTA_ESCENA):
        try:
            cargar_escena(RUTA_ESCENA, escena)
            print("Escena cargada de", RUTA_ESCENA)
        except Exception as error:
            print("Aviso: no se pudo leer escena.txt:", error)
    if not escena.luces() and not os.path.isfile(RUTA_ESCENA):
        luces_iniciales(escena)

    # Selecciona el primer objeto de la lista de NODOS
    for nodo, _nivel in escena.recorrer_arbol():
        if nodo.TIPO == "nodeObjeto3D":
            escena.seleccionar(nodo)
            break
    return escena


def main():
    if not glfw.init():
        print("No se pudo iniciar glfw")
        return 1

    ventana = glfw.create_window(ANCHO_VENTANA, ALTO_VENTANA, "motor3d", None, None)
    if not ventana:
        glfw.terminate()
        print("No se pudo crear la ventana")
        return 1
    glfw.make_context_current(ventana)
    # Sin sincronia vertical: el LIMITE FPS de la configuracion global manda
    glfw.swap_interval(0)

    escena = crear_escena()
    escena.configurar_opengl()
    entrada = Entrada(ventana)
    panel = PanelNodos(ventana)
    panel.ruta_escena = RUTA_ESCENA
    limitador = LimitadorFPS()
    estado = {"fps": 0.0}

    # Los nodeAudio con AL INICIAR empiezan a sonar
    for nodo in escena.nodos:
        if nodo.TIPO == "nodeAudio" and nodo.al_iniciar:
            nodo.reproducir()

    previo = glfw.get_time()
    acumulado, cuadros = 0.0, 0

    while not glfw.window_should_close(ventana):
        glfw.poll_events()
        ahora = glfw.get_time()
        dt = min(ahora - previo, 0.1)
        previo = ahora
        acumulado += dt
        cuadros += 1
        if acumulado >= 0.5:
            estado["fps"] = cuadros / acumulado
            acumulado, cuadros = 0.0, 0

        if glfw.get_key(ventana, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(ventana, True)

        ancho_v, alto_v = glfw.get_window_size(ventana)
        ancho_fb, alto_fb = glfw.get_framebuffer_size(ventana)
        if ancho_fb == 0 or alto_fb == 0:   # ventana minimizada
            glfw.wait_events_timeout(0.1)
            continue
        escala = ancho_fb / max(1, ancho_v)

        # El panel lee el mouse al inicio de cada cuadro
        panel.nuevo_cuadro()

        entrada.procesar(
            escena, dt, ANCHO_PANEL,
            rueda=panel.rueda(),
            ui_mouse=panel.capturando_mouse(),
            ui_teclado=panel.capturando_teclado(),
        )

        # Limpia toda la ventana (incluida la franja del panel)
        glViewport(0, 0, ancho_fb, alto_fb)
        glDisable(GL_SCISSOR_TEST)
        glClearColor(0.07, 0.07, 0.09, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Escena 3D en el area a la derecha del panel
        x_panel = int(ANCHO_PANEL * escala)
        escena.configurar_opengl()
        escena.dibujar(x_panel, 0, max(1, ancho_fb - x_panel), alto_fb)

        # Panel izquierdo (2D, encima de la escena)
        panel.dibujar(escena, estado, alto_v)

        glfw.swap_buffers(ventana)

        # LIMITE FPS (configuracion global): espera lo que falte del cuadro
        limitador.esperar(escena.global_.limite_fps)

    for nodo in escena.nodos:
        if nodo.TIPO == "nodeAudio":
            nodo.detener()
    for objeto in escena.objetos():
        objeto.liberar()
    panel.cerrar()
    glfw.terminate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
