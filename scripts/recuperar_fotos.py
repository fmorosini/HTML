"""Recupera las imágenes que faltaban en el sitio a partir de la carpeta local de fotos.

Las 118 imágenes que el WordPress servía con 404 no existen en el servidor ni están
archivadas: todas tenían tildes o `ñ` en el nombre. Este script las toma de la carpeta
de fotos original, las copia a assets/img/especies/ con un nombre sin acentos (para no
repetir el problema) y actualiza data/species_full.json para que el build las incluya.

Uso:  python3 scripts/recuperar_fotos.py [--aplicar]
Sin --aplicar sólo informa lo que haría.
"""
import json, os, re, shutil, sys, unicodedata, urllib.parse, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FOTOS = os.path.join(os.path.dirname(ROOT), "fotos")
DESTINO = os.path.join(ROOT, "assets/img/especies")
DATOS = os.path.join(ROOT, "data/species_full.json")

APLICAR = "--aplicar" in sys.argv


def sin_acentos(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("ñ", "n").replace("Ñ", "N")


def clave(nombre):
    """Clave de comparación: sin extensión, sin sufijos de WordPress, sólo alfanumérico."""
    n = urllib.parse.unquote(nombre).rsplit(".", 1)[0]
    n = re.sub(r"-\d+x\d+$", "", n)      # miniatura: -300x225
    n = re.sub(r"-scaled$", "", n)        # WordPress agrega -scaled al original grande
    n = re.sub(r"-\d$", "", n)            # duplicados: -1, -2
    return re.sub(r"[^a-z0-9]+", "", sin_acentos(n).lower())


def nombre_destino(nombre_original):
    """Nombre ASCII seguro, conservando algo legible."""
    base = urllib.parse.unquote(nombre_original)
    base = re.sub(r"-\d+x\d+(?=\.[^.]+$)", "", base)   # sacar el sufijo de tamaño
    base = re.sub(r"-scaled(?=\.[^.]+$)", "", base)
    base = sin_acentos(base)
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base)
    return re.sub(r"-+", "-", base)


# --- índice de la carpeta de fotos ---
locales = {}
for p in glob.glob(os.path.join(FOTOS, "**", "*"), recursive=True):
    if os.path.isfile(p) and re.search(r"\.(jpe?g|png|gif)$", p, re.I):
        locales.setdefault(clave(os.path.basename(p)), []).append(p)

print(f"fotos disponibles en la carpeta: {sum(len(v) for v in locales.values())}")

with open(DATOS, encoding="utf-8") as f:
    especies = json.load(f)

recuperadas, sin_match = [], []
for sp in especies:
    for img in sp.get("images", []):
        if img.get("file"):
            continue
        origen = os.path.basename(img.get("src_original", ""))
        if not origen:
            continue
        candidatos = locales.get(clave(origen))
        if not candidatos:
            sin_match.append((sp["slug"], urllib.parse.unquote(origen)))
            continue

        # conservar la extensión real del archivo local
        ext = os.path.splitext(candidatos[0])[1].lower()
        destino_nombre = os.path.splitext(nombre_destino(origen))[0] + ext
        recuperadas.append((sp["slug"], img, candidatos[0], destino_nombre))

print(f"imágenes recuperables: {len(recuperadas)}")
print(f"sin correspondencia:   {len(sin_match)}")
for slug, nombre in sin_match:
    print(f"   - {nombre}   [{slug}]")

if not APLICAR:
    print("\n(simulación: volvé a correr con --aplicar para copiar y actualizar los datos)")
    sys.exit(0)

os.makedirs(DESTINO, exist_ok=True)
copiadas = 0
for slug, img, origen_path, destino_nombre in recuperadas:
    destino_path = os.path.join(DESTINO, destino_nombre)
    if not os.path.exists(destino_path):
        shutil.copy2(origen_path, destino_path)
        copiadas += 1
    img["file"] = destino_nombre
    img["recuperada_de"] = os.path.relpath(origen_path, FOTOS)

with open(DATOS, "w", encoding="utf-8") as f:
    json.dump(especies, f, ensure_ascii=False, indent=2)

print(f"\narchivos copiados: {copiadas}")
print(f"data/species_full.json actualizado ({len(recuperadas)} imágenes ahora con archivo)")
print("Ahora corré: python3 scripts/build.py")
