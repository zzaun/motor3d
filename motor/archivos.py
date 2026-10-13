"""
Lectura y escritura de los .txt del motor (Python puro, sin pandas).

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
    [vertices]
    x y z

Los nodos se relacionan por NOMBRE (campo padre = nombre del padre).
"""

import os

from .nodos import (
    TIPOS,
    NodeGlobal,
    NodeCamera,
    NodeObjeto3D,
    crear_nodo,
)

# Encabezado esperado para archivos de objetos
ENCABEZADO_OBJETO = "# motor3d objeto v1"
# Encabezado esperado para archivos de escena
ENCABEZADO_ESCENA = "# motor3d escena v1"

# Lee archivos de texto con bloques [nodo] y secciones de datos
def leer_txt(ruta):
    """    Devuelve (bloques_nodo, secciones).
    bloques_nodo: lista de dict {clave: texto}.
    secciones: dict {nombre: filas}.
    """
    # Almacena todos los bloques de nodos leidos
    bloques = []
    # Almacena las secciones de datos encontradas
    secciones = {}
    # Referencia al bloque o seccion actualmente activa
    actual = None
    # Abre el archivo en modo lectura
    with open(ruta, "r", encoding="utf-8") as f:
        # Procesa cada linea del archivo
        for linea in f:
            # Elimina espacios y saltos de linea
            linea = linea.strip()
            # Ignora lineas vacias y comentarios
            if not linea or linea.startswith("#"):
                continue
            # Detecta el inicio de una nueva seccion
            if linea.startswith("[") and linea.endswith("]"):
                # Obtiene el nombre de la seccion
                nombre = linea[1:-1].strip().lower()
                # Crea un nuevo bloque de nodo
                if nombre == "nodo":
                    actual = {}
                    bloques.append(actual)
                # Crea o reutiliza una seccion de datos
                else:
                    actual = secciones.setdefault(nombre, [])

                continue
            # Procesa pares clave = valor dentro de un nodo
            if isinstance(actual, dict):
                if "=" in linea:
                    clave, valor = linea.split("=", 1)
                    actual[clave.strip().lower()] = valor.strip()
            # Procesa filas numericas dentro de una seccion
            elif isinstance(actual, list):
                actual.append(linea.split())
    return bloques, secciones

# Copia al nodo los parametros definidos en el bloque
def aplicar_parametros(nodo, bloque, ruta=""):
    # Recorre todos los parametros del nodo
    for p in nodo.parametros():
        # Ignora nombres y parametros inexistentes
        if p.clave in bloque and p.clave != "name":
            try:
                # Convierte texto al tipo esperado y lo asigna
                setattr(
                    nodo,
                    p.clave,
                    p.de_texto(bloque[p.clave]),
                )

            # Informa valores invalidos sin detener la carga
            except (ValueError, TypeError) as e:
                print(
                    f"  aviso: {os.path.basename(ruta)}: valor invalido en "
                    f"'{p.clave}' del nodo '{nodo.name}' ({e})"
                )


# Lee un archivo de objeto y construye un NodeObjeto3D
def leer_objeto(ruta):
    # Obtiene bloques y secciones del archivo
    bloques, secciones = leer_txt(ruta)
    # Busca el bloque principal del objeto
    bloque = next(
        (
            b for b in bloques
            if b.get("tipo", "") in ("nodeObjeto3D",)
        ),
        None,
    )

    # Verifica que exista un nodo de objeto valido
    if bloque is None:
        raise ValueError(
            "no tiene un [nodo] de tipo nodeObjeto3D"
        )

    # Verifica que existan las secciones obligatorias
    for requerida in ("vertices", "normales", "caras"):

        if requerida not in secciones:
            raise ValueError(
                f"falta la seccion [{requerida}]"
            )

    # Convierte vertices a tuplas de flotantes
    vertices = [
        tuple(float(c) for c in fila[:3])
        for fila in secciones["vertices"]
    ]

    # Convierte normales a tuplas de flotantes
    normales = [
        tuple(float(c) for c in fila[:3])
        for fila in secciones["normales"]
    ]

    # Convierte caras a indices y coordenadas UV
    caras = [
        (
            int(fila[0]),
            int(fila[1]),
            int(fila[2]),
            float(fila[3]),
            float(fila[4]),
            float(fila[5]),
        )
        for fila in secciones["caras"]
    ]

    # Carga UVs si estan presentes
    uvs = [
        tuple(float(c) for c in fila[:2])
        for fila in secciones.get("uvs", [])
    ]

    # Verifica correspondencia entre vertices y normales
    if len(vertices) != len(normales):
        raise ValueError(
            "vertices y normales no tienen la misma longitud"
        )

    # Obtiene la cantidad total de vertices
    n = len(vertices)

    # Verifica que las caras usen indices validos
    for c in caras:

        if (
            min(c[0], c[1], c[2]) < 0
            or
            max(c[0], c[1], c[2]) >= n
        ):
            raise ValueError(
                "una cara usa un indice de vertice inexistente"
            )

    # Usa el nombre guardado o el nombre del archivo
    nombre = (
        bloque.get("name")
        or
        os.path.splitext(
            os.path.basename(ruta)
        )[0]
    )

    # Crea el nodo con la geometria cargada
    nodo = NodeObjeto3D(
        nombre,
        vertices,
        normales,
        caras,
        uvs,
    )
    # Aplica propiedades adicionales del archivo
    aplicar_parametros(nodo, bloque, ruta)
    # Conserva el nombre del padre para enlazar despues
    nodo.padre_nombre = bloque.get("padre", "")
    # Guarda la posicion inicial del objeto
    nodo.location_mundo_inicial = list(nodo.location)
    return nodo

