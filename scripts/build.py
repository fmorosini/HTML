import json, os, re, unicodedata
from jinja2 import Environment, FileSystemLoader

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(ROOT, "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=False, trim_blocks=True, lstrip_blocks=True)

SITE_URL = "https://arbolesurbanos.com.ar"
DEFAULT_OG_IMAGE = f"{SITE_URL}/assets/img/au_logo_horizontal_verde.png"

CAT_MAP = {
    "Latifoliada perenne": "latifoliada-perenne",
    "Latifoliada caduca": "latifoliada-caduca",
    "Conífera perenne": "conifera-perenne",
    "Conífera caduca": "conifera-caduca",
}

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def write(path, html):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(html)

def jsonld(data):
    """Serialize a dict/list to a <script>-safe JSON-LD string."""
    return json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

with open(os.path.join(ROOT, "data/species_full.json"), encoding="utf-8") as f:
    species_raw = json.load(f)

with open(os.path.join(ROOT, "data/static_pages.json"), encoding="utf-8") as f:
    static_pages = json.load(f)

# ---------------------------------------------------------------
# Normalize species data
# ---------------------------------------------------------------
ALT_HINTS = [
    (r"flor", "Flores de {n}"),
    (r"fruto|s[aá]mara|semilla", "Frutos de {n}"),
    (r"corteza", "Corteza de {n}"),
    (r"ejemplar|adulto|jov[ea]n", "Ejemplar de {n}"),
    (r"foliar|hoja|env[ée]s|follaje", "Hojas de {n}"),
    (r"pi[nñ]a|estr[oó]bilo", "Piñas de {n}"),
    (r"ramita|rama", "Rama de {n}"),
]

def guess_alt(filename, sci_name):
    base = strip_accents(filename.lower())
    for pattern, template in ALT_HINTS:
        if re.search(pattern, base):
            return template.format(n=sci_name)
    return f"Fotografía de {sci_name}"

species = []
for s in species_raw:
    fields = s.get("fields", [])
    field_map = {f["label"].upper(): f["value"] for f in fields}
    sci_name = field_map.get("NOMBRE CIENTÍFICO") or field_map.get("NOMBRE CIENTIFICO") or s["title"]
    family = field_map.get("FAMILIA BOTÁNICA") or field_map.get("FAMILIA BOTANICA") or ""
    origen = field_map.get("ORIGEN", "")
    descripcion = field_map.get("DESCRIPCIÓN GENERAL") or field_map.get("DESCRIPCION GENERAL") or ""

    images = s.get("images", [])
    map_image = next((i for i in images if i.get("is_map") and i.get("file")), None)
    gallery_images = [i for i in images if i.get("file") and i is not map_image]

    # Backfill missing alt text from filename hints (task: SEO/AEO alt text)
    if map_image and not map_image.get("alt", "").strip():
        map_image["alt"] = f"Área de distribución natural de {sci_name}"
    for img in gallery_images:
        if not img.get("alt", "").strip():
            img["alt"] = guess_alt(img["file"], sci_name)

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
        "origen": origen,
        "descripcion": descripcion,
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
    canonical_url = f"{SITE_URL}/especies/{sp['slug']}.html"
    og_image = f"{SITE_URL}/assets/img/especies/{sp['thumb']}" if sp["thumb"] else DEFAULT_OG_IMAGE
    page_description = f"{sp['common_name'] or sp['sci_name']} ({sp['sci_name']}) — {sp['family']}. {strip_html(sp['origen'])}"[:300]

    taxon_ld = {
        "@context": "https://schema.org",
        "@type": "Taxon",
        "@id": canonical_url + "#taxon",
        "name": sp["common_name"] or sp["sci_name"],
        "scientificName": sp["sci_name"],
        "url": canonical_url,
        "taxonRank": "species",
        "description": strip_html(sp["descripcion"])[:500] or page_description,
        "image": og_image,
        "isPartOf": {"@id": f"{SITE_URL}/#website"},
    }
    if sp["family"]:
        taxon_ld["parentTaxon"] = {"@type": "Taxon", "name": sp["family"], "taxonRank": "family"}
    if sp["categories"]:
        taxon_ld["additionalProperty"] = [
            {"@type": "PropertyValue", "name": "Categoría", "value": c["label"]} for c in sp["categories"]
        ]

    breadcrumb_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{SITE_URL}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "Especies", "item": f"{SITE_URL}/fichas-de-especies.html"},
            {"@type": "ListItem", "position": 3, "name": sp["sci_name"], "item": canonical_url},
        ],
    }

    html = tmpl_ficha.render(
        base="../",
        active="especies",
        site_url=SITE_URL,
        canonical_url=canonical_url,
        og_image=og_image,
        og_type="article",
        page_title=sp["title"],
        page_description=page_description,
        sci_name=sp["sci_name"],
        common_name=sp["common_name"],
        categories=sp["categories"],
        map_image=sp["map_image"],
        gallery_images=sp["gallery_images"],
        fields=sp["fields"],
        extra_text=sp["extra_text"],
        prev=prev_sp,
        next=next_sp,
        jsonld_taxon=jsonld(taxon_ld),
        jsonld_breadcrumb=jsonld(breadcrumb_ld),
    )
    write(f"especies/{sp['slug']}.html", html)

