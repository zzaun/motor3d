"""Fuente de pixeles 5x7 propia (no usa GLUT), basada en tu ejemplo.

Cada letra son 7 filas de 5 columnas:
  "#" = pixel encendido, "." = pixel apagado.

Cambios respecto al ejemplo:
  - Se agregaron todas las letras, los numeros y algunos simbolos.
  - El texto se pasa a MAYUSCULAS y se quitan los acentos antes de dibujar
    (la fuente solo tiene mayusculas sin acento).
  - Cada letra se compila UNA vez en una display list de OpenGL. Asi dibujar
    un texto es solo llamar a esas listas, en vez de mandar miles de
    glVertex2f en cada cuadro (en Python eso seria muy lento).
"""
import unicodedata

from OpenGL.GL import *

FUENTE = {
    # ---------------- Letras ----------------
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".####", "#....", "#....", "#....", "#....", "#....", ".####"],
    "D": ["####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "J": ["..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."],
    "K": ["#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"],
    "L": ["#....", "#....", "#....", "#....", "#....", "#....", "#####"],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "Q": [".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "U": ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "W": ["#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"],
    "X": ["#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"],
    "Y": ["#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."],
    "Z": ["#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"],

    # ---------------- Numeros ----------------
    "0": [".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."],
    "1": ["..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."],
    "2": [".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"],
    "3": ["#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."],
    "4": ["...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."],
    "5": ["#####", "#....", "####.", "....#", "....#", "#...#", ".###."],
    "6": ["..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."],
    "7": ["#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."],
    "8": [".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."],
    "9": [".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."],

    # ---------------- Simbolos ----------------
    "-": [".....", ".....", ".....", "#####", ".....", ".....", "....."],
    "+": [".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".##..", ".##.."],
    ",": [".....", ".....", ".....", ".....", ".##..", "..#..", ".#..."],
    ":": [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."],
    "/": ["....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."],
    "(": ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."],
    ")": [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."],
    "[": [".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."],
    "]": [".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."],
    "%": ["##..#", "##..#", "...#.", "..#..", ".#...", "#..##", "#..##"],
    "_": [".....", ".....", ".....", ".....", ".....", ".....", "#####"],
    "=": [".....", ".....", "#####", ".....", "#####", ".....", "....."],
    ">": ["#....", ".#...", "..#..", "...#.", "..#..", ".#...", "#...."],
    "<": ["...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."],
    "*": [".....", "#.#.#", ".###.", "#####", ".###.", "#.#.#", "....."],
    "!": ["..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."],
    "?": [".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."],
}

# Una display list por (letra, escala); se crean la primera vez que se usan
_listas = {}


def normalizar(texto):
    """Pasa a mayusculas y quita acentos (la fuente no los tiene)."""
    descompuesto = unicodedata.normalize("NFD", str(texto).upper())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def ancho_texto(texto, escala=2):
    """Ancho en pixeles: 5 columnas + 1 de separacion por letra, sin la ultima."""
    n = len(texto)
    return max(0, n * 6 * escala - escala)


def _lista_de_letra(letra, escala):
    """Devuelve la display list de una letra, creandola si hace falta."""
    clave = (letra, escala)
    if clave not in _listas:
        lista = glGenLists(1)
        glNewList(lista, GL_COMPILE)
        filas = FUENTE.get(letra)
        # Si la letra no existe (por ejemplo un espacio) solo se avanza
        if filas:
            glBegin(GL_QUADS)
            for r, fila in enumerate(filas):
                for c, p in enumerate(fila):
                    # Solo dibujamos los pixeles encendidos
                    if p == "#":
                        px, py = c * escala, r * escala
                        glVertex2f(px, py)
                        glVertex2f(px + escala, py)
                        glVertex2f(px + escala, py + escala)
                        glVertex2f(px, py + escala)
            glEnd()
        # Al final de cada letra la "pluma" avanza al siguiente casillero
        glTranslatef(6 * escala, 0, 0)
        glEndList()
        _listas[clave] = lista
    return _listas[clave]


def dibujar_texto(x, y, texto, escala=2):
    """Dibuja el texto con su esquina superior izquierda en (x, y)."""
    texto = normalizar(texto)
    glPushMatrix()
    glTranslatef(x, y, 0)
    for letra in texto:
        glCallList(_lista_de_letra(letra, escala))
    glPopMatrix()


def liberar_listas():
    """Libera las display lists (al cerrar el programa)."""
    for lista in _listas.values():
        glDeleteLists(lista, 1)
    _listas.clear()
