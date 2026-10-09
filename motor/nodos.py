"""Sistema de nodos del motor.

Cada nodo hereda los parametros del anterior:

    Node                       id, name
    |-- NodeGlobal             ambiente general del espacio (uno solo)
    |-- Node3D                 Location, Rotation, EJES, FotogramasClaves
        |-- NodeObjeto3D       geometria, colores de cara, huesos
        |-- NodeLight          ILUMINACION, Color, Power, Shadow
        |   |-- NodeLightPoint     Radius
        |   |   `-- NodeLightSpot  Radius + Angle
        |   `-- NodeLightSol       (la direccion sale de la Rotation)
        `-- NodeCamera         FOV, modo orbital / libre

Cada clase declara sus parametros en una tabla (PARAMS). Esa misma tabla se
usa para: crear los atributos del nodo, dibujar la interfaz de
NODE CONFIGURACION y guardar/leer los .txt. Agregar un parametro nuevo es
agregar una linea P(...) a la clase que corresponda.
"""
import copy
import math

from OpenGL.GL import *  # noqa: F401,F403


# ======================================================================
# Descripcion de un parametro
# ======================================================================
class P:
    """Un parametro de nodo.

    tipo: "bool" | "int" | "float" | "vec3" | "color" | "opcion" | "texto"
    cuando: funcion(nodo) -> bool; si existe, el parametro solo se muestra
            en la interfaz cuando devuelve True.
    editable: False = la interfaz lo muestra pero no lo cambia.
    ui: False = no aparece en la interfaz (pero se guarda).
    """

    def __init__(self, clave, tipo, etiqueta, defecto=None, paso=0.1,
                 minimo=None, maximo=None, decimales=2, opciones=None,
                 ayuda="", cuando=None, ejes="XYZ", editable=True, ui=True):
        self.clave = clave
        self.tipo = tipo
        self.etiqueta = etiqueta
        self.defecto = defecto
        self.paso = paso
        self.minimo = minimo
        self.maximo = maximo
        self.decimales = decimales
        self.opciones = opciones or []
        self.ayuda = ayuda
        self.cuando = cuando
        self.ejes = ejes
        self.editable = editable
        self.ui = ui

    # ---- texto <-> valor (para los .txt) ----
    def a_texto(self, valor):
        if self.tipo == "bool":
            return "1" if valor else "0"
        if self.tipo == "int":
            return str(int(valor))
        if self.tipo == "float":
            return _num(valor)
        if self.tipo in ("vec3", "color"):
            return " ".join(_num(v) for v in valor)
        return str(valor)

    def de_texto(self, texto):
        texto = texto.strip()
        if self.tipo == "bool":
            return texto.lower() in ("1", "true", "si", "sí", "x", "yes")
        if self.tipo == "int":
            return int(float(texto))
        if self.tipo == "float":
            return float(texto)
        if self.tipo in ("vec3", "color"):
            partes = [float(v) for v in texto.replace(",", " ").split()]
            if len(partes) != 3:
                raise ValueError("se esperaban 3 valores")
            return partes
        return texto


def _num(x):
    """Numero sin notacion cientifica y sin ceros sobrantes."""
    texto = ("%.6f" % x).rstrip("0").rstrip(".")
    return "0" if texto in ("", "-0") else texto


# ======================================================================
# node (basico)
# ======================================================================
class Node:
    TIPO = "node"
    PARAMS = [
        P("name", "texto", "NOMBRE", "", editable=False, ui=False),
    ]

    def __init__(self, nombre="node"):
        self.id = -1                 # lo asigna la escena
        self.padre = None            # referencia al nodo padre (jerarquia)
        self.hijos = []
        self.padre_nombre = ""       # solo se usa al cargar archivos
        for p in self.parametros():
            setattr(self, p.clave, copy.deepcopy(p.defecto))
        self.name = nombre

    @classmethod
    def parametros(cls):
        """Parametros de la clase y de sus clases base (los de la base primero).

        Si una clase redefine un parametro con la misma clave, el nuevo
        reemplaza al anterior pero conserva su lugar en el orden.
        """
        por_clave, orden = {}, []
        for clase in reversed(cls.__mro__):
            for p in clase.__dict__.get("PARAMS", []):
                if p.clave not in por_clave:
                    orden.append(p.clave)
                por_clave[p.clave] = p
        return [por_clave[k] for k in orden]

    def parametros_visibles(self):
        """Parametros que la interfaz debe mostrar para este nodo."""
        return [p for p in self.parametros()
                if p.ui and (p.cuando is None or p.cuando(self))]

    def es_3d(self):
        return isinstance(self, Node3D)


