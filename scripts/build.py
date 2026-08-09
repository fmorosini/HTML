import json, os, re, unicodedata
from jinja2 import Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(ROOT, "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False, trim_blocks=True, lstrip_blocks=True)

CAT_MAP = {
    "Latifoliada perenne": "latifoliada-perenne",
    "Latifoliada caduca": "latifoliada-caduca",
    "Conífera perenne": "conifera-perenne",
    "Conífera caduca": "conifera-caduca",
}
CAT_LABELS = list(CAT_MAP.items())  # preserves order for filter chips

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def write(path, html):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(html)

with open(os.path.join(ROOT, "data/species_full.json"), encoding="utf-8") as f:
    species_raw = json.load(f)

with open(os.path.join(ROOT, "data/static_pages.json"), encoding="utf-8") as f:
    static_pages = json.load(f)

# ---------------------------------------------------------------
# Normalize species data
# ---------------------------------------------------------------
species = []
for s in species_raw:
    fields = s.get("fields", [])
    field_map = {f["label"].upper(): f["value"] for f in fields}
    sci_name = field_map.get("NOMBRE CIENTÍFICO") or field_map.get("NOMBRE CIENTIFICO") or s["title"]
    family = field_map.get("FAMILIA BOTÁNICA") or field_map.get("FAMILIA BOTANICA") or ""

    images = s.get("images", [])
    map_image = next((i for i in images if i.get("is_map") and i.get("file")), None)
    gallery_images = [i for i in images if i.get("file") and i is not map_image]
    thumb = gallery_images[0]["file"] if gallery_images else (map_image["file"] if map_image else None)

    cats = []
    for c in s.get("categories", []):
        slug = CAT_MAP.get(c)
        if slug:
            cats.append({"slug": slug, "label": c})

    species.append({
        "slug": s["slug"],
        "title": s["title"],
        "sci_name": sci_name,
        "common_name": s.get("common_name", ""),
        "family": family,
        "fields": fields,
        "extra_text": s.get("extra_text", []),
        "categories": cats,
        "cats_csv": ",".join(c["slug"] for c in cats),
        "map_image": map_image,
        "gallery_images": gallery_images,
        "thumb": thumb,
        "search_text": strip_accents(" ".join([
            s["title"], sci_name, s.get("common_name", ""), family
        ])).lower(),
    })

species.sort(key=lambda s: s["sci_name"].lower())
SPECIES_COUNT = len(species)

# ---------------------------------------------------------------
# Render species ficha pages
# ---------------------------------------------------------------
tmpl_ficha = env.get_template("ficha.html")
for i, sp in enumerate(species):
    prev_sp = species[i - 1] if i > 0 else None
    next_sp = species[i + 1] if i < len(species) - 1 else None
    html = tmpl_ficha.render(
        base="../",
        active="especies",
        page_title=sp["title"],
        page_description=f"{sp['sci_name']} ({sp['family']}) — ficha de especie del arbolado urbano.",
        sci_name=sp["sci_name"],
        common_name=sp["common_name"],
        categories=sp["categories"],
        map_image=sp["map_image"],
        gallery_images=sp["gallery_images"],
        fields=sp["fields"],
        extra_text=sp["extra_text"],
        prev=prev_sp,
        next=next_sp,
    )
    write(f"especies/{sp['slug']}.html", html)

print(f"Generadas {SPECIES_COUNT} fichas de especies.")

# ---------------------------------------------------------------
# Render species listing page
# ---------------------------------------------------------------
tmpl_list = env.get_template("listado_especies.html")
html = tmpl_list.render(
    base="",
    active="especies",
    page_title="Fichas de especies",
    page_description="Buscador de fichas de especies del arbolado urbano de Norpatagonia.",
    species=species,
    categories=[{"slug": slug, "label": label} for label, slug in [(l, s) for l, s in CAT_MAP.items()]],
)
write("fichas-de-especies.html", html)
print("Generado fichas-de-especies.html")

# ---------------------------------------------------------------
# Render static content pages
# ---------------------------------------------------------------
tmpl_content = env.get_template("content_page.html")
STATIC_ACTIVE = {
    "acerca-de-arboles-urbanos": "acerca",
    "asociacion-civil-propatagonia": "acerca",
    "catedra-arbolado-urbano": "acerca",
    "practicas-laborales-alumnos": "acerca",
    "licencia-de-uso": "acerca",
    "referencias": "referencias",
}
for slug, page in static_pages.items():
    html = tmpl_content.render(
        base="",
        active=STATIC_ACTIVE.get(slug, ""),
        page_title=page["title"],
        title=page["title"],
        rows=page["rows"],
    )
    write(f"{slug}.html", html)
print(f"Generadas {len(static_pages)} páginas de contenido estático.")

# ---------------------------------------------------------------
# Render contacto.html
# ---------------------------------------------------------------
tmpl_contacto = env.get_template("contacto.html")
write("contacto.html", tmpl_contacto.render(base="", active="contacto", page_title="Contáctenos"))
print("Generado contacto.html")

# ---------------------------------------------------------------
# Render index.html
# ---------------------------------------------------------------
tmpl_index = env.get_template("index.html")
write("index.html", tmpl_index.render(
    base="", active="inicio", page_title="Inicio",
    species_count=SPECIES_COUNT,
))
print("Generado index.html")

# ---------------------------------------------------------------
# Build lightweight search index (optional artifact, not required at runtime)
# ---------------------------------------------------------------
index_data = [{
    "slug": sp["slug"], "sci_name": sp["sci_name"], "common_name": sp["common_name"],
    "family": sp["family"], "categories": [c["slug"] for c in sp["categories"]],
} for sp in species]
write("data/species_index.json", json.dumps(index_data, ensure_ascii=False, indent=2))

print("BUILD OK")
