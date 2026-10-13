#   Escena: contiene todos los nodos y sabe dibujarlos.
#  - global_  : el nodeGlobal (ambiente general; uno solo, siempre id 0)
#  - nodos    : todos los demas nodos (objetos, luces y camara), en una lista plana. La jerarquia sale de los campos padre / hijos.
#  - camara   : el nodeCamera (tambien esta dentro de `nodos`)
#  - seleccion: el nodo seleccionado (o None)
# El dibujo se hace en dos pasadas sobre el arbol de nodos:
#  1) luces: cada luz se configura con la matriz de su nodo ya aplicada, asi OpenGL transforma su posicion y direccion (y funciona aunque la luz sea
#    hija de otro nodo).
#  2) objetos: se dibuja la geometria, los ejes, los huesos y los iconos.


from OpenGL.GL import *  # noqa: F401,F403

from . import audio
from .nodos import (NodeGlobal, NodeCamera, NodeObjeto3D, NodeLight, NodeAudio,
                    NodeLightPoint, NodeLightSol, NodeLightSpot, MAX_LUCES)

_CLASES_LUZ = {"nodeLightPoint": NodeLightPoint, "nodeLightSol": NodeLightSol, "nodeLightSpot": NodeLightSpot}
_NOMBRES_LUZ = {"nodeLightPoint": "Punto", "nodeLightSol": "Sol", "nodeLightSpot": "Spot"}