# ======================================================================
# nodeGlobal: ambiente general del espacio
# ======================================================================
class NodeGlobal(Node):
    TIPO = "nodeGlobal"
    PARAMS = [
        P("rejilla", "bool", "REJILLA", True),
        P("modo_vision", "opcion", "MODO DE VISION", "MATERIAL",
          opciones=["ALAMBRE", "SOLIDO", "MATERIAL"]),
        P("limite_fps", "int", "LIMITE FPS", 60, paso=5, minimo=0, maximo=1000,
          decimales=0, ayuda="0 = SIN LIMITE"),
        P("color_fondo", "color", "FONDO", [0.12, 0.13, 0.16]),
        P("luz_ambiental", "color", "LUZ AMBIENTAL", [0.20, 0.20, 0.20]),
        P("mostrar_huesos", "bool", "MOSTRAR HUESOS", True),
        P("dos_caras", "bool", "DOS CARAS", False),
    ]


# ======================================================================
# node3D: tiene lugar en el espacio
# ======================================================================
class Node3D(Node):
    TIPO = "node3D"
    PARAMS = [
        P("visible", "bool", "VISIBLE", True),
        P("ejes", "bool", "EJES", False),
        P("location", "vec3", "LOCATION", [0.0, 0.0, 0.0], paso=0.05),
        P("rotation", "vec3", "ROTATION", [0.0, 0.0, 0.0], paso=1.0, decimales=1),
    ]

    # Parametros de transformacion: en la interfaz van al final, para que los
    # parametros propios de cada tipo (color y power de una luz, por ejemplo)
    # se vean primero sin tener que desplazar el panel.
    CLAVES_TRANSFORMACION = ("visible", "ejes", "location", "rotation")

    def parametros_visibles(self):
        todos = super().parametros_visibles()
        propios = [p for p in todos if p.clave not in self.CLAVES_TRANSFORMACION]
        transformacion = [p for p in todos if p.clave in self.CLAVES_TRANSFORMACION]
        return propios + transformacion

    def __init__(self, nombre="node3D"):
        super().__init__(nombre)
        # Lista de claves de animacion: [(fotograma, {parametro: valor}), ...]
        # Queda vacia hasta que agreguemos el sistema de animacion.
        self.fotogramas_claves = []
        self.location_mundo_inicial = [0.0, 0.0, 0.0]
        self._reposo = None

    def guardar_reposo(self):
        self._reposo = (list(self.location), list(self.rotation))

    def reiniciar(self):
        if self._reposo:
            self.location = list(self._reposo[0])
            self.rotation = list(self._reposo[1])

    def aplicar_transformacion(self):
        """Multiplica la matriz de OpenGL por Location y Rotation."""
        glTranslatef(*self.location)
        glRotatef(self.rotation[2], 0, 0, 1)
        glRotatef(self.rotation[1], 0, 1, 0)
        glRotatef(self.rotation[0], 1, 0, 0)

    def dibujar_ejes(self, largo=1.0):
        """Ejes X (rojo), Y (verde), Z (azul) en el origen del nodo."""
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glColor3f(0.9, 0.2, 0.2); glVertex3f(0, 0, 0); glVertex3f(largo, 0, 0)
        glColor3f(0.2, 0.9, 0.2); glVertex3f(0, 0, 0); glVertex3f(0, largo, 0)
        glColor3f(0.3, 0.4, 0.95); glVertex3f(0, 0, 0); glVertex3f(0, 0, largo)
        glEnd()
        glLineWidth(1.0)


