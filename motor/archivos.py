"""Lectura y escritura de los .txt del motor (Python puro, sin pandas).

Dos tipos de archivo, con el mismo formato:

  objetos3d/<objeto>.txt   lo genera obj_a_cordenas: encabezado [nodo] con la
                           informacion del nodo + la geometria del objeto.
  escena.txt               lo escribe el boton GUARDAR: un bloque [nodo] por
                           cada nodo de la escena (global, camara, luces,
                           objetos) con sus parametros actuales.

Formato:
    # comentario
    [nodo]
    clave = valor
    [vertices]          <- secciones de datos: una fila de numeros por linea
    x y z

Los nodos se relacionan por NOMBRE (campo padre = nombre del padre).
"""
import os

from .nodos import (TIPOS, NodeGlobal, NodeCamera, NodeObjeto3D, crear_nodo)

ENCABEZADO_OBJETO = "# motor3d objeto v1"
ENCABEZADO_ESCENA = "# motor3d escena v1"


# ======================================================================
# Lectura generica
# ======================================================================
def leer_txt(ruta):
    """Devuelve (bloques_nodo, secciones).

    bloques_nodo: lista de dict {clave: texto} (uno por cada [nodo]).
    secciones: dict {nombre: [lista de filas, cada fila = lista de textos]}.
    """
    bloques, secciones = [], {}
    actual = None          # None | dict (bloque nodo) | list (seccion de datos)
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if linea.startswith("[") and linea.endswith("]"):
                nombre = linea[1:-1].strip().lower()
                if nombre == "nodo":
                    actual = {}
                    bloques.append(actual)
                else:
                    actual = secciones.setdefault(nombre, [])
                continue
            if isinstance(actual, dict):
                if "=" in linea:
                    clave, valor = linea.split("=", 1)
                    actual[clave.strip().lower()] = valor.strip()
            elif isinstance(actual, list):
                actual.append(linea.split())
    return bloques, secciones


def aplicar_parametros(nodo, bloque, ruta=""):
    """Copia al nodo los valores del bloque que correspondan a sus parametros."""
    for p in nodo.parametros():
        if p.clave in bloque and p.clave != "name":
            try:
                setattr(nodo, p.clave, p.de_texto(bloque[p.clave]))
            except (ValueError, TypeError) as e:
                print(f"  aviso: {os.path.basename(ruta)}: valor invalido en "
                      f"'{p.clave}' del nodo '{nodo.name}' ({e})")


# ======================================================================
# Objetos (.txt generados por el conversor)
# ======================================================================
def leer_objeto(ruta):
    """Lee un objeto3D y devuelve su NodeObjeto3D (o lanza ValueError)."""
    bloques, secciones = leer_txt(ruta)
    bloque = next((b for b in bloques
                   if b.get("tipo", "") in ("nodeObjeto3D",)), None)
    if bloque is None:
        raise ValueError("no tiene un [nodo] de tipo nodeObjeto3D")
    for requerida in ("vertices", "normales", "caras"):
        if requerida not in secciones:
            raise ValueError(f"falta la seccion [{requerida}]")

    vertices = [tuple(float(c) for c in fila[:3]) for fila in secciones["vertices"]]
    normales = [tuple(float(c) for c in fila[:3]) for fila in secciones["normales"]]
    caras = [(int(fila[0]), int(fila[1]), int(fila[2]),
              float(fila[3]), float(fila[4]), float(fila[5]))
             for fila in secciones["caras"]]
    uvs = [tuple(float(c) for c in fila[:2]) for fila in secciones.get("uvs", [])]

    if len(vertices) != len(normales):
        raise ValueError("vertices y normales no tienen la misma longitud")
    n = len(vertices)
    for c in caras:
        if min(c[0], c[1], c[2]) < 0 or max(c[0], c[1], c[2]) >= n:
            raise ValueError("una cara usa un indice de vertice inexistente")

    nombre = bloque.get("name") or os.path.splitext(os.path.basename(ruta))[0]
    nodo = NodeObjeto3D(nombre, vertices, normales, caras, uvs)
    aplicar_parametros(nodo, bloque, ruta)
    nodo.padre_nombre = bloque.get("padre", "")
    nodo.location_mundo_inicial = list(nodo.location)
    return nodo


# ======================================================================
# Escena (.txt escrito por GUARDAR)
# ======================================================================
def _escribir_bloque(lineas, nodo):
    lineas.append("[nodo]")
    lineas.append("tipo = " + nodo.TIPO)
    lineas.append("id = %d" % nodo.id)
    lineas.append("name = " + nodo.name)
    if nodo.es_3d():
        lineas.append("padre = " + (nodo.padre.name if nodo.padre else ""))
    for p in nodo.parametros():
        if p.clave == "name":
            continue
        lineas.append("%s = %s" % (p.clave, p.a_texto(getattr(nodo, p.clave))))
    # fotogramas_claves: se guardaran cuando exista el sistema de animacion


def guardar_escena(ruta, escena):
    """Guarda la configuracion actual (global, camara, luces y objetos)."""
    lineas = [ENCABEZADO_ESCENA,
              "# Estado de la escena guardado desde el motor (boton GUARDAR).",
              "# La geometria de los objetos sigue en objetos3d/*.txt."]
    _escribir_bloque(lineas, escena.global_)
    for nodo in escena.nodos:
        _escribir_bloque(lineas, nodo)
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def cargar_escena(ruta, escena):
    """Aplica un escena.txt sobre la escena (los objetos ya estan cargados)."""
    bloques, _ = leer_txt(ruta)
    por_nombre = {n.name: n for n in escena.nodos}
    padres = {}                      # nodo -> nombre del padre guardado
    ids_usados = {0}

    for b in bloques:
        tipo = b.get("tipo", "")
        nombre = b.get("name", "")
        clase = TIPOS.get(tipo)
        if clase is None:
            print(f"  aviso: tipo de nodo desconocido en escena.txt: '{tipo}'")
            continue

        if clase is NodeGlobal:
            aplicar_parametros(escena.global_, b, ruta)
            continue

        nuevo = False

        if clase is NodeCamera:
            nodo = escena.camara
        elif clase is NodeObjeto3D:
            nodo = por_nombre.get(nombre)
            if nodo is None:
                print(f"  aviso: escena.txt menciona el objeto '{nombre}', "
                      f"pero no existe su .txt en objetos3d/")
                continue
        else:
            nodo = crear_nodo(tipo, nombre or tipo)
            escena.agregar(nodo)
            por_nombre[nodo.name] = nodo
            nuevo = True

        aplicar_parametros(nodo, b, ruta)
        if nuevo:
            nodo.guardar_reposo()   # su pose de reposo es la guardada
        if nodo.es_3d():
            padres[nodo] = b.get("padre", "")

        # Conserva el id guardado si no choca con otro
        try:
            nuevo_id = int(b.get("id", "-1"))
        except ValueError:
            nuevo_id = -1
        if nuevo_id > 0 and nuevo_id not in ids_usados:
            nodo.id = nuevo_id
        ids_usados.add(nodo.id)

    # Jerarquia guardada (reemplaza a la de los encabezados de los objetos)
    for nodo, nombre_padre in padres.items():
        if isinstance(nodo, NodeCamera):
            continue
        padre = por_nombre.get(nombre_padre) if nombre_padre else None
        escena.enlazar(nodo, padre)
    escena.normalizar_ids()