class Escena:
    def __init__(self):
        self.global_ = NodeGlobal("global")
        self.global_.id = 0

        self.nodos = []
        self._siguiente_id = 1
        self.seleccion = None
        self._luz_indice = 0
        self._luz_activa = True

        self.camara = NodeCamera("camara")
        self.agregar(self.camara)

        # Reservado para la futura animacion (por fotograma)
        self.frame_actual = 0
        self.reproduciendo = False
    # ------------------------------------------------------------------
    # Gestion de nodos
    # ------------------------------------------------------------------
    def _nombre_unico(self, nombre):
        usados = {n.name for n in self.nodos}
        base, k = nombre, 2
        while nombre in usados:
            nombre = "%s_%d" % (base, k)
            k += 1
        return nombre

    def agregar(self, nodo, padre=None):
        """Agrega un nodo a la escena (con id y nombre unicos)."""
        nodo.name = self._nombre_unico(nodo.name)
        if nodo.id < 0:
            nodo.id = self._siguiente_id
        self._siguiente_id = max(self._siguiente_id, nodo.id) + 1
        self.nodos.append(nodo)
        if padre is not None:
            self.enlazar(nodo, padre)
        return nodo

    def normalizar_ids(self):
        """Garantiza que no haya dos nodos con el mismo id."""
        vistos = {0}
        for n in self.nodos:
            if n.id in vistos or n.id < 0:
                n.id = self._siguiente_id
            vistos.add(n.id)
            self._siguiente_id = max(self._siguiente_id, n.id) + 1

    def enlazar(self, nodo, padre):
        """Hace de `padre` el padre de `nodo` (None = raiz). No cambia posiciones."""
        if isinstance(nodo, NodeCamera):
            return False
        if padre is not None:
            if padre is nodo or self.es_ancestro(nodo, padre):
                print(f"  aviso: ciclo en la jerarquia con '{nodo.name}', se ignora")
                return False
            if not padre.es_3d() or isinstance(padre, NodeCamera):
                return False
        if nodo.padre is not None and nodo in nodo.padre.hijos:
            nodo.padre.hijos.remove(nodo)
        nodo.padre = padre
        if padre is not None:
            padre.hijos.append(nodo)
        return True

    def es_ancestro(self, candidato, nodo):
        """True si `candidato` es ancestro de `nodo`."""
        actual, visto = nodo, set()
        while actual is not None and id(actual) not in visto:
            if actual is candidato:
                return True
            visto.add(id(actual))
            actual = actual.padre
        return False

    def raices(self):
        return [n for n in self.nodos if n.padre is None]

    def objetos(self):
        return [n for n in self.nodos if isinstance(n, NodeObjeto3D)]

    def luces(self):
        return [n for n in self.nodos if isinstance(n, NodeLight)]

    def agregar_luz(self, tipo):
        """Crea una luz del tipo dado. Devuelve None si ya hay 8."""
        if len(self.luces()) >= MAX_LUCES:
            return None
        luz = _CLASES_LUZ[tipo](_NOMBRES_LUZ[tipo])
        if tipo == "nodeLightSol":
            luz.location = [4.0, 5.0, 4.0]
            luz.rotation = [-50.0, 30.0, 0.0]
        elif tipo == "nodeLightSpot":
            luz.location = [0.0, 4.0, 0.0]
            luz.rotation = [-90.0, 0.0, 0.0]
        else:
            luz.location = [-3.0, 3.0, 3.0]
        luz.guardar_reposo()
        return self.agregar(luz)

    def agregar_audio(self):
        """Crea un nodeAudio con el primer sonido de recursos/sonidos/."""
        nodo = NodeAudio("Audio")
        sonidos = audio.listar_sonidos()
        nodo.archivo = sonidos[0] if sonidos else ""
        nodo.guardar_reposo()
        return self.agregar(nodo)

    def eliminar(self, nodo):
        """Elimina un nodo (sus hijos pasan al padre del nodo)."""
        if nodo is None or isinstance(nodo, NodeCamera) or nodo not in self.nodos:
            return False
        for hijo in list(nodo.hijos):
            self.enlazar(hijo, nodo.padre)
        self.enlazar(nodo, None)
        self.nodos.remove(nodo)
        if isinstance(nodo, NodeObjeto3D):
            nodo.liberar()
        if isinstance(nodo, NodeAudio):
            nodo.detener()
        if self.seleccion is nodo:
            self.seleccion = None
        return True

    # ------------------------------------------------------------------
    # Seleccion
    # ------------------------------------------------------------------
    def seleccionar(self, nodo):
        self.seleccion = nodo

    def recorrer_arbol(self):
        """Genera (nodo, nivel) en el orden jerarquico de la lista de NODOS."""
        def visitar(nodo, nivel):
            yield nodo, nivel
            for hijo in nodo.hijos:
                yield from visitar(hijo, nivel + 1)
        for raiz in self.raices():
            yield from visitar(raiz, 0)

    def seleccionar_siguiente(self):
        """Tab: pasa al siguiente nodo, en el orden de la lista de NODOS."""
        nodos = [n for n, _nivel in self.recorrer_arbol()]
        if not nodos:
            return
        if self.seleccion in nodos:
            self.seleccion = nodos[(nodos.index(self.seleccion) + 1) % len(nodos)]
        else:
            self.seleccion = nodos[0]

    def reiniciar_objetos(self):
        """Devuelve objetos y luces a su pose de reposo (la camara no)."""
        for n in self.nodos:
            if n is not self.camara:
                n.reiniciar()

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def configurar_opengl(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_NORMALIZE)           # normales validas aunque haya escala
        glShadeModel(GL_SMOOTH)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.3, 0.3, 0.3, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)

    def dibujar(self, x, y, ancho, alto):
        """Dibuja la escena en el area (x, y, ancho, alto) en pixeles."""
        g = self.global_
        cam = self.camara

        glViewport(x, y, ancho, alto)
        glScissor(x, y, ancho, alto)
        glEnable(GL_SCISSOR_TEST)
        glClearColor(*g.color_fondo, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        cam.aplicar_proyeccion(ancho, alto)
        cam.aplicar_vista()

        if g.dos_caras:
            glDisable(GL_CULL_FACE)
            glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        else:
            glEnable(GL_CULL_FACE)
            glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_FALSE)

        # Rejilla del piso y ejes del mundo (sin iluminacion)
        glDisable(GL_LIGHTING)
        if g.rejilla:
            self._dibujar_rejilla()
            self._dibujar_ejes_mundo()

        # Pasada 1: luces
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [*g.luz_ambiental, 1.0])
        for i in range(MAX_LUCES):
            glDisable(GL_LIGHT0 + i)
        self._luz_indice = 0
        for raiz in self.raices():
            self._pasada_luces(raiz)

        # Pasada 2: objetos, ejes, huesos e iconos
        self._luz_activa = g.modo_vision != "ALAMBRE"
        if self._luz_activa:
            glEnable(GL_LIGHTING)
        else:
            glDisable(GL_LIGHTING)
        for raiz in self.raices():
            self._pasada_dibujo(raiz)

        glDisable(GL_LIGHTING)
        glDisable(GL_SCISSOR_TEST)

    def _pasada_luces(self, nodo):
        if isinstance(nodo, NodeCamera):
            return
        glPushMatrix()
        nodo.aplicar_transformacion()
        if (isinstance(nodo, NodeLight) and nodo.iluminacion
                and self._luz_indice < MAX_LUCES):
            nodo.aplicar(self._luz_indice)
            self._luz_indice += 1
        for hijo in nodo.hijos:
            self._pasada_luces(hijo)
        glPopMatrix()

    def _pasada_dibujo(self, nodo):
        if isinstance(nodo, NodeCamera):
            return
        g = self.global_
        glPushMatrix()
        nodo.aplicar_transformacion()
        seleccionado = self.seleccion is nodo

        if nodo.ejes:
            glDisable(GL_LIGHTING)
            nodo.dibujar_ejes()
            if self._luz_activa:
                glEnable(GL_LIGHTING)

        if isinstance(nodo, NodeObjeto3D):
            nodo.dibujar_geometria(g.modo_vision, seleccionado, self._luz_activa)
            if g.mostrar_huesos and nodo.es_hueso and nodo.visible:
                nodo.dibujar_hueso(self._luz_activa)
        elif isinstance(nodo, NodeLight) and nodo.visible:
            nodo.dibujar_icono(seleccionado)
            if self._luz_activa:
                glEnable(GL_LIGHTING)

        # Los hijos se dibujan dentro del marco local del padre
        for hijo in nodo.hijos:
            self._pasada_dibujo(hijo)
        glPopMatrix()

    def _dibujar_rejilla(self, mitad=10):
        glBegin(GL_LINES)
        for i in range(-mitad, mitad + 1):
            tono = 0.45 if i == 0 else 0.25
            glColor3f(tono, tono, tono)
            glVertex3f(i, 0, -mitad)
            glVertex3f(i, 0, mitad)
            glVertex3f(-mitad, 0, i)
            glVertex3f(mitad, 0, i)
        glEnd()

    def _dibujar_ejes_mundo(self, largo=1.5):
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glColor3f(0.9, 0.2, 0.2); glVertex3f(0, 0, 0); glVertex3f(largo, 0, 0)
        glColor3f(0.2, 0.9, 0.2); glVertex3f(0, 0, 0); glVertex3f(0, largo, 0)
        glColor3f(0.3, 0.4, 0.95); glVertex3f(0, 0, 0); glVertex3f(0, 0, largo)
        glEnd()
        glLineWidth(1.0)