# ======================================================================
# nodeObjeto3D: geometria que se dibuja
# ======================================================================
class NodeObjeto3D(Node3D):
    TIPO = "nodeObjeto3D"
    PARAMS = [
        P("escala", "vec3", "ESCALA", [1.0, 1.0, 1.0], paso=0.05, minimo=0.01),
        P("es_hueso", "bool", "HUESO", False),
        P("apunta_a", "texto", "APUNTA A", "", editable=False),
        P("pivote", "vec3", "PIVOTE", [0.0, 0.0, 0.0], paso=0.02),
    ]

    def __init__(self, nombre="objeto", vertices=None, normales=None,
                 caras=None, uvs=None):
        super().__init__(nombre)
        # Informacion necesaria para dibujar y pintar las caras (coordenadas locales)
        self.vertices = vertices or []   # [(x, y, z)]
        self.normales = normales or []   # [(nx, ny, nz)] una por vertice
        self.caras = caras or []         # [(v1, v2, v3, r, g, b)]
        self.uvs = uvs or []             # [(u, v)] o vacio
        self._lista_geo = None           # display list solo con la forma
        self._lista_color = None         # display list con forma + color por cara
        self._reposo_escala = None

    def guardar_reposo(self):
        super().guardar_reposo()
        self._reposo_escala = list(self.escala)

    def reiniciar(self):
        super().reiniciar()
        if self._reposo_escala:
            self.escala = list(self._reposo_escala)

    def aplicar_transformacion(self):
        """M = T(location) . T(pivote) . Rz.Ry.Rx . S(escala) . T(-pivote)

        El objeto rota y escala alrededor de su pivote; sus hijos se dibujan
        en este mismo marco local.
        """
        px, py, pz = self.pivote
        glTranslatef(*self.location)
        glTranslatef(px, py, pz)
        glRotatef(self.rotation[2], 0, 0, 1)
        glRotatef(self.rotation[1], 0, 1, 0)
        glRotatef(self.rotation[0], 1, 0, 0)
        glScalef(*self.escala)
        glTranslatef(-px, -py, -pz)

    # ------------------------------------------------------------------
    # Dibujo de la geometria
    # ------------------------------------------------------------------
    def _compilar(self):
        """Compila la geometria una sola vez en dos display lists."""
        self.liberar()
        # 1) solo la forma (para alambre, solido y, mas adelante, seleccion)
        self._lista_geo = glGenLists(1)
        glNewList(self._lista_geo, GL_COMPILE)
        glBegin(GL_TRIANGLES)
        for v1, v2, v3, _r, _g, _b in self.caras:
            for i in (v1, v2, v3):
                glNormal3f(*self.normales[i])
                glVertex3f(*self.vertices[i])
        glEnd()
        glEndList()
        # 2) forma + color de cada cara (modo MATERIAL)
        self._lista_color = glGenLists(1)
        glNewList(self._lista_color, GL_COMPILE)
        glBegin(GL_TRIANGLES)
        for v1, v2, v3, r, g, b in self.caras:
            glColor3f(r, g, b)
            for i in (v1, v2, v3):
                glNormal3f(*self.normales[i])
                glVertex3f(*self.vertices[i])
        glEnd()
        glEndList()

    def dibujar_geometria(self, modo, resaltado=False, luz_activa=True):
        """Dibuja segun el MODO DE VISION global (ALAMBRE / SOLIDO / MATERIAL)."""
        if not self.visible:
            return
        if self._lista_geo is None:
            self._compilar()
        if modo == "ALAMBRE":
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glColor3f(0.75, 0.85, 0.95)
            glCallList(self._lista_geo)
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        elif modo == "SOLIDO":
            glColor3f(0.75, 0.75, 0.78)
            glCallList(self._lista_geo)
        else:  # MATERIAL
            glCallList(self._lista_color)
        if resaltado:
            self._dibujar_contorno(luz_activa)

    def _dibujar_contorno(self, luz_activa):
        """Contorno amarillo para ver que nodo esta seleccionado."""
        glDisable(GL_LIGHTING)
        glDepthFunc(GL_LEQUAL)          # las lineas no "parpadean" sobre la cara
        glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        glLineWidth(2.0)
        glColor3f(1.0, 0.9, 0.1)
        glCallList(self._lista_geo)
        glLineWidth(1.0)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glDepthFunc(GL_LESS)
        if luz_activa:
            glEnable(GL_LIGHTING)

    def dibujar_hueso(self, luz_activa=True):
        """Marca el pivote y una linea hacia el objeto al que apunta."""
        glDisable(GL_LIGHTING)
        glDisable(GL_DEPTH_TEST)
        px, py, pz = self.pivote
        glColor3f(1.0, 0.4, 0.1)
        glPointSize(8.0)
        glBegin(GL_POINTS)
        glVertex3f(px, py, pz)
        glEnd()
        destino = next((h for h in self.hijos if h.name == self.apunta_a), None)
        if destino is not None:
            piv = getattr(destino, "pivote", [0.0, 0.0, 0.0])
            glBegin(GL_LINES)
            glVertex3f(px, py, pz)
            glVertex3f(destino.location[0] + piv[0],
                       destino.location[1] + piv[1],
                       destino.location[2] + piv[2])
            glEnd()
        glPointSize(1.0)
        glEnable(GL_DEPTH_TEST)
        if luz_activa:
            glEnable(GL_LIGHTING)

    def liberar(self):
        for atributo in ("_lista_geo", "_lista_color"):
            lista = getattr(self, atributo)
            if lista is not None:
                glDeleteLists(lista, 1)
                setattr(self, atributo, None)


