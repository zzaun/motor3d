# motor3d: visor/motor 3D con glfw + OpenGL, basado en nodos.
#   Lee los .txt de objetos3d/ (generados por obj_a_cordenas), arma la escena de nodos y la muestra con la interfaz al costado izquierdo:
#  NODOS (cafe) / CONFIGURACION GLOBAL (verde) / NODE CONFIGURACION (azul).
#   Uso: python3 main.py

import os
import sys

import glfw
from OpenGL.GL import *  # noqa: F401,F403

from motor.escena import Escena
from motor.entrada import Entrada
from motor.limitador import LimitadorFPS
from motor.archivos import cargar_escena
from motor.preparar_objetos3d import preparar_objetos3d

# Importa el panel principal de la interfaz
from interfaz.panel_nodos import PanelNodos

# Importa el ancho fijo del panel lateral
from interfaz.interfaz import ANCHO as ANCHO_PANEL

# Obtiene la ruta absoluta del directorio actual
BASE = os.path.dirname(os.path.abspath(__file__))
# Carpeta que contiene los objetos 3D disponibles
CARPETA_OBJETOS = os.path.join(BASE, "objetos3d")
# Archivo donde se guarda y carga la escena
RUTA_ESCENA = os.path.join(BASE, "escena.txt")
# Tamaño inicial de la ventana
ANCHO_VENTANA, ALTO_VENTANA = 1280, 800


def luces_iniciales(escena):
    # Crea la luz direccional principal
    sol = escena.agregar_luz("nodeLightSol")
    sol.power = 0.9
    # Crea una luz puntual complementaria
    punto = escena.agregar_luz("nodeLightPoint")
    punto.color = [1.0, 0.85, 0.6]
    punto.power = 0.7
    punto.radius = 12.0

def crear_escena():
    # Crea la escena principal
    escena = Escena()
    # Carga todos los objetos encontrados en la carpeta objetos3d
    preparar_objetos3d(CARPETA_OBJETOS, escena)
    # Intenta restaurar una escena previamente guardada
    if os.path.isfile(RUTA_ESCENA):
        try:
            cargar_escena(RUTA_ESCENA, escena)
            print("Escena cargada de", RUTA_ESCENA)
        except Exception as error:
            print("Aviso: no se pudo leer escena.txt:", error)
    # Agrega luces por defecto si no existe una escena guardada
    if not escena.luces() and not os.path.isfile(RUTA_ESCENA):
        luces_iniciales(escena)

    # Selecciona el primer objeto 3D encontrado
    for nodo, _nivel in escena.recorrer_arbol():
        if nodo.TIPO == "nodeObjeto3D":
            escena.seleccionar(nodo)
            break

    return escena

def main():
    # Inicializa GLFW
    if not glfw.init():
        print("No se pudo iniciar glfw")
        return 1
    # Crea la ventana principal
    ventana = glfw.create_window(
        ANCHO_VENTANA,
        ALTO_VENTANA,
        "motor3d",
        None,
        None,
    )
    # Finaliza GLFW si la ventana no pudo crearse
    if not ventana:
        glfw.terminate()
        print("No se pudo crear la ventana")
        return 1
    # Establece el contexto OpenGL actual
    glfw.make_context_current(ventana)
    # Desactiva VSync para usar el limitador FPS interno
    glfw.swap_interval(0)
    # Construye la escena
    escena = crear_escena()
    # Aplica la configuracion inicial de OpenGL
    escena.configurar_opengl()
    # Inicializa los sistemas de entrada e interfaz
    entrada = Entrada(ventana)
    panel = PanelNodos(ventana)
    # Asocia la ruta de guardado de la escena al panel
    panel.ruta_escena = RUTA_ESCENA
    # Crea el limitador de velocidad de cuadros
    limitador = LimitadorFPS()
    # Almacena informacion de estado para la interfaz
    estado = {"fps": 0.0}
    # Reproduce automaticamente los audios marcados para inicio
    for nodo in escena.nodos:
        if nodo.TIPO == "nodeAudio" and nodo.al_iniciar:
            nodo.reproducir()

    # Almacena el instante anterior para calcular delta time
    previo = glfw.get_time()
    # Acumuladores usados para medir FPS
    acumulado, cuadros = 0.0, 0

    # Bucle principal de la aplicacion
    while not glfw.window_should_close(ventana):
        # Procesa eventos pendientes del sistema
        glfw.poll_events()
        # Calcula el tiempo transcurrido desde el cuadro anterior
        ahora = glfw.get_time()
        dt = min(ahora - previo, 0.1)
        previo = ahora
        # Actualiza los acumuladores de FPS
        acumulado += dt
        cuadros += 1
        # Actualiza la medicion de FPS cada medio segundo
        if acumulado >= 0.5:
            estado["fps"] = cuadros / acumulado
            acumulado, cuadros = 0.0, 0

        # Cierra la aplicacion al presionar ESC
        if glfw.get_key(ventana, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(ventana, True)

        # Obtiene el tamaño logico y real de la ventana
        ancho_v, alto_v = glfw.get_window_size(ventana)
        ancho_fb, alto_fb = glfw.get_framebuffer_size(ventana)

        # Omite el renderizado mientras la ventana este minimizada
        if ancho_fb == 0 or alto_fb == 0:
            glfw.wait_events_timeout(0.1)
            continue

        # Calcula la relacion entre pixeles reales y logicos
        escala = ancho_fb / max(1, ancho_v)
        # Reinicia el estado de entrada de la interfaz
        panel.nuevo_cuadro()
        # Procesa entrada de teclado y mouse
        entrada.procesar(
            escena,
            dt,
            ANCHO_PANEL,
            rueda=panel.rueda(),
            ui_mouse=panel.capturando_mouse(),
            ui_teclado=panel.capturando_teclado(),
        )

        # Configura el viewport para toda la ventana
        glViewport(0, 0, ancho_fb, alto_fb)
        # Desactiva el recorte por regiones
        glDisable(GL_SCISSOR_TEST)
        # Define el color de limpieza del cuadro
        glClearColor(0.07, 0.07, 0.09, 1.0)
        # Limpia los buffers de color y profundidad
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Calcula el ancho real ocupado por el panel lateral
        x_panel = int(ANCHO_PANEL * escala)
        # Actualiza estados OpenGL de la escena
        escena.configurar_opengl()
        # Renderiza la escena 3D fuera del area del panel
        escena.dibujar(
            x_panel,
            0,
            max(1, ancho_fb - x_panel),
            alto_fb,
        )

        # Dibuja la interfaz sobre la escena
        panel.dibujar(escena, estado, alto_v)
        # Presenta el cuadro renderizado en pantalla
        glfw.swap_buffers(ventana)
        # Espera para respetar el limite de FPS configurado
        limitador.esperar(escena.global_.limite_fps)

    # Detiene todos los nodos de audio
    for nodo in escena.nodos:
        if nodo.TIPO == "nodeAudio":
            nodo.detener()

    # Libera recursos graficos de los objetos cargados
    for objeto in escena.objetos():
        objeto.liberar()

    # Libera recursos de la interfaz
    panel.cerrar()
    # Finaliza GLFW
    glfw.terminate()
    return 0

# Ejecuta la aplicacion si el archivo se inicia directamente
if __name__ == "__main__":
    sys.exit(main())