print(f"Generadas {SPECIES_COUNT} fichas de especies.")

# ---------------------------------------------------------------
# Render species listing page
# ---------------------------------------------------------------
tmpl_list = env.get_template("listado_especies.html")
listing_breadcrumb = jsonld({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{SITE_URL}/index.html"},
        {"@type": "ListItem", "position": 2, "name": "Especies", "item": f"{SITE_URL}/fichas-de-especies.html"},
    ],
})
html = tmpl_list.render(
    base="",
    active="especies",
    site_url=SITE_URL,
    canonical_url=f"{SITE_URL}/fichas-de-especies.html",
    og_image=DEFAULT_OG_IMAGE,
    page_title="Fichas de especies",
    page_description=f"Buscador de {SPECIES_COUNT} fichas de especies del arbolado urbano de Norpatagonia: nombre científico, familia, origen y fotos.",
    species=species,
    categories=[{"slug": slug, "label": label} for label, slug in [(l, s) for l, s in CAT_MAP.items()]],
    jsonld_breadcrumb=listing_breadcrumb,
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

TERM_RE = re.compile(r"^([A-ZÁÉÍÓÚÑ0-9²/ ]{2,40})\s*\n?\s*:\s*(.+)$", re.S)

def extract_defined_terms(rows):
    terms = []
    for row in rows:
        for cell in row:
            for block in cell:
                if block.get("type") != "text":
                    continue
                for p in block.get("paragraphs", []):
                    m = TERM_RE.match(strip_html(p))
                    if m:
                        term, definition = m.group(1).strip().rstrip(":"), m.group(2).strip()
                        if len(definition) > 20:
                            terms.append({"term": term, "definition": definition})
    return terms

for slug, page in static_pages.items():
    canonical_url = f"{SITE_URL}/{slug}.html"
    jsonld_extra_blocks = [{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{SITE_URL}/index.html"},
            {"@type": "ListItem", "position": 2, "name": page["title"], "item": canonical_url},
        ],
    }]

    if slug == "referencias":
        terms = extract_defined_terms(page["rows"])
        if terms:
            jsonld_extra_blocks.append({
                "@context": "https://schema.org",
                "@type": "DefinedTermSet",
                "name": "Referencias — Glosario del arbolado urbano",
                "url": canonical_url,
                "hasDefinedTerm": [
                    {"@type": "DefinedTerm", "name": t["term"], "description": t["definition"][:400]}
                    for t in terms
                ],
            })

    html = tmpl_content.render(
        base="",
        active=STATIC_ACTIVE.get(slug, ""),
        site_url=SITE_URL,
        canonical_url=canonical_url,
        og_image=DEFAULT_OG_IMAGE,
        page_title=page["title"],
        title=page["title"],
        rows=page["rows"],
        jsonld_blocks=[jsonld(b) for b in jsonld_extra_blocks],
    )
    write(f"{slug}.html", html)
print(f"Generadas {len(static_pages)} páginas de contenido estático.")

