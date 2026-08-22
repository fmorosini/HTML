import glob, json, os, re, sys, unicodedata
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

# ---------------------------------------------------------------
# Mapas del arbolado. Una sola lista para todo: las páginas de mapa y la
# grilla del home, para que no se desincronicen.
#   localidad  -> título de la página de mapa (h1)
#   nombre     -> rótulo del botón en el home (más corto)
#   en_home    -> si aparece en la grilla 2x2, en este orden:
#                 1 arriba izq., 2 arriba der., 3 abajo izq., 4 abajo der.
#   centro     -> None calcula el centro desde los propios datos
# ---------------------------------------------------------------
CENTRO_SMA = (-40.157417863269345, -71.35222077369691)

MAPAS = [
    {
        "salida": "mapa_sma1.html", "geojson": "SMA1.geojson",
        "localidad": "San Martín de Los Andes Centro", "nombre": "San Martín Centro",
        "imagen": "boton-san-martin-de-los-andes-centro.png",
        "centro": CENTRO_SMA, "zoom": 15, "en_home": True,
    },
    {
        "salida": "mapa_sma3.html", "geojson": "SMA3.geojson",
        "localidad": "San Martín de Los Andes Periferia", "nombre": "San Martín Periferia",
        "imagen": "boton-san-martin-de-los-andes-periferia.png",
        "centro": CENTRO_SMA, "zoom": 15, "en_home": True,
    },
    {
        "salida": "mapa-junin-de-los-andes.html", "geojson": "junin.geojson",
        "localidad": "Junín de Los Andes", "nombre": "Junín de los Andes",
        "imagen": "boton-junin-de-los-andes.png",
        "centro": None, "zoom": 18, "en_home": True,
    },
    {
        "salida": "mapa-alumine.html", "geojson": "alumine.geojson",
        "localidad": "Aluminé", "nombre": "Aluminé",
        "imagen": "boton-alumine.png",
        "centro": None, "zoom": 16, "en_home": True,
    },
    # Se genera pero queda sin enlazar desde el sitio (decisión del proyecto).
    {
        "salida": "mapa_sma2.html", "geojson": "SMA2.geojson",
        "localidad": "San Martín de Los Andes", "nombre": "San Martín de los Andes",
        "imagen": None,
        "centro": CENTRO_SMA, "zoom": 15, "en_home": False,
    },
]

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
MAPAS_HOME = [m for m in MAPAS if m.get("en_home")]

faltantes = []
for m in MAPAS_HOME:
    m["imagen_ok"] = os.path.exists(os.path.join(ROOT, "assets/img", m["imagen"]))
    if not m["imagen_ok"]:
        faltantes.append(m["imagen"])

tmpl_index = env.get_template("index.html")
write("index.html", tmpl_index.render(
    base="", active="inicio",
    site_url=SITE_URL,
    canonical_url=f"{SITE_URL}/index.html",
    og_image=DEFAULT_OG_IMAGE,
    page_title="Inicio",
    page_description=f"Mapas del arbolado urbano de San Martín de los Andes, Aluminé y Junín de los Andes, y {SPECIES_COUNT} fichas de especies.",
    species_count=SPECIES_COUNT,
    mapas=MAPAS_HOME,
))
print("Generado index.html")
if faltantes:
    print(f"  aviso: faltan {len(faltantes)} imágenes en assets/img/: {', '.join(faltantes)}")

# ---------------------------------------------------------------
# Search index (used only for potential future client-side needs)
# ---------------------------------------------------------------
index_data = [{
    "slug": sp["slug"], "sci_name": sp["sci_name"], "common_name": sp["common_name"],
    "family": sp["family"], "categories": [c["slug"] for c in sp["categories"]],
    "thumb": sp["thumb"],
} for sp in species]
write("data/species_index.json", json.dumps(index_data, ensure_ascii=False, indent=2))

# ---------------------------------------------------------------
# json/especies-lookup.json
#
# Algunos GeoJSON del arbolado (junin) sólo traen `nombrecientifico` y les
# faltan los campos que el código de los mapas necesita: `imagen` (ícono por
# especie), `thumbnail` (foto del popup) y `url_ficha`. Este índice permite
# completarlos por nombre científico, para que esos mapas se vean igual que
# los de SMA sin tener que tocar su código de dibujado.
#
# Los valores se cosechan de los GeoJSON que SÍ traen esos campos. Si en algún
# momento se regenera junin.geojson con el esquema completo, su mapa deja de
# depender de este archivo.
#
# Claves normalizadas: sin acentos, minúsculas, sólo letras y espacios. Se
# indexa por nombre completo y por "género especie" (primeros 2 tokens), para
# tolerar variedades y cultivares del dato de campo.
# ---------------------------------------------------------------
def norm_sci(s):
    s = strip_accents(s or "").lower()
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def put(lookup, key, entry):
    """Guarda por nombre completo y por género+especie, sin sobreescribir."""
    if not key:
        return
    lookup.setdefault(key, entry)
    toks = key.split()
    if len(toks) >= 2:
        lookup.setdefault(" ".join(toks[:2]), entry)

FUENTES_GEOJSON = ["SMA1", "SMA2", "SMA3", "alumine", "junin"]

# Slugs locales válidos, para no enlazar a fichas inexistentes: el dato de campo
# arrastra slugs viejos de WordPress (ilex-aquifolium-acebo,
# crateagus-monogyna-epino-albar, embotrium-coccineum-notro) que hoy no existen.
slug_por_nombre = {}
for sp in species:
    slug_por_nombre.setdefault(norm_sci(sp["sci_name"]), sp["slug"])
    toks = norm_sci(sp["sci_name"]).split()
    if len(toks) >= 2:
        slug_por_nombre.setdefault(" ".join(toks[:2]), sp["slug"])