# ======================================================================
# nodeLight: luces (cada una hereda Location y Rotation de node3D)
# ======================================================================
class NodeLight(Node3D):
    """Una luz mira hacia su eje -Z local; la Rotation decide hacia donde."""
    TIPO = "nodeLight"
    PARAMS = [
        P("iluminacion", "bool", "ILUMINACION", True),
        P("color", "color", "COLOR", [1.0, 1.0, 1.0]),
        P("power", "float", "POWER", 1.0, paso=0.05, minimo=0.0, maximo=20.0),
        P("shadow", "bool", "SHADOW", False, ayuda="SOMBRAS: PROXIMAMENTE"),
    ]

    def _difuso(self):
        k = self.power
        return [self.color[0] * k, self.color[1] * k, self.color[2] * k, 1.0]

    def _base(self, luz):
        """Color de la luz; la posicion/direccion cambian segun el tipo."""
        d = self._difuso()
        glEnable(luz)
        glLightfv(luz, GL_DIFFUSE, d)
        glLightfv(luz, GL_SPECULAR, d)
        glLightfv(luz, GL_AMBIENT, [0.0, 0.0, 0.0, 1.0])
        glLightf(luz, GL_CONSTANT_ATTENUATION, 1.0)
        glLightf(luz, GL_LINEAR_ATTENUATION, 0.0)
        glLightf(luz, GL_QUADRATIC_ATTENUATION, 0.0)
        glLightf(luz, GL_SPOT_CUTOFF, 180.0)

    def aplicar(self, indice):
        """Configura GL_LIGHT<indice>. Se llama con la matriz del nodo ya aplicada,
        asi OpenGL transforma la posicion y la direccion por nosotros."""
        raise NotImplementedError

    def dibujar_icono(self, resaltado=False):
        raise NotImplementedError

    def _color_icono(self, resaltado):
        glColor3f(*(1.0, 0.9, 0.1) if resaltado else tuple(self.color))