# ---------------------------------------------------------------
# Render contacto.html
# ---------------------------------------------------------------
tmpl_contacto = env.get_template("contacto.html")
contacto_breadcrumb = jsonld({
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{SITE_URL}/index.html"},
        {"@type": "ListItem", "position": 2, "name": "Contáctenos", "item": f"{SITE_URL}/contacto.html"},
    ],
})
write("contacto.html", tmpl_contacto.render(
    base="", active="contacto",
    site_url=SITE_URL,
    canonical_url=f"{SITE_URL}/contacto.html",
    og_image=DEFAULT_OG_IMAGE,
    page_title="Contáctenos",
    jsonld_breadcrumb=contacto_breadcrumb,
))
print("Generado contacto.html")

# ---------------------------------------------------------------
# Render index.html
# ---------------------------------------------------------------
tmpl_index = env.get_template("index.html")
write("index.html", tmpl_index.render(
    base="", active="inicio",
    site_url=SITE_URL,
    canonical_url=f"{SITE_URL}/index.html",
    og_image=DEFAULT_OG_IMAGE,
    page_title="Inicio",
    page_description=f"Mapa interactivo y {SPECIES_COUNT} fichas de especies del arbolado urbano de la zona cordillerana de Norpatagonia.",
    species_count=SPECIES_COUNT,
))
print("Generado index.html")

# ---------------------------------------------------------------
# Search index (used only for potential future client-side needs)
# ---------------------------------------------------------------
index_data = [{
    "slug": sp["slug"], "sci_name": sp["sci_name"], "common_name": sp["common_name"],
    "family": sp["family"], "categories": [c["slug"] for c in sp["categories"]],
} for sp in species]
write("data/species_index.json", json.dumps(index_data, ensure_ascii=False, indent=2))

# ---------------------------------------------------------------
# sitemap.xml
# ---------------------------------------------------------------
static_urls = ["index.html", "fichas-de-especies.html", "contacto.html"] + [f"{slug}.html" for slug in static_pages]
species_urls = [f"especies/{sp['slug']}.html" for sp in species]

sitemap_entries = "\n".join(
    f"  <url><loc>{SITE_URL}/{path}</loc><changefreq>monthly</changefreq><priority>{prio}</priority></url>"
    for path, prio in (
        [(p, "0.8") for p in static_urls] + [(p, "0.6") for p in species_urls]
    )
)
sitemap_xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    f"{sitemap_entries}\n"
    "</urlset>\n"
)
write("sitemap.xml", sitemap_xml)
print(f"Generado sitemap.xml ({len(static_urls) + len(species_urls)} URLs)")

# ---------------------------------------------------------------
# robots.txt
# ---------------------------------------------------------------
write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
print("Generado robots.txt")

# ---------------------------------------------------------------
# llms.txt — guía de contenido para crawlers de modelos de lenguaje
# ---------------------------------------------------------------
llms_txt = f"""# Arboles Urbanos

> Mapas y fichas del arbolado urbano de localidades de la zona cordillerana de Norpatagonia (Argentina). Proyecto de la Cátedra de Arbolado Urbano (Asentamiento Universitario San Martín de los Andes, Universidad Nacional del Comahue) y la Asociación Civil Propatagonia.

## Contenido principal

- [Mapa interactivo]({SITE_URL}/index.html): ubicación geográfica de {SPECIES_COUNT}+ árboles relevados, con especie, tipo de follaje y magnitud.
- [Fichas de especies]({SITE_URL}/fichas-de-especies.html): buscador de {SPECIES_COUNT} especies arbóreas, cada una con nombre científico, familia botánica, origen, descripción, usos, reproducción y fotografías.
- [Referencias]({SITE_URL}/referencias.html): glosario de términos usados en las fichas (nombre científico, magnitud, categorías de follaje).
- [Acerca de esta página]({SITE_URL}/acerca-de-arboles-urbanos.html), [Asociación Civil Propatagonia]({SITE_URL}/asociacion-civil-propatagonia.html), [Cátedra Arbolado Urbano]({SITE_URL}/catedra-arbolado-urbano.html): contexto institucional del proyecto.
- [Licencia de uso]({SITE_URL}/licencia-de-uso.html): contenido bajo licencia Creative Commons Atribución-CompartirIgual 4.0 Internacional. Los datos de georreferenciación son abiertos.

## Contacto

Email: mapaarbolesurbanos@gmail.com · Instagram: @mapa.arboles.urbanos
"""
write("llms.txt", llms_txt)
print("Generado llms.txt")

print("BUILD OK")
