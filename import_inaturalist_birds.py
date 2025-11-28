# -*- coding: utf-8 -*-
"""
Importador de Aves -> Obsidian Markdown (YAML frontmatter)
Usa: eBird Taxonomy + iNaturalist API + Wikipedia (fallback) para obter imagem
Gera um arquivo por espécie com campo coverUrl apontando a imagem (quando encontrada)
Suporta retomar de onde parou e evita duplicatas.
"""

import os
import time
import requests
import yaml
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------
# CONFIG
# --------------------------------------------------------
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except:
    pass

OUTPUT_DIR = r"C:\Users\Usuario\Documents\Gnosis\3- Bem estar\Hobbies e Inspirações\Coleções\Animals (Non Fiction)\Birds"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")
MAX_WORKERS = 10  # número de threads para download paralelo

session = requests.Session()
session.headers.update({"User-Agent": "BirdImporter/1.0 (via iNaturalist)"})

# --------------------------------------------------------
# UTILIDADES
# --------------------------------------------------------
def get_json(url, params=None):
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def safe_filename(s):
    s = s.replace("/", "-").replace("\\", "-").replace(":", "-")
    s = s.replace("*", "").replace("?", "").replace('"', "").strip()
    return s

def write_md(filename, yaml_obj, body_md=""):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(yaml.safe_dump(yaml_obj, sort_keys=False, allow_unicode=True))
        f.write("---\n\n")
        f.write(body_md)

# --------------------------------------------------------
# iNaturalist: pegar imagem
# --------------------------------------------------------
def get_inat_image_url_by_taxon(scientific_name, per_page=1):
    try:
        resp = get_json(
            "https://api.inaturalist.org/v1/observations",
            {
                "taxon_name": scientific_name,
                "per_page": per_page,
                "order_by": "observed_on",
                "order": "desc"
            }
        )
        results = resp.get("results", [])
        if not results:
            return None
        obs = results[0]
        photos = obs.get("photos", [])
        if not photos:
            return None
        first_photo = photos[0]
        for key in ("url", "medium_url", "original_url", "large_url"):
            if key in first_photo and first_photo[key]:
                return first_photo[key]
        return first_photo.get("url")
    except Exception:
        return None

# --------------------------------------------------------
# Wikipedia: pegar imagem principal
# --------------------------------------------------------
def get_wikipedia_image(scientific_name):
    try:
        # pegar artigo em inglês (melhor cobertura)
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": scientific_name,
            "prop": "pageimages",
            "pithumbsize": 800
        }
        data = get_json(url, params=params)
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                return thumb
        return None
    except Exception:
        return None

# --------------------------------------------------------
# EBIRD TAXONOMY
# --------------------------------------------------------
def load_ebird_taxonomy():
    print("[INFO] Baixando taxonomia eBird (pode demorar)...")
    url = "https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=json"
    data = get_json(url)
    print(f"[INFO] {len(data)} espécies carregadas.")
    return data

# --------------------------------------------------------
# Função principal de processamento de cada pássaro
# --------------------------------------------------------
def process_bird(bird, processed_set):
    sci_name = bird.get("sciName", "").strip()
    com_name_en = bird.get("comName", "").strip()
    family = bird.get("familyComName", "").strip()
    order = bird.get("order", "").strip()
    species_code = bird.get("speciesCode", "").strip()
    com_name_pt = bird.get("comNamePt", "").strip()

    if species_code in processed_set:
        print(f"[SKIP] {com_name_en} — já processado")
        return species_code

    # buscar imagem: primeiro iNaturalist, depois Wikipedia
    cover_url = get_inat_image_url_by_taxon(sci_name)
    if not cover_url:
        cover_url = get_wikipedia_image(sci_name)

    yaml_obj = {
        "type": "animals",
        "subType": "bird",
        "id": species_code,
        "name_en": com_name_en,
        "name_pt": com_name_pt,
        "scientific_name": sci_name,
        "taxonomy": {
            "order": order,
            "family": family,
        },
        "coverUrl": cover_url,
        "image": cover_url,
    }

    fname = safe_filename(f"{com_name_en}.md")
    md_body = f"# {com_name_en}\n\n"
    if com_name_pt:
        md_body += f"**Nome em PT-BR:** {com_name_pt}\n\n"
    md_body += f"**Nome científico:** *{sci_name}*\n\n"
    md_body += f"**Família:** {family}\n\n"
    md_body += f"**Ordem:** {order}\n\n"
    if cover_url:
        md_body += f"![image]({cover_url})\n"

    write_md(fname, yaml_obj, md_body)
    print(f"[OK] {com_name_en} — cover: {bool(cover_url)}")
    return species_code

# --------------------------------------------------------
# Main
# --------------------------------------------------------
def main():
    birds = load_ebird_taxonomy()

    # carregar checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            processed = set(json.load(f))
    else:
        processed = set()

    total = len(birds)
    print(f"[INFO] Começando importação — {len(processed)} já processados.")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_species = {executor.submit(process_bird, b, processed): b for b in birds}

        for future in as_completed(future_to_species):
            species_code = future.result()
            if species_code:
                processed.add(species_code)
                # salvar checkpoint incremental
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    json.dump(list(processed), f, ensure_ascii=False, indent=2)

    print("\n=== IMPORTAÇÃO DE AVES FINALIZADA ===")

if __name__ == "__main__":
    main()