class NodeLightPoint(NodeLight):
    """Luz puntual (bombilla). Radius = hasta donde ilumina."""
    TIPO = "nodeLightPoint"
    PARAMS = [
        P("radius", "float", "RADIUS (M)", 10.0, paso=0.5, minimo=0.1, maximo=500.0),
    ]

    def _atenuacion(self):
        """Radius -> atenuacion de OpenGL: la luz baja al 5% en el radio."""
        r = max(0.1, self.radius)
        return 19.0 / (r * r)

    def aplicar(self, indice):
        luz = GL_LIGHT0 + indice
        self._base(luz)
        glLightfv(luz, GL_POSITION, [0.0, 0.0, 0.0, 1.0])
        glLightf(luz, GL_QUADRATIC_ATTENUATION, self._atenuacion())

    def dibujar_icono(self, resaltado=False):
        glDisable(GL_LIGHTING)
        self._color_icono(resaltado)
        glPointSize(9.0 if resaltado else 6.0)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPointSize(1.0)
        if resaltado:
            _circulo(0, self.radius)
            _circulo(1, self.radius)
            _circulo(2, self.radius)


class NodeLightSol(NodeLight):
    """Luz de sol: solo importa hacia donde mira (Rotation)."""
    TIPO = "nodeLightSol"
    PARAMS = []

    def aplicar(self, indice):
        luz = GL_LIGHT0 + indice
        self._base(luz)
        # w = 0 -> es una direccion: (0, 0, 1) apunta HACIA la luz,
        # asi que la luz viaja hacia -Z (hacia donde mira el nodo).
        glLightfv(luz, GL_POSITION, [0.0, 0.0, 1.0, 0.0])

    def dibujar_icono(self, resaltado=False):
        glDisable(GL_LIGHTING)
        self._color_icono(resaltado)
        glPointSize(9.0 if resaltado else 6.0)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPointSize(1.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, -1.5)
        glVertex3f(0, 0, -1.5)
        glVertex3f(0.1, 0, -1.3)
        glVertex3f(0, 0, -1.5)
        glVertex3f(-0.1, 0, -1.3)
        glEnd()


class NodeLightSpot(NodeLightPoint):
    """Foco (linterna): Radius y Angle (apertura del cono)."""
    TIPO = "nodeLightSpot"
    PARAMS = [
        P("angle", "float", "ANGLE", 40.0, paso=1.0, minimo=1.0, maximo=90.0,
          decimales=0),
        P("concentracion", "float", "CONCENTRAC.", 10.0, paso=1.0, minimo=0.0,
          maximo=128.0, decimales=0),
    ]

    def aplicar(self, indice):
        luz = GL_LIGHT0 + indice
        self._base(luz)
        glLightfv(luz, GL_POSITION, [0.0, 0.0, 0.0, 1.0])
        glLightf(luz, GL_QUADRATIC_ATTENUATION, self._atenuacion())
        glLightfv(luz, GL_SPOT_DIRECTION, [0.0, 0.0, -1.0])
        glLightf(luz, GL_SPOT_CUTOFF, max(1.0, min(90.0, self.angle)))
        glLightf(luz, GL_SPOT_EXPONENT, max(0.0, min(128.0, self.concentracion)))

    def dibujar_icono(self, resaltado=False):
        glDisable(GL_LIGHTING)
        self._color_icono(resaltado)
        glPointSize(9.0 if resaltado else 6.0)
        glBegin(GL_POINTS)
        glVertex3f(0, 0, 0)
        glEnd()
        glPointSize(1.0)
        # Cono: 4 aristas y un circulo a 2 m (o al radio, si es menor)
        d = min(2.0, self.radius)
        r = d * math.tan(math.radians(max(1.0, min(89.0, self.angle))))
        glBegin(GL_LINES)
        for a in (0.0, 90.0, 180.0, 270.0):
            glVertex3f(0, 0, 0)
            glVertex3f(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), -d)
        glEnd()
        glBegin(GL_LINE_LOOP)
        for k in range(24):
            a = 2 * math.pi * k / 24
            glVertex3f(r * math.cos(a), r * math.sin(a), -d)
        glEnd()


def _circulo(eje, radio, segmentos=32):
    """Circulo de un radio en un plano (0 = YZ, 1 = XZ, 2 = XY)."""
    glBegin(GL_LINE_LOOP)
    for k in range(segmentos):
        a = 2 * math.pi * k / segmentos
        c, s = radio * math.cos(a), radio * math.sin(a)
        if eje == 0:
            glVertex3f(0, c, s)
        elif eje == 1:
            glVertex3f(c, 0, s)
        else:
            glVertex3f(c, s, 0)
    glEnd()


