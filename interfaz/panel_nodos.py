"""Panel izquierdo del motor: tres bloques siempre visibles.

  NODOS [CAFE]                lista jerarquica con todos los nodos de la
                              escena (solo nombres, y su tipo a la derecha).
                              Al pie: agregar luces y eliminar el nodo elegido.
  CONFIGURACION GLOBAL [VERDE]  todos los parametros del nodeGlobal y el boton
                              GUARDAR (escribe escena.txt).
  NODE CONFIGURACION [AZUL]   el nodo seleccionado y SOLO sus parametros.

Los controles de los parametros no estan escritos a mano: se generan a partir
de la tabla PARAMS de cada clase de nodo (motor/nodos.py), asi que un
parametro nuevo aparece solo en la interfaz y en los archivos.
"""
from motor.archivos import guardar_escena
from motor.nodos import NodeCamera, Node3D

from .interfaz import (Interfaz, TEMA_CAFE, TEMA_VERDE, TEMA_AZUL, COLOR_TEXTO,
                       COLOR_GRIS, COLOR_AVISO, ALTO_FILA, SEPARACION)
from .fuente import liberar_listas

# Alto del pie fijo de NODOS: dos filas de botones
ALTO_PIE_NODOS = 2 * (ALTO_FILA + SEPARACION) + 6


