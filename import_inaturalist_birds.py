# -*- coding: utf-8 -*-
"""
Importador de Aves -> Obsidian Markdown (YAML frontmatter)
Usa: eBird Taxonomy + iNaturalist API (observações) para obter imagem
Gera um arquivo por espécie com campo coverUrl apontando a imagem (quando encontrada)
"""

import os
import time
import requests
import yaml
import sys

# --------------------------------------------------------
# CONFIG (Windows + Pasta)
# --------------------------------------------------------
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except:
    pass

OUTPUT_DIR = r"C:\Users\Usuario\Documents\Gnosis\3- Bem estar\Hobbies e Inspirações\Coleções\Animals (Non Fiction)\Birds"
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
# iNaturalist: buscar uma observação para o táxon
# --------------------------------------------------------

def get_inat_image_url_by_taxon(scientific_name, per_page=1):
    """
    Tenta buscar observações no iNaturalist para a espécie (nome científico).
    Retorna a URL da primeira foto da primeira observação encontrada, ou None.
    """
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
        # cada photo tem 'url' base — pode haver diferentes tamanhos
        # usar a URL “original_size” se disponível, senão “medium_url” ou “url”
        first_photo = photos[0]
        # iNaturalist API v1 costuma retornar 'url', 'medium_url' etc.
        for key in ("url", "medium_url", "original_url", "large_url"):
            if key in first_photo and first_photo[key]:
                return first_photo[key]
        # fallback: se só houver 'url'
        return first_photo.get("url")
    except Exception as e:
        # print("Erro ao buscar iNaturalist:", e)
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
# PROGRAMA PRINCIPAL
# --------------------------------------------------------

def main():
    birds = load_ebird_taxonomy()

    for b in birds:
        sci_name = b.get("sciName", "").strip()
        com_name_en = b.get("comName", "").strip()
        family = b.get("familyComName", "").strip()
        order = b.get("order", "").strip()
        species_code = b.get("speciesCode", "").strip()
        com_name_pt = b.get("comNamePt", "").strip()

        # Buscar imagem no iNaturalist
        cover_url = get_inat_image_url_by_taxon(sci_name)
        time.sleep(0.2)  # para evitar limite de requisições

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

        # Nome do arquivo com nome legível da espécie
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

    print("\n=== IMPORTAÇÃO DE AVES FINALIZADA ===")

if __name__ == "__main__":
    main()
