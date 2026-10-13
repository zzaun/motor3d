#   preparar_objetos3d: lee los .txt de la carpeta objetos3d/ y crea los nodeObjeto3D de la escena. Cada .txt es un objeto.
#   Despues enlaza la jerarquia segun el encabezado de cada objeto:
#   - Si un objeto tiene 'padre', ese es su padre.
#   - Si un hueso tiene 'apunta_a' y el objeto apuntado no tiene padre explicito, el hueso pasa a ser su padre.
#   La posicion de un hijo pasa a ser relativa a su padre (la pose de reposo sigue siendo la del modelo original).

import os

from .archivos import leer_objeto


def preparar_objetos3d(carpeta, escena):
    """Carga todos los .txt de la carpeta en la escena. Devuelve la lista."""
    objetos = []
    if not os.path.isdir(carpeta):
        print(f"No existe la carpeta de objetos: {carpeta}")
        return objetos

    for archivo in sorted(os.listdir(carpeta)):
        if not archivo.lower().endswith(".txt"):
            continue
        ruta = os.path.join(carpeta, archivo)
        try:
            nodo = leer_objeto(ruta)
        except Exception as e:
            print(f"  aviso: no se pudo leer {archivo}: {e}")
            continue
        objetos.append(escena.agregar(nodo))

    resolver_jerarquia(escena, objetos)
    print(f"{len(objetos)} objeto(s) cargados de {carpeta}")
    return objetos


def resolver_jerarquia(escena, objetos):
    por_nombre = {o.name: o for o in objetos}

    # 1) 'apunta_a' implica una relacion padre -> hijo
    for o in objetos:
        if o.apunta_a:
            destino = por_nombre.get(o.apunta_a)
            if destino is None:
                print(f"  aviso: '{o.name}' apunta a '{o.apunta_a}', que no existe")
            elif destino is o:
                print(f"  aviso: '{o.name}' apunta a si mismo, se ignora")
            elif not destino.padre_nombre:
                destino.padre_nombre = o.name

    # 2) Enlazar
    for o in objetos:
        if not o.padre_nombre:
            continue
        padre = por_nombre.get(o.padre_nombre)
        if padre is None:
            print(f"  aviso: el padre '{o.padre_nombre}' de '{o.name}' no existe")
            continue
        escena.enlazar(o, padre)

    # 3) Posiciones locales (relativas al padre) y pose de reposo
    for o in objetos:
        mundo = o.location_mundo_inicial
        if o.padre is not None and hasattr(o.padre, "location_mundo_inicial"):
            pm = o.padre.location_mundo_inicial
            o.location = [mundo[0] - pm[0], mundo[1] - pm[1], mundo[2] - pm[2]]
        else:
            o.location = list(mundo)
        o.guardar_reposo()