# Agrega un nodo a la lista de texto de la escena
def _escribir_bloque(lineas, nodo):
    # Marca el inicio de un bloque de nodo
    lineas.append("[nodo]")
    # Guarda el tipo del nodo
    lineas.append("tipo = " + nodo.TIPO)
    # Guarda el identificador unico
    lineas.append("id = %d" % nodo.id)
    # Guarda el nombre del nodo
    lineas.append("name = " + nodo.name)

    # Guarda la relacion padre-hijo para nodos 3D
    if nodo.es_3d():
        lineas.append(
            "padre = " +
            (nodo.padre.name if nodo.padre else "")
        )
    # Guarda todos los parametros serializables
    for p in nodo.parametros():
        if p.clave == "name":
            continue
        lineas.append(
            "%s = %s"
            %
            (
                p.clave,
                p.a_texto(
                    getattr(
                        nodo,
                        p.clave,
                    )
                ),
            )
        )
    # Las animaciones se guardaran cuando el sistema exista

# Guarda el estado completo de la escena
def guardar_escena(ruta, escena):
    # Crea el contenido base del archivo
    lineas = [
        ENCABEZADO_ESCENA,
        "# Estado de la escena guardado desde el motor (boton GUARDAR).",
        "# La geometria de los objetos sigue en objetos3d/*.txt.",
    ]
    # Guarda la configuracion global
    _escribir_bloque(lineas, escena.global_)
    # Guarda todos los nodos de la escena
    for nodo in escena.nodos:
        _escribir_bloque(lineas, nodo)
    # Obtiene el directorio destino
    carpeta = os.path.dirname(ruta)
    # Crea la carpeta si no existe
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    # Escribe el archivo de escena
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


# Aplica una escena guardada sobre la escena actual
def cargar_escena(ruta, escena):
    # Lee todos los bloques de la escena
    bloques, _ = leer_txt(ruta)
    # Permite localizar nodos por nombre
    por_nombre = {
        n.name: n
        for n in escena.nodos
    }
    # Almacena relaciones padre-hijo pendientes
    padres = {}
    # Controla ids ya utilizados
    ids_usados = {0}

    # Procesa cada bloque leido
    for b in bloques:
        # Obtiene el tipo y nombre del nodo
        tipo = b.get("tipo", "")
        nombre = b.get("name", "")
        # Busca la clase correspondiente
        clase = TIPOS.get(tipo)

        # Ignora tipos desconocidos
        if clase is None:
            print(
                f"  aviso: tipo de nodo desconocido en escena.txt: '{tipo}'"
            )
            continue
        # Actualiza la configuracion global
        if clase is NodeGlobal:
            aplicar_parametros(
                escena.global_,
                b,
                ruta,
            )
            continue
        # Indica si el nodo fue creado durante la carga
        nuevo = False

        # Reutiliza la camara existente
        if clase is NodeCamera:
            nodo = escena.camara

        # Busca el objeto previamente cargado
        elif clase is NodeObjeto3D:
            nodo = por_nombre.get(nombre)
            # Ignora referencias a objetos inexistentes
            if nodo is None:
                print(
                    f"  aviso: escena.txt menciona el objeto '{nombre}', "
                    f"pero no existe su .txt en objetos3d/"
                )
                continue

        # Crea nodos auxiliares como luces u otros tipos
        else:
            nodo = crear_nodo(
                tipo,
                nombre or tipo,
            )

            escena.agregar(nodo)
            por_nombre[nodo.name] = nodo
            nuevo = True
        # Aplica parametros guardados
        aplicar_parametros(nodo, b, ruta)

        # Usa la transformacion cargada como pose inicial
        if nuevo:
            nodo.guardar_reposo()
        # Guarda la jerarquia para reconstruir despues
        if nodo.es_3d():
            padres[nodo] = b.get("padre", "")

        # Recupera el id guardado si esta disponible
        try:
            nuevo_id = int(
                b.get("id", "-1")
            )

        except ValueError:
            nuevo_id = -1
        # Conserva ids validos sin colisiones
        if (
            nuevo_id > 0
            and
            nuevo_id not in ids_usados
        ):
            nodo.id = nuevo_id
        ids_usados.add(nodo.id)

    # Reconstruye la jerarquia de la escena
    for nodo, nombre_padre in padres.items():

        # La camara no participa en la jerarquia
        if isinstance(nodo, NodeCamera):
            continue

        # Busca el padre correspondiente
        padre = (
            por_nombre.get(nombre_padre)
            if nombre_padre
            else None
        )
        # Establece la relacion padre-hijo
        escena.enlazar(nodo, padre)
    # Reorganiza