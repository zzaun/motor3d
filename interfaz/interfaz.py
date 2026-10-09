"""Interfaz grafica propia (solo botones), dibujada con OpenGL en 2D encima
de la escena. Esta basada en tu ejemplo: mismos botones (gris, gris claro al
pasar el cursor, color de "activo"), misma fuente de pixeles y el mismo clic
leido con glfw.

Es de "modo inmediato": en cada cuadro se llama, en orden, a boton(),
numero(), conmutador()... y cada llamada dibuja el control y devuelve de
inmediato si hubo clic.

El panel izquierdo se divide en REGIONES (NODOS, CONFIGURACION GLOBAL, NODE
CONFIGURACION). Cada region tiene su propio color, su propio desplazamiento
(scroll) y recorta lo que se sale de ella.

Todo se mide en pixeles de ventana, con el origen arriba a la izquierda.
"""
import glfw

from OpenGL.GL import *

from .fuente import dibujar_texto, ancho_texto, normalizar

# ----------------------------------------------------------------------
# Medidas (pixeles)
# ----------------------------------------------------------------------
ANCHO = 360            # ancho de la franja izquierda
MARGEN = 8             # espacio a los lados
ALTO_FILA = 26         # alto de cada boton / fila
SEPARACION = 4         # espacio vertical entre filas
ANCHO_BARRA = 6        # ancho de la barra de desplazamiento
ESCALA = 2             # cada pixel de letra = 2x2 pixeles reales
ALTO_TEXTO = 7 * ESCALA + 4
ALTO_TITULO = 24       # barra de titulo de cada region
ANCHO_ETIQUETA = 148   # espacio para el nombre de un parametro

# ----------------------------------------------------------------------
# Colores
# ----------------------------------------------------------------------
COLOR_FONDO = (0.07, 0.07, 0.09)
COLOR_TEXTO = (1.0, 1.0, 1.0)
COLOR_GRIS = (0.66, 0.68, 0.74)
COLOR_AVISO = (1.0, 0.65, 0.25)


class Tema:
    """Colores de una region: fondo, barra de titulo y botones."""

    def __init__(self, fondo, titulo, normal, sobre, activo, caja):
        self.fondo, self.titulo = fondo, titulo
        self.normal, self.sobre, self.activo, self.caja = normal, sobre, activo, caja


# NODOS = cafe, CONFIGURACION GLOBAL = verde, NODE CONFIGURACION = azul
TEMA_CAFE = Tema((0.15, 0.11, 0.08), (0.50, 0.32, 0.16), (0.30, 0.21, 0.14),
                 (0.45, 0.31, 0.20), (0.82, 0.54, 0.20), (0.10, 0.07, 0.05))
TEMA_VERDE = Tema((0.07, 0.15, 0.10), (0.18, 0.45, 0.25), (0.14, 0.28, 0.18),
                  (0.22, 0.42, 0.27), (0.32, 0.78, 0.40), (0.05, 0.10, 0.07))
TEMA_AZUL = Tema((0.07, 0.10, 0.19), (0.18, 0.32, 0.60), (0.14, 0.20, 0.36),
                 (0.22, 0.31, 0.52), (0.27, 0.58, 0.98), (0.05, 0.07, 0.14))