lookup = {}
sin_ficha = set()
for nombre_fuente in FUENTES_GEOJSON:
    ruta = os.path.join(ROOT, "json", f"{nombre_fuente}.geojson")
    if not os.path.exists(ruta):
        continue
    with open(ruta, encoding="utf-8") as f:
        geo = json.load(f)
    for feat in geo.get("features", []):
        p = feat.get("properties", {})
        clave = norm_sci(p.get("nombrecientifico"))
        if not clave:
            continue
        toks = clave.split()
        slug = slug_por_nombre.get(clave) or (
            slug_por_nombre.get(" ".join(toks[:2])) if len(toks) >= 2 else None
        )
        if not slug:
            sin_ficha.add(p.get("nombrecientifico"))
        entrada = {}
        if (p.get("imagen") or "").strip():
            entrada["imagen"] = p["imagen"].strip()
        if (p.get("thumbnail") or "").strip():
            entrada["thumbnail"] = p["thumbnail"].strip()
        if slug:
            entrada["slug"] = slug
        if entrada:
            put(lookup, clave, entrada)

# Especies con ficha propia que no aparecen en ningún GeoJSON: quedan sin ícono
# ni miniatura, pero con link a la ficha.
for sp in species:
    put(lookup, norm_sci(sp["sci_name"]), {"slug": sp["slug"]})

write("json/especies-lookup.json", json.dumps(lookup, ensure_ascii=False, indent=1))
con_icono = sum(1 for v in lookup.values() if v.get("imagen"))
print(f"Generado json/especies-lookup.json ({len(lookup)} claves, {con_icono} con ícono)")
if sin_ficha:
    print(f"  aviso: {len(sin_ficha)} especies del arbolado sin ficha propia: {', '.join(sorted(sin_ficha))}")

# ---------------------------------------------------------------
# Mapas Leaflet
# Todos salen de la misma plantilla, con el marco del sitio (nav y pie);
# sólo cambian GeoJSON, centro, zoom y localidad.
# ---------------------------------------------------------------
def centro_de(nombre_geojson):
    """Centro del bounding box de los datos, para encuadrar el mapa."""
    with open(os.path.join(ROOT, "json", nombre_geojson), encoding="utf-8") as f:
        geo = json.load(f)
    lats, lons = [], []
    for feat in geo.get("features", []):
        coords = (feat.get("geometry") or {}).get("coordinates")
        if coords and len(coords) >= 2:
            lons.append(coords[0])
            lats.append(coords[1])
    if not lats:
        return None
    return ((min(lats) + max(lats)) / 2, (min(lons) + max(lons)) / 2)

tmpl_mapa = env.get_template("mapa.html")
generados = 0
for cfg in MAPAS:
    ruta_geo = os.path.join(ROOT, "json", cfg["geojson"])
    if not os.path.exists(ruta_geo):
        print(f"  aviso: falta json/{cfg['geojson']}, se omite {cfg['salida']}")
        continue
    centro = cfg["centro"] or centro_de(cfg["geojson"])
    canonical_url = f"{SITE_URL}/{cfg['salida']}"
    breadcrumb = jsonld({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{SITE_URL}/index.html"},
            {"@type": "ListItem", "position": 2, "name": cfg["localidad"], "item": canonical_url},
        ],
    })
    og_image = (f"{SITE_URL}/assets/img/{cfg['imagen']}"
                if cfg.get("imagen") and os.path.exists(os.path.join(ROOT, "assets/img", cfg["imagen"]))
                else DEFAULT_OG_IMAGE)
    write(cfg["salida"], tmpl_mapa.render(
        base="",
        active="inicio",
        site_url=SITE_URL,
        canonical_url=canonical_url,
        og_image=og_image,
        page_title=cfg["localidad"],
        page_description=f"Mapa interactivo del arbolado urbano de {cfg['localidad']}. Hacé click sobre un árbol para ver sus datos y su ficha.",
        localidad=cfg["localidad"],
        geojson=cfg["geojson"],
        centro_lat=centro[0],
        centro_lon=centro[1],
        zoom=cfg["zoom"],
        jsonld_breadcrumb=breadcrumb,
    ))
    generados += 1
print(f"Generados {generados} mapas desde templates/mapa.html")

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

# ---------------------------------------------------------------
# Chequeo final de las páginas generadas.
# Jinja rinde una variable inexistente como cadena vacía, así que un typo en el
# nombre de un campo deja href="" (que recarga la misma página) o src="" sin
# ningún error. Ya pasó una vez con los 4 botones del home: conviene que el
# build avise en lugar de publicar enlaces rotos.
# ---------------------------------------------------------------
problemas = []
for ruta_html in sorted(glob.glob(os.path.join(ROOT, "*.html")) +
                        glob.glob(os.path.join(ROOT, "especies", "*.html"))):
    contenido = open(ruta_html, encoding="utf-8").read()
    rel = os.path.relpath(ruta_html, ROOT)
    for atributo in ('href=""', "href=''", 'src=""', "src=''"):
        n = contenido.count(atributo)
        if n:
            problemas.append(f"{rel}: {n} x {atributo}")

if problemas:
    print("ERROR: hay atributos vacíos en las páginas generadas:")
    for p in problemas:
        print("   -", p)
    sys.exit(1)

print("Chequeo de enlaces vacíos: OK")
print("BUILD OK")