# ======================================================================
# nodeCamera: la camara tambien es un nodo
# ======================================================================
class NodeCamera(Node3D):
    """Camara con dos modos:
      orbital -> gira alrededor de un punto (objetivo, distancia, yaw, pitch)
      libre   -> usa su Location y su Rotation (X = pitch, Y = yaw, Z = giro)
    """
    TIPO = "nodeCamera"
    PARAMS = [
        # La camara no se oculta ni lleva ejes
        P("visible", "bool", "VISIBLE", True, ui=False),
        P("ejes", "bool", "EJES", False, ui=False),
        P("modo", "opcion", "MODO", "orbital", opciones=["orbital", "libre"]),
        P("fov", "float", "FOV", 50.0, paso=1.0, minimo=10.0, maximo=120.0, decimales=0),
        P("ortografica", "bool", "ORTOGRAFICA", False),
        P("cerca", "float", "CERCA", 0.1, paso=0.05, minimo=0.01, maximo=10.0),
        P("lejos", "float", "LEJOS", 200.0, paso=5.0, minimo=10.0, maximo=2000.0,
          decimales=0),
        P("sensibilidad", "float", "SENSIBILIDAD", 0.3, paso=0.05, minimo=0.05,
          maximo=1.0),
        # Orbital
        P("objetivo", "vec3", "OBJETIVO", [0.0, 1.0, 0.0], paso=0.1,
          cuando=lambda n: n.modo == "orbital"),
        P("distancia", "float", "DISTANCIA", 8.0, paso=0.2, minimo=0.3, maximo=500.0,
          cuando=lambda n: n.modo == "orbital"),
        P("yaw", "float", "YAW", 30.0, paso=1.0, decimales=1,
          cuando=lambda n: n.modo == "orbital"),
        P("pitch", "float", "PITCH", 20.0, paso=1.0, minimo=-89.0, maximo=89.0,
          decimales=1, cuando=lambda n: n.modo == "orbital"),
        # Libre (Location y Rotation, heredadas de node3D, solo en este modo)
        P("location", "vec3", "LOCATION", [0.0, 2.0, 8.0], paso=0.1,
          cuando=lambda n: n.modo == "libre"),
        P("rotation", "vec3", "ROTATION", [0.0, 0.0, 0.0], paso=1.0, decimales=1,
          cuando=lambda n: n.modo == "libre"),
        P("velocidad", "float", "VELOCIDAD", 4.0, paso=0.5, minimo=0.5, maximo=30.0,
          decimales=1, cuando=lambda n: n.modo == "libre"),
    ]

    # ------------------------------------------------------------------
    # Entrada (la usa motor/entrada.py)
    # ------------------------------------------------------------------
    def orbitar(self, dx, dy):
        self.yaw -= dx * self.sensibilidad
        self.pitch = max(-89.0, min(89.0, self.pitch + dy * self.sensibilidad))

    def acercar(self, delta):
        self.distancia = max(0.3, self.distancia * (0.9 ** delta))

    def desplazar_objetivo(self, dx, dy):
        """Mueve el punto objetivo en el plano de la pantalla (orbital)."""
        derecha, arriba = self._ejes_orbital()
        k = self.distancia * 0.0015
        for i in range(3):
            self.objetivo[i] += (-derecha[i] * dx + arriba[i] * dy) * k

    def mirar(self, dx, dy):
        self.rotation[1] -= dx * self.sensibilidad
        self.rotation[0] = max(-89.0, min(89.0, self.rotation[0] - dy * self.sensibilidad))

    def mover_libre(self, adelante, derecha, arriba, dt):
        f, r = self._vectores_libre()
        v = self.velocidad * dt
        for i in range(3):
            self.location[i] += (f[i] * adelante + r[i] * derecha) * v
        self.location[1] += arriba * v

    # ------------------------------------------------------------------
    # Cambio de modo conservando la vista actual
    # ------------------------------------------------------------------
    def cambiar_modo(self, modo):
        if modo == self.modo:
            return
        if modo == "libre":
            self.location = list(self._posicion_orbital())
            self.rotation = [-self.pitch, self.yaw, 0.0]
        else:
            f, _ = self._vectores_libre()
            self.objetivo = [self.location[i] + f[i] * self.distancia for i in range(3)]
            self.yaw = self.rotation[1]
            self.pitch = -self.rotation[0]
        self.modo = modo

    def vista_rapida(self, nombre):
        self.cambiar_modo("orbital")
        angulos = {"frontal": (0.0, 0.0), "lateral": (90.0, 0.0),
                   "superior": (0.0, 89.0), "trasera": (180.0, 0.0)}
        if nombre in angulos:
            self.yaw, self.pitch = angulos[nombre]

    # ------------------------------------------------------------------
    # Geometria auxiliar
    # ------------------------------------------------------------------
    def _posicion_orbital(self):
        y, p = math.radians(self.yaw), math.radians(self.pitch)
        return (self.objetivo[0] + self.distancia * math.cos(p) * math.sin(y),
                self.objetivo[1] + self.distancia * math.sin(p),
                self.objetivo[2] + self.distancia * math.cos(p) * math.cos(y))

    def _ejes_orbital(self):
        y, p = math.radians(self.yaw), math.radians(self.pitch)
        derecha = (math.cos(y), 0.0, -math.sin(y))
        arriba = (-math.sin(p) * math.sin(y), math.cos(p), -math.sin(p) * math.cos(y))
        return derecha, arriba

    def _vectores_libre(self):
        y, p = math.radians(self.rotation[1]), math.radians(self.rotation[0])
        adelante = (-math.cos(p) * math.sin(y), math.sin(p), -math.cos(p) * math.cos(y))
        derecha = (math.cos(y), 0.0, -math.sin(y))
        return adelante, derecha

    def posicion_actual(self):
        return self._posicion_orbital() if self.modo == "orbital" else tuple(self.location)

    # ------------------------------------------------------------------
    # Aplicar a OpenGL (solo GL, sin GLU)
    # ------------------------------------------------------------------
    def aplicar_proyeccion(self, ancho, alto):
        aspecto = ancho / max(1, alto)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        if self.ortografica:
            alto_v = self.distancia * math.tan(math.radians(self.fov / 2))
            glOrtho(-alto_v * aspecto, alto_v * aspecto, -alto_v, alto_v,
                    -self.lejos, self.lejos)
        else:
            top = self.cerca * math.tan(math.radians(self.fov / 2))
            glFrustum(-top * aspecto, top * aspecto, -top, top, self.cerca, self.lejos)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def aplicar_vista(self):
        """Deja en GL_MODELVIEW la matriz de vista (tras glLoadIdentity)."""
        if self.modo == "orbital":
            glTranslatef(0.0, 0.0, -self.distancia)
            glRotatef(self.pitch, 1, 0, 0)
            glRotatef(-self.yaw, 0, 1, 0)
            glTranslatef(-self.objetivo[0], -self.objetivo[1], -self.objetivo[2])
        else:
            glRotatef(-self.rotation[2], 0, 0, 1)
            glRotatef(-self.rotation[0], 1, 0, 0)
            glRotatef(-self.rotation[1], 0, 1, 0)
            glTranslatef(-self.location[0], -self.location[1], -self.location[2])


# ======================================================================
# Registro de tipos (para leer los .txt)
# ======================================================================
TIPOS = {c.TIPO: c for c in (
    Node, NodeGlobal, Node3D, NodeObjeto3D, NodeLight,
    NodeLightPoint, NodeLightSol, NodeLightSpot, NodeCamera)}
TIPOS["nodeGobal"] = NodeGlobal      # alias del nombre tal como lo escribiste

TIPOS_LUZ = ["nodeLightPoint", "nodeLightSol", "nodeLightSpot"]
MAX_LUCES = 8


def crear_nodo(tipo, nombre):
    """Crea un nodo a partir del nombre de su tipo (None si no existe)."""
    clase = TIPOS.get(tipo)
    return clase(nombre) if clase else None
