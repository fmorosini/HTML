import json, re, os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote

BASE = "https://arbolesurbanos.com.ar"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
IMG_DIR = "assets/img/site"
PDF_DIR = "assets/pdf"
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

PAGES = [
    "acerca-de-arboles-urbanos",
    "asociacion-civil-propatagonia",
    "catedra-arbolado-urbano",
    "practicas-laborales-alumnos",
    "licencia-de-uso",
    "referencias",
]

def clean_filename(url):
    name = unquote(os.path.basename(urlparse(url).path))
    name = re.sub(r"[^A-Za-z0-9._\-ÁÉÍÓÚÑáéíóúñ]", "_", name)
    return name

def download_image(url, dest_path):
    if os.path.exists(dest_path):
        return True
    try:
        r = requests.get(url, headers=H, timeout=30)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print("  IMG FAIL", url, e)
        return False

def download_pdf(url, dest_path):
    if os.path.exists(dest_path):
        return True
    try:
        r = requests.get(url, headers=H, timeout=60)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print("  PDF FAIL", url, e)
        return False

def inner_html(tag):
    return re.sub(r"\s+", " ", tag.decode_contents()).strip()

def fix_links(html):
    # rewrite internal links to the old opendata endpoint / site root sensibly (kept as external reference)
    return html

def text_widget_to_paragraphs(widget):
    ps = widget.find_all("p", recursive=False) or widget.find_all("p")
    if ps:
        out = []
        for p in ps:
            html = inner_html(p)
            if html and html.strip():
                out.append(html)
        if out:
            return out
    raw = widget.get_text("\n", strip=True)
    parts = [re.sub(r"[ \t]+", " ", p).strip() for p in re.split(r"\n\s*\n", raw)]
    return [p for p in parts if p]

def process_image(img, dest_dir=IMG_DIR):
    src = img.get("src")
    if not src:
        return None
    fname = clean_filename(src)
    dest = os.path.join(dest_dir, fname)
    ok = download_image(src, dest)
    width = img.get("width")
    height = img.get("height")

    link_file = None
    parent_a = img.find_parent("a")
    if parent_a and parent_a.get("href", "").lower().endswith(".pdf"):
        pdf_url = parent_a["href"]
        pdf_fname = clean_filename(pdf_url)
        pdf_dest = os.path.join(PDF_DIR, pdf_fname)
        if download_pdf(pdf_url, pdf_dest):
            link_file = pdf_fname

    return {
        "type": "image",
        "file": fname if ok else None,
        "alt": img.get("alt", ""),
        "width": int(width) if width and str(width).isdigit() else None,
        "height": int(height) if height and str(height).isdigit() else None,
        "link_pdf": link_file,
    }

def parse_cell(cell):
    blocks = []
    for widget in cell.select(".so-panel"):
        # El título del widget (h3.widget-title) es hermano del .textwidget, no
        # está dentro: si no se lee acá se pierden, por ejemplo, los títulos de
        # los trabajos en Prácticas Laborales.
        titulo = widget.select_one(".widget-title")
        if titulo:
            texto = re.sub(r"\s+", " ", titulo.get_text(" ", strip=True)).strip()
            if texto:
                nivel = titulo.name if titulo.name in ("h2", "h3", "h4") else "h3"
                blocks.append({"type": "heading", "level": nivel, "text": texto})

        tw = widget.select_one(".textwidget")
        if tw:
            paras = text_widget_to_paragraphs(tw)
            if paras:
                blocks.append({"type": "text", "paragraphs": paras})
            continue
        img = widget.select_one("img")
        if img:
            b = process_image(img)
            if b:
                blocks.append(b)
            continue
    return blocks

def parse_simple_content(content):
    """Fallback for plain WP editor content (no page builder)."""
    blocks = []
    for el in content.find_all(["p", "ul", "ol", "h2", "h3", "h4"], recursive=False):
        if el.name in ("ul", "ol"):
            items = [inner_html(li) for li in el.find_all("li", recursive=False)]
            items = [i for i in items if i]
            if items:
                blocks.append({"type": "list", "ordered": el.name == "ol", "items": items})
            continue
        if el.name in ("h2", "h3", "h4"):
            txt = el.get_text(" ", strip=True)
            if txt:
                blocks.append({"type": "heading", "level": el.name, "text": txt})
            continue
        # paragraph: may wrap a single image
        img = el.find("img")
        if img and len(el.get_text(strip=True)) == 0:
            b = process_image(img)
            if b:
                blocks.append(b)
            continue
        html = inner_html(el)
        if html:
            blocks.append({"type": "text", "paragraphs": [html]})
    return [[b] for b in blocks]  # each block its own row/cell for simple pages

results = {}
for slug in PAGES:
    url = f"{BASE}/{slug}/"
    r = requests.get(url, headers=H, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    article = soup.select_one("article")
    h1 = article.select_one(".entry-title")
    title = h1.get_text(strip=True) if h1 else slug
    content = article.select_one(".entry-content")

    rows = []
    grids = content.select(".panel-grid")
    if grids:
        for grid in grids:
            cells = grid.select(".panel-grid-cell")
            row_blocks = [parse_cell(c) for c in cells]
            if any(row_blocks):
                rows.append(row_blocks)
    else:
        for block_list in parse_simple_content(content):
            rows.append([block_list])

    n_text = sum(1 for row in rows for cell in row for b in cell if b["type"] == "text")
    n_img = sum(1 for row in rows for cell in row for b in cell if b["type"] == "image")
    n_list = sum(1 for row in rows for cell in row for b in cell if b["type"] == "list")

    results[slug] = {"slug": slug, "title": title, "rows": rows}
    print(slug, "-> rows:", len(rows), "text:", n_text, "images:", n_img, "lists:", n_list)

with open("data/static_pages.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("DONE")