class Interfaz:
    def __init__(self, ventana):
        # Guardamos la ventana para leer el mouse y su tamano
        self.ventana = ventana

        # Clics y rueda que llegan por callback; se procesan en nuevo_cuadro()
        self._clics = []
        self._rueda_pendiente = 0.0
        self._rueda_panel = 0.0
        self._rueda_escena = 0.0

        # Desplazamiento de cada region: clave -> {"scroll": px}
        self.regiones = {}
        # Secciones plegables: clave -> abierta (True/False)
        self.abiertos = {}

        # Estado del cuadro actual
        self.mx = self.my = 0.0
        self.ancho_v = self.alto_v = 0
        self.clic = None
        self.izq_abajo = False
        self.shift = False
        self.ahora = 0.0
        self._y = 0.0
        self._contador = 0
        self._tema = TEMA_AZUL
        self._clip = None            # (x0, y0, x1, y1) de la region actual
        self._region = None          # datos de la region abierta

        # Para repetir un boton +/- mientras se mantiene presionado
        self._id_mantenido = None
        self._t_repite = 0.0

        # Registramos las funciones que se llaman al hacer clic y al girar la rueda
        glfw.set_mouse_button_callback(ventana, self._al_clic)
        glfw.set_scroll_callback(ventana, self._al_rueda)

    # ------------------------------------------------------------------
    # Callbacks de glfw
    # ------------------------------------------------------------------
    def _al_clic(self, ventana, boton, accion, mods):
        # Solo reaccionamos al presionar el boton izquierdo
        if boton == glfw.MOUSE_BUTTON_LEFT and accion == glfw.PRESS:
            x, y = glfw.get_cursor_pos(ventana)
            # Solo guardamos los clics que caen sobre el panel
            if x <= ANCHO:
                self._clics.append((x, y))

    def _al_rueda(self, ventana, dx, dy):
        self._rueda_pendiente += dy

    # ------------------------------------------------------------------
    # Ciclo de cada cuadro
    # ------------------------------------------------------------------
    def nuevo_cuadro(self):
        """Lee el estado del mouse. Llamar al inicio de cada cuadro."""
        self.mx, self.my = glfw.get_cursor_pos(self.ventana)
        self.ancho_v, self.alto_v = glfw.get_window_size(self.ventana)
        self.ahora = glfw.get_time()
        self.izq_abajo = (glfw.get_mouse_button(
            self.ventana, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS)
        self.shift = (glfw.get_key(self.ventana, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
                      or glfw.get_key(self.ventana, glfw.KEY_RIGHT_SHIFT) == glfw.PRESS)

        # Un clic por cuadro (el mas antiguo)
        self.clic = self._clics.pop(0) if self._clics else None
        if not self.izq_abajo:
            self._id_mantenido = None

        # La rueda mueve la region bajo el cursor, o la camara si esta fuera del panel
        rueda = self._rueda_pendiente
        self._rueda_pendiente = 0.0
        if self.mx <= ANCHO:
            self._rueda_panel, self._rueda_escena = rueda, 0.0
        else:
            self._rueda_panel, self._rueda_escena = 0.0, rueda

    def rueda(self):
        """Rueda del mouse que le toca a la escena (zoom de camara)."""
        return self._rueda_escena

    def capturando_mouse(self):
        """True si el cursor esta sobre el panel."""
        return self.mx <= ANCHO

    def capturando_teclado(self):
        """Esta interfaz no usa el teclado."""
        return False

    @property
    def ancho_util(self):
        """Ancho disponible para los controles."""
        return ANCHO - 2 * MARGEN - ANCHO_BARRA

    # ------------------------------------------------------------------
    # Estado 2D de OpenGL (igual que en tu ejemplo)
    # ------------------------------------------------------------------
    def iniciar_2d(self):
        fb_ancho, fb_alto = glfw.get_framebuffer_size(self.ventana)

        # La escena dejo el viewport reducido: lo ponemos a toda la ventana
        glViewport(0, 0, fb_ancho, fb_alto)

        # Proyeccion ortogonal: 1 unidad = 1 pixel, Y crece hacia abajo
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.ancho_v, self.alto_v, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Los botones no usan iluminacion ni profundidad
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)

        # Fondo de toda la franja (las regiones lo cubren casi por completo)
        self._contador = 0
        self._clip = None
        self.rect(0, 0, ANCHO, self.alto_v, COLOR_FONDO)

    def terminar_2d(self):
        """Restaura el estado 3D."""
        glDisable(GL_SCISSOR_TEST)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_CULL_FACE)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

    def _recortar_pantalla(self, x, y, ancho, alto):
        """Recorta el dibujo a un rectangulo (en pixeles de ventana)."""
        fb_ancho, fb_alto = glfw.get_framebuffer_size(self.ventana)
        k = fb_ancho / max(1, self.ancho_v)
        glEnable(GL_SCISSOR_TEST)
        glScissor(int(x * k), int(fb_alto - (y + alto) * k),
                  int(ancho * k) + 1, int(alto * k) + 1)

    # ------------------------------------------------------------------
    # Regiones (bloques de colores con su propio scroll)
    # ------------------------------------------------------------------
    def abrir_region(self, clave, y, alto, tema, titulo, alto_pie=0, derecha=""):
        """Dibuja el fondo y el titulo de una region y empieza su contenido.

        alto_pie: espacio fijo al final de la region (fuera del scroll) para
        botones que deben verse siempre; se usa con abrir_pie().
        derecha: texto corto pegado a la derecha de la barra de titulo.
        """
        datos = self.regiones.setdefault(clave, {"scroll": 0.0})
        self._tema = tema

        # Fondo y barra de titulo
        self.rect(0, y, ANCHO, alto, tema.fondo)
        self.rect(0, y, ANCHO, ALTO_TITULO, tema.titulo)
        glColor3f(*COLOR_TEXTO)
        ty = y + (ALTO_TITULO - 7 * ESCALA) / 2
        dibujar_texto(MARGEN, ty, self._recortar(titulo, ANCHO - 2 * MARGEN), ESCALA)
        if derecha:
            derecha = normalizar(derecha)
            glColor3f(*COLOR_GRIS)
            dibujar_texto(ANCHO - MARGEN - ancho_texto(derecha, ESCALA), ty, derecha, ESCALA)

        # Area de contenido
        y_cont = y + ALTO_TITULO
        alto_cont = max(0, alto - ALTO_TITULO - alto_pie)

        # La rueda desplaza la region que esta bajo el cursor
        if (self._rueda_panel and self.mx <= ANCHO
                and y_cont <= self.my <= y_cont + alto_cont):
            datos["scroll"] -= self._rueda_panel * 40.0
            self._rueda_panel = 0.0

        self._region = {"datos": datos, "y": y, "alto": alto, "y_cont": y_cont,
                        "alto_cont": alto_cont, "alto_pie": alto_pie}
        self._clip = (0, y_cont, ANCHO, y_cont + alto_cont)
        self._recortar_pantalla(0, y_cont, ANCHO, alto_cont)
        self._y = y_cont + MARGEN - datos["scroll"]

    def cerrar_region(self):
        """Termina el contenido: limita el scroll y dibuja la barra."""
        r = self._region
        datos = r["datos"]
        contenido = self._y + datos["scroll"] + MARGEN - r["y_cont"]
        maximo = max(0.0, contenido - r["alto_cont"])
        datos["scroll"] = max(0.0, min(maximo, datos["scroll"]))

        if maximo > 0:
            alto_barra = max(20.0, r["alto_cont"] * r["alto_cont"] / contenido)
            y_barra = r["y_cont"] + (datos["scroll"] / maximo) * (r["alto_cont"] - alto_barra)
            self.rect(ANCHO - ANCHO_BARRA, y_barra, ANCHO_BARRA - 1, alto_barra,
                      self._tema.sobre)

        glDisable(GL_SCISSOR_TEST)
        self._clip = None

    def abrir_pie(self):
        """Empieza el pie fijo de la region abierta (no se desplaza)."""
        r = self._region
        y_pie = r["y"] + r["alto"] - r["alto_pie"]
        self.rect(0, y_pie, ANCHO, r["alto_pie"], self._tema.titulo)
        self._clip = (0, y_pie, ANCHO, y_pie + r["alto_pie"])
        self._recortar_pantalla(0, y_pie, ANCHO, r["alto_pie"])
        self._y = y_pie + 4

    def cerrar_pie(self):
        glDisable(GL_SCISSOR_TEST)
        self._clip = None

    # ------------------------------------------------------------------
    # Dibujo basico
    # ------------------------------------------------------------------
    def rect(self, x, y, ancho, alto, color):
        glColor3f(*color)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + ancho, y)
        glVertex2f(x + ancho, y + alto)
        glVertex2f(x, y + alto)
        glEnd()

    def _dentro_clip(self, px, py):
        if self._clip is None:
            return True
        x0, y0, x1, y1 = self._clip
        return x0 <= px <= x1 and y0 <= py <= y1

    def _visible(self, y, alto):
        if self._clip is None:
            return y + alto >= 0 and y <= self.alto_v
        return y + alto >= self._clip[1] and y <= self._clip[3]

    def _recortar(self, texto, ancho_disponible):
        """Acorta el texto con '.' si no cabe en el ancho dado."""
        texto = normalizar(texto)
        maximo = int((ancho_disponible + ESCALA) // (6 * ESCALA))
        if len(texto) <= maximo:
            return texto
        return texto[:max(0, maximo - 1)] + "."

    # ------------------------------------------------------------------
    # Controles de bajo nivel (usan posiciones absolutas)
    # ------------------------------------------------------------------
    def _boton(self, x, y, ancho, alto, texto, activo=False, repetir=False,
               color=None, alinear="centro", texto_derecha=None):
        """Dibuja un boton y devuelve True si se hizo clic (o se repite)."""
        self._contador += 1
        ident = self._contador
        visible = self._visible(y, alto)
        if not visible:
            return False

        # El cursor esta encima del boton (y dentro de la region)
        sobre = (x <= self.mx <= x + ancho and y <= self.my <= y + alto
                 and self._dentro_clip(self.mx, self.my))

        pulsado = False
        if (self.clic is not None
                and x <= self.clic[0] <= x + ancho
                and y <= self.clic[1] <= y + alto
                and self._dentro_clip(*self.clic)):
            # Clic nuevo sobre este boton: lo "consumimos"
            pulsado = True
            self.clic = None
            if repetir:
                self._id_mantenido = ident
                self._t_repite = self.ahora + 0.40
        elif (repetir and self.izq_abajo and sobre
              and self._id_mantenido == ident and self.ahora >= self._t_repite):
            # Boton mantenido presionado: repite rapido
            pulsado = True
            self._t_repite = self.ahora + 0.06

        # Verde/color de activo, claro al pasar el cursor, oscuro normal
        t = self._tema
        if activo:
            relleno = t.activo
        elif sobre:
            relleno = t.sobre
        elif color is not None:
            relleno = color
        else:
            relleno = t.normal
        self.rect(x, y, ancho, alto, relleno)

        # Texto (y, opcionalmente, una etiqueta gris pegada a la derecha)
        ty = y + (alto - 7 * ESCALA) / 2
        ancho_der = 0
        if texto_derecha:
            texto_derecha = normalizar(texto_derecha)
            ancho_der = ancho_texto(texto_derecha, ESCALA)
            glColor3f(*COLOR_GRIS if not activo else COLOR_TEXTO)
            dibujar_texto(x + ancho - 6 - ancho_der, ty, texto_derecha, ESCALA)
            ancho_der += 10
        texto = self._recortar(texto, ancho - 12 - ancho_der)
        tx = x + 6 if alinear == "izq" else x + (ancho - ancho_texto(texto, ESCALA)) / 2
        glColor3f(*COLOR_TEXTO)
        dibujar_texto(tx, ty, texto, ESCALA)
        return pulsado

    # ------------------------------------------------------------------
    # Controles de alto nivel (usan el diseno vertical automatico)
    # ------------------------------------------------------------------
    def espacio(self, pixeles=6):
        self._y += pixeles

    def texto(self, texto, color=COLOR_GRIS, sangria=0):
        """Una linea de texto."""
        if self._visible(self._y, ALTO_TEXTO):
            glColor3f(*color)
            dibujar_texto(MARGEN + sangria, self._y + 2,
                          self._recortar(texto, self.ancho_util - sangria), ESCALA)
        self._y += ALTO_TEXTO

    def parrafo(self, texto, color=COLOR_GRIS):
        """Texto que se parte en varias lineas segun el ancho del panel."""
        maximo = int((self.ancho_util + ESCALA) // (6 * ESCALA))
        linea = ""
        for palabra in normalizar(texto).split():
            if linea and len(linea) + 1 + len(palabra) > maximo:
                self.texto(linea, color)
                linea = palabra
            else:
                linea = (linea + " " + palabra).strip()
        if linea:
            self.texto(linea, color)

    def boton(self, texto, activo=False, sangria=0, color=None, alinear="centro",
              texto_derecha=None):
        """Boton de ancho completo. Devuelve True si se hizo clic."""
        r = self._boton(MARGEN + sangria, self._y, self.ancho_util - sangria,
                        ALTO_FILA, texto, activo, False, color, alinear,
                        texto_derecha)
        self._y += ALTO_FILA + SEPARACION
        return r

    def botones_fila(self, textos, activos=None):
        """Varios botones en una fila. Devuelve el indice clicado o -1."""
        n = len(textos)
        hueco = 4
        ancho = (self.ancho_util - hueco * (n - 1)) / n
        clicado = -1
        for i, t in enumerate(textos):
            activo = bool(activos[i]) if activos else False
            x = MARGEN + i * (ancho + hueco)
            if self._boton(x, self._y, ancho, ALTO_FILA, t, activo):
                clicado = i
        self._y += ALTO_FILA + SEPARACION
        return clicado

    def conmutador(self, texto, valor):
        """Boton que se enciende o apaga. Devuelve el nuevo valor."""
        if self.boton(texto, bool(valor), 0, None, "izq",
                      "SI" if valor else "NO"):
            return not valor
        return valor

    def numero(self, etiqueta, valor, paso, minimo=None, maximo=None, decimales=2):
        """Fila: ETIQUETA [-] valor [+]. Shift = pasos x10. Devuelve el valor."""
        y = self._y
        x_menos = MARGEN + ANCHO_ETIQUETA
        w_boton, w_valor = 28, 84
        x_valor = x_menos + w_boton + 2
        x_mas = x_valor + w_valor + 2

        if self._visible(y, ALTO_FILA):
            glColor3f(*COLOR_TEXTO)
            dibujar_texto(MARGEN, y + (ALTO_FILA - 7 * ESCALA) / 2,
                          self._recortar(etiqueta, ANCHO_ETIQUETA - 4), ESCALA)

        menos = self._boton(x_menos, y, w_boton, ALTO_FILA, "-", False, True)

        if self._visible(y, ALTO_FILA):
            self.rect(x_valor, y, w_valor, ALTO_FILA, self._tema.caja)
            cifra = ("%." + str(decimales) + "f") % valor
            glColor3f(*COLOR_TEXTO)
            dibujar_texto(x_valor + (w_valor - ancho_texto(cifra, ESCALA)) / 2,
                          y + (ALTO_FILA - 7 * ESCALA) / 2, cifra, ESCALA)

        mas = self._boton(x_mas, y, w_boton, ALTO_FILA, "+", False, True)

        # Solo se toca el valor cuando se pulsa - o + (asi la interfaz no
        # redondea ni "pelea" con otros cambios, como orbitar la camara)
        if menos or mas:
            k = paso * (10.0 if self.shift else 1.0)
            valor += k if mas else -k
            if minimo is not None:
                valor = max(minimo, valor)
            if maximo is not None:
                valor = min(maximo, valor)
            valor = round(valor, decimales + 2)

        self._y += ALTO_FILA + SEPARACION
        return valor

    def vec3(self, prefijo, valores, paso, minimo=None, maximo=None,
             decimales=2, ejes="XYZ"):
        """Tres filas numero() (una por eje). Devuelve la lista nueva."""
        nuevos = list(valores)
        for i, eje in enumerate(ejes):
            nuevos[i] = self.numero("%s %s" % (prefijo, eje), valores[i], paso,
                                    minimo, maximo, decimales)
        return nuevos

    def color3(self, prefijo, valores):
        """Muestra de color + tres filas R, G, B entre 0 y 1."""
        y = self._y
        if self._visible(y, ALTO_FILA):
            glColor3f(*COLOR_TEXTO)
            dibujar_texto(MARGEN, y + (ALTO_FILA - 7 * ESCALA) / 2,
                          self._recortar(prefijo, ANCHO_ETIQUETA - 4), ESCALA)
            self.rect(MARGEN + ANCHO_ETIQUETA, y, 28 + 84 + 28 + 4, ALTO_FILA,
                      tuple(max(0.0, min(1.0, c)) for c in valores))
        self._y += ALTO_FILA + SEPARACION
        return self.vec3(prefijo, valores, 0.05, 0.0, 1.0, 2, "RGB")