class PanelNodos(Interfaz):
    def __init__(self, ventana):
        super().__init__(ventana)
        self.ruta_escena = "escena.txt"      # lo cambia main.py
        self._aviso_lista = ("", 0.0)        # (texto, hasta cuando)
        self._aviso_guardar = ("", 0.0)

    def cerrar(self):
        liberar_listas()

    # ------------------------------------------------------------------
    # Dibujo del panel (una vez por cuadro)
    # ------------------------------------------------------------------
    def dibujar(self, escena, estado, alto_ventana):
        if self.ancho_v == 0 or self.alto_v == 0:
            return
        self.iniciar_2d()

        # Reparto del alto entre los tres bloques
        alto = self.alto_v
        alto_nodos = max(200, int(alto * 0.36))
        alto_global = max(180, int(alto * 0.27))
        alto_config = max(120, alto - alto_nodos - alto_global)

        y = 0
        self.abrir_region("nodos", y, alto_nodos, TEMA_CAFE, "NODOS",
                          ALTO_PIE_NODOS, "%.0f FPS" % estado.get("fps", 0.0))
        self._lista_nodos(escena)
        self.cerrar_region()
        self._pie_nodos(escena)
        self.cerrar_pie()

        y += alto_nodos
        self.abrir_region("global", y, alto_global, TEMA_VERDE,
                          "CONFIGURACION GLOBAL")
        self._config_global(escena)
        self.cerrar_region()

        y += alto_global
        self.abrir_region("config", y, alto_config, TEMA_AZUL,
                          "NODE CONFIGURACION")
        self._config_nodo(escena)
        self.cerrar_region()

        self.terminar_2d()

    # ------------------------------------------------------------------
    # NODOS
    # ------------------------------------------------------------------
    def _lista_nodos(self, escena):
        for nodo, nivel in escena.recorrer_arbol():
            elegido = escena.seleccion is nodo
            if self.boton(nodo.name, elegido, nivel * 14, None, "izq", nodo.TIPO):
                escena.seleccionar(nodo)

    def _pie_nodos(self, escena):
        """Botones fijos al pie de NODOS: agregar luces y eliminar."""
        self.abrir_pie()
        i = self.botones_fila(["+ PUNTO", "+ SOL", "+ SPOT"])
        if i >= 0:
            tipo = ["nodeLightPoint", "nodeLightSol", "nodeLightSpot"][i]
            nueva = escena.agregar_luz(tipo)
            if nueva is None:
                self._aviso_lista = ("MAXIMO 8 LUCES", self.ahora + 3.0)
            else:
                escena.seleccionar(nueva)

        texto, hasta = self._aviso_lista
        if texto and self.ahora < hasta:
            self.boton(texto, False, 0, (0.55, 0.28, 0.10))
        else:
            borrable = (escena.seleccion is not None
                        and not isinstance(escena.seleccion, NodeCamera))
            if self.boton("ELIMINAR NODO") and borrable:
                escena.eliminar(escena.seleccion)

    # ------------------------------------------------------------------
    # CONFIGURACION GLOBAL
    # ------------------------------------------------------------------
    def _config_global(self, escena):
        texto, hasta = self._aviso_guardar
        etiqueta = texto if (texto and self.ahora < hasta) else "GUARDAR"
        if self.boton(etiqueta, etiqueta != "GUARDAR"):
            try:
                guardar_escena(self.ruta_escena, escena)
                self._aviso_guardar = ("ESCENA GUARDADA", self.ahora + 2.0)
            except OSError as e:
                print("No se pudo guardar la escena:", e)
                self._aviso_guardar = ("ERROR AL GUARDAR", self.ahora + 3.0)
        self._parametros(escena.global_)

    # ------------------------------------------------------------------
    # NODE CONFIGURACION
    # ------------------------------------------------------------------
    def _config_nodo(self, escena):
        nodo = escena.seleccion
        if nodo is None:
            self.parrafo("SELECCIONA UN NODO EN LA LISTA DE NODOS")
            return

        # NODE-NAME [tipo]
        self.texto("%s [%s]" % (nodo.name, nodo.TIPO), COLOR_TEXTO)
        if nodo.padre is not None:
            self.texto("PADRE: " + nodo.padre.name)
        self.espacio(4)

        self._parametros(nodo)

        if isinstance(nodo, NodeCamera):
            self.espacio()
            self.texto("VISTAS RAPIDAS")
            i = self.botones_fila(["FRONTAL", "LATERAL"])
            j = self.botones_fila(["SUPERIOR", "TRASERA"])
            nombres = ["frontal", "lateral", "superior", "trasera"]
            if i >= 0:
                nodo.vista_rapida(nombres[i])
            if j >= 0:
                nodo.vista_rapida(nombres[2 + j])
        elif isinstance(nodo, Node3D):
            self.espacio()
            if self.boton("REINICIAR POSE"):
                nodo.reiniciar()

    # ------------------------------------------------------------------
    # Controles generados a partir de la tabla de parametros
    # ------------------------------------------------------------------
    def _parametros(self, nodo):
        for p in nodo.parametros_visibles():
            self._control(nodo, p)
            if p.ayuda:
                self.texto(p.ayuda, COLOR_GRIS)

    def _control(self, nodo, p):
        valor = getattr(nodo, p.clave)
        nuevo = valor

        if not p.editable:
            self.texto("%s: %s" % (p.etiqueta, valor if valor != "" else "-"))
            return

        if p.tipo == "bool":
            nuevo = self.conmutador(p.etiqueta, valor)
        elif p.tipo in ("int", "float"):
            nuevo = self.numero(p.etiqueta, valor, p.paso, p.minimo, p.maximo,
                                p.decimales)
            if p.tipo == "int":
                nuevo = int(round(nuevo))
        elif p.tipo == "vec3":
            nuevo = self.vec3(p.etiqueta, valor, p.paso, p.minimo, p.maximo,
                              p.decimales, p.ejes)
        elif p.tipo == "color":
            nuevo = self.color3(p.etiqueta, valor)
        elif p.tipo == "opcion":
            self.texto(p.etiqueta)
            activos = [valor == o for o in p.opciones]
            i = self.botones_fila(p.opciones, activos)
            if i >= 0:
                nuevo = p.opciones[i]
        else:
            self.texto("%s: %s" % (p.etiqueta, valor))
            return

        if nuevo != valor:
            # Si el nodo tiene un metodo cambiar_<clave> (por ejemplo la camara
            # al cambiar de modo), se usa para que conserve la vista.
            cambiar = getattr(nodo, "cambiar_" + p.clave, None)
            if cambiar is not None and p.tipo == "opcion":
                cambiar(nuevo)
            else:
                setattr(nodo, p.clave, nuevo)
