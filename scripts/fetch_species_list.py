import requests, re, json
from bs4 import BeautifulSoup

BASE = "https://arbolesurbanos.com.ar"
r = requests.get(f"{BASE}/fichas-de-especies/", timeout=30, headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
r.raise_for_status()
soup = BeautifulSoup(r.text, "html.parser")

EXCLUDE = {"fichas-de-especies","referencias","contacto","acerca-de-arboles-urbanos",
           "catedra-arbolado-urbano","asociacion-civil-propatagonia","practicas-laborales-alumnos",
           "licencia-de-uso", ""}

species = {}
for a in soup.select("a[href]"):
    href = a["href"]
    m = re.match(rf"^{re.escape(BASE)}/([a-z0-9\-]+)/?$", href)
    if not m:
        continue
    slug = m.group(1)
    if slug in EXCLUDE:
        continue
    title = a.get_text(strip=True)
    if slug not in species:
        species[slug] = {"slug": slug, "url": href, "title": title}
    elif title and not species[slug]["title"]:
        species[slug]["title"] = title

print(len(species), "species found")
with open("data/species_list.json","w") as f:
    json.dump(sorted(species.values(), key=lambda s: s["slug"]), f, ensure_ascii=False, indent=2)
