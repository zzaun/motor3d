"""Entrada de teclado y ratón (por sondeo, sin callbacks propios para no
pelear con la interfaz).

Controles:
  Tab ............ siguiente entidad seleccionada
  C .............. alternar cámara orbital / libre
  1 2 3 4 ........ vistas frontal / lateral / superior / trasera
  Shift+R ........ reiniciar todos los objetos
  Orbital: clic izq. orbitar, clic der. o central mover, rueda zoom
  Libre:   clic der. (o izq.) mirar, WASD mover, Q/E bajar/subir
  Shift .......... movimiento más rápido
"""
import glfw


class Entrada:
    def __init__(self, ventana):
        self.ventana = ventana
        self._previas = {}
        self._cursor = glfw.get_cursor_pos(ventana)
        self._arrastre = False        # ¿hay un arrastre iniciado sobre la escena?
        self._algun_previo = False    # ¿había algún botón presionado el cuadro anterior?

    # ------------------------------------------------------------------
    def _pulsada(self, tecla):
        """True solo en el cuadro en que se presiona la tecla."""
        ahora = glfw.get_key(self.ventana, tecla) == glfw.PRESS
        antes = self._previas.get(tecla, False)
        self._previas[tecla] = ahora
        return ahora and not antes

    def _mantenida(self, tecla):
        return glfw.get_key(self.ventana, tecla) == glfw.PRESS

    def _boton(self, boton):
        return glfw.get_mouse_button(self.ventana, boton) == glfw.PRESS

    # ------------------------------------------------------------------
    def procesar(self, escena, dt, panel_ancho, rueda, ui_mouse, ui_teclado):
        """Actualiza cámara y selección. `panel_ancho` en coordenadas de ventana."""
        cam = escena.camara
        x, y = glfw.get_cursor_pos(self.ventana)
        dx, dy = x - self._cursor[0], y - self._cursor[1]
        self._cursor = (x, y)

        sobre_escena = x > panel_ancho and not ui_mouse
        shift = self._mantenida(glfw.KEY_LEFT_SHIFT) or self._mantenida(glfw.KEY_RIGHT_SHIFT)

        # ---- Cámara con el ratón ----
        izq = self._boton(glfw.MOUSE_BUTTON_LEFT)
        der = self._boton(glfw.MOUSE_BUTTON_RIGHT)
        cen = self._boton(glfw.MOUSE_BUTTON_MIDDLE)
        algun = izq or der or cen
        if not algun:
            self._arrastre = False
        elif not self._algun_previo and sobre_escena:
            self._arrastre = True   # el arrastre empezó sobre la escena
        self._algun_previo = algun

        if cam.modo == "orbital":
            if self._arrastre:
                if izq and not shift:
                    cam.orbitar(dx, dy)
                elif der or cen or (izq and shift):
                    cam.desplazar_objetivo(dx, dy)
            if sobre_escena and rueda:
                cam.acercar(rueda)
        else:
            if self._arrastre and (der or izq):
                cam.mirar(dx, dy)
            if sobre_escena and rueda:
                cam.mover_libre(rueda * 2.0, 0, 0, 0.25)

        # ---- Teclado (si la interfaz no lo está usando) ----
        if ui_teclado:
            return
        if self._pulsada(glfw.KEY_TAB):
            escena.seleccionar_siguiente()
        if self._pulsada(glfw.KEY_C):
            cam.cambiar_modo("libre" if cam.modo == "orbital" else "orbital")
        for tecla, vista in ((glfw.KEY_1, "frontal"), (glfw.KEY_2, "lateral"),
                             (glfw.KEY_3, "superior"), (glfw.KEY_4, "trasera")):
            if self._pulsada(tecla):
                cam.vista_rapida(vista)
        if shift and self._pulsada(glfw.KEY_R):
            escena.reiniciar_objetos()

        if cam.modo == "libre":
            k = 3.0 if shift else 1.0
            adelante = (self._mantenida(glfw.KEY_W) - self._mantenida(glfw.KEY_S))
            derecha = (self._mantenida(glfw.KEY_D) - self._mantenida(glfw.KEY_A))
            arriba = (self._mantenida(glfw.KEY_E) - self._mantenida(glfw.KEY_Q))
            cam.mover_libre(adelante * k, derecha * k, arriba * k, dt)


    # ------------------------------------------------------------------
