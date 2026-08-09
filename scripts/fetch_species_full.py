import json, re, os, time
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote

BASE = "https://arbolesurbanos.com.ar"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
IMG_DIR = "assets/img/especies"
os.makedirs(IMG_DIR, exist_ok=True)

with open("data/species_list.json") as f:
    species_list = json.load(f)

LABEL_RE = re.compile(r"^([A-ZÁÉÍÓÚÑ0-9 ²/]{3,40}):\s*(.*)$", re.UNICODE)

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

def parse_species(item):
    slug, url = item["slug"], item["url"]
    try:
        r = requests.get(url, headers=H, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print("FAIL", slug, e)
        return {"slug": slug, "url": url, "error": str(e)}

    soup = BeautifulSoup(r.text, "html.parser")
    article = soup.select_one("article")
    if not article:
        return {"slug": slug, "url": url, "error": "no article"}

    h1 = article.select_one(".entry-title")
    title = h1.get_text(strip=True) if h1 else item.get("title", slug)

    posted = article.select_one(".posted-on time, .posted-on a")
    published = posted.get_text(strip=True) if posted else ""

    cats = [a.get_text(strip=True) for a in article.select(".cat-links a")]

    content = article.select_one(".entry-content")
    common_name = ""
    fields = []
    intro_extra = []
    if content:
        cells = content.select(".panel-grid-cell")
        text_cell = cells[0] if cells else content
        paragraphs = text_cell.select(".textwidget > p") or text_cell.select("p")
        for p in paragraphs:
            txt = p.get_text(" ", strip=True)
            txt = re.sub(r"\s+", " ", txt).strip()
            if not txt:
                continue
            strong = p.find("strong")
            if strong:
                strong_text = strong.get_text(" ", strip=True).rstrip(":").strip()
                rest = txt
                # remove the strong part from the beginning
                if txt.startswith(strong.get_text(" ", strip=True)):
                    rest = txt[len(strong.get_text(" ", strip=True)):].strip()
                    rest = rest.lstrip(":").strip()
                m = LABEL_RE.match(txt)
                if m:
                    label, value = m.group(1).strip(), m.group(2).strip()
                    fields.append({"label": label, "value": value})
                elif not fields and not common_name:
                    common_name = strong_text
                else:
                    intro_extra.append(txt)
            else:
                intro_extra.append(txt)

        # images: any <img> inside content, excluding ones already handled
        imgs = []
        for img in content.select("img"):
            src = img.get("src")
            if not src:
                continue
            alt = img.get("alt", "").strip()
            fname = clean_filename(src)
            dest = os.path.join(IMG_DIR, fname)
            ok = download_image(src, dest)
            is_adn = bool(re.search(r"adn", fname, re.I)) or "distribuci" in alt.lower()
            imgs.append({
                "src_original": src,
                "file": fname if ok else None,
                "alt": alt,
                "is_map": is_adn,
            })
    else:
        imgs = []

    # prev/next from original site nav (informational only)
    nav_links = article.select(".navigation a, nav.post-navigation a")

    return {
        "slug": slug,
        "url": url,
        "title": title,
        "common_name": common_name,
        "published": published,
        "categories": cats,
        "fields": fields,
        "extra_text": intro_extra,
        "images": imgs,
    }

results = []
errors = []
with ThreadPoolExecutor(max_workers=10) as ex:
    futs = {ex.submit(parse_species, item): item for item in species_list}
    done_count = 0
    for fut in as_completed(futs):
        res = fut.result()
        results.append(res)
        done_count += 1
        if res.get("error"):
            errors.append(res)
        if done_count % 10 == 0:
            print(f"{done_count}/{len(species_list)} done")

results.sort(key=lambda r: r["slug"])
with open("data/species_full.json", "w") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("TOTAL:", len(results), "ERRORS:", len(errors))
for e in errors:
    print(" -", e["slug"], e.get("error"))
