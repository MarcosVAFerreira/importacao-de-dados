# -*- coding: utf-8 -*-
"""
Importador de Livros -> Obsidian Markdown (YAML frontmatter)
Usa: Goodreads API + fallback de capa via Open Library / Web (quando disponível)
Gera um arquivo por livro com coverUrl apontando a imagem (quando encontrada)
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

OUTPUT_DIR = r"C:\Users\Usuario\Documents\Gnosis\3- Bem estar\Hobbies e Inspirações\Coleções\Leituras\Livros"
os.makedirs(OUTPUT_DIR, exist_ok=True)

CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")
MAX_WORKERS = 5  # threads para download paralelo

session = requests.Session()
session.headers.update({"User-Agent": "BookImporter/1.0"})

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
# Obter imagem da capa via Open Library (fallback)
# --------------------------------------------------------
def get_cover_url(isbn=None):
    if not isbn:
        return None
    return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"

# --------------------------------------------------------
# Função de processamento de cada livro
# --------------------------------------------------------
def process_book(book, processed_set):
    # Espera-se que book seja um dict com dados do Goodreads
    title = book.get("title")
    portugueseTitle = book.get("title_pt") or ""
    englishTitle = book.get("title_en") or title
    coverUrl = book.get("image_url") or get_cover_url(book.get("isbn"))
    onlineRating = str(book.get("average_rating", "Desconhecido"))
    subType = book.get("genre", "Desconhecido")
    status = book.get("status", "Desconhecido")
    rating = str(book.get("rating", "Desconhecido"))
    autor = book.get("author", "Desconhecido")
    editora = book.get("publisher", "Desconhecido")
    ano = str(book.get("publication_year", "Desconhecido"))
    pais = book.get("country", "Desconhecido")
    idioma = book.get("language", "Desconhecido")
    era = book.get("era", "Desconhecido")
    cronologia = ano

    uid = f"{title}_{autor}"
    if uid in processed_set:
        print(f"[SKIP] {title} — já processado")
        return uid

    yaml_obj = {
        "title": {title: None},
        "portugueseTitle": {portugueseTitle: None},
        "englishTitle": {englishTitle: None},
        "coverUrl": {coverUrl: None},
        "onlineRating": {onlineRating: None},
        "type": "Livros",
        "subType": {subType: None},
        "status": {status: None},
        "rating": {rating: None},
        "autor": {autor: None},
        "editora": {editora: None},
        "ano": {ano: None},
        "país": {pais: None},
        "idioma": {idioma: None},
        "era": {era: None},
        "cronologia": {cronologia: None},
        "tags": [
            "coleção/Livros",
            f"gênero/{subType}",
            f"autor/{autor}",
            f"país/{pais}",
            f"era/{era}",
            f"status/{status}",
            f"Rating/{onlineRating}"
        ]
    }

    fname = safe_filename(f"{title}.md")
    md_body = f"# {title}\n\n"
    if portugueseTitle:
        md_body += f"**Título em PT-BR:** {portugueseTitle}\n\n"
    md_body += f"**Título em EN:** {englishTitle}\n\n"
    md_body += f"**Autor:** {autor}\n\n"
    md_body += f"**Editora:** {editora}\n\n"
    md_body += f"**Ano:** {ano}\n\n"
    md_body += f"**País:** {pais}\n\n"
    md_body += f"**Idioma:** {idioma}\n\n"
    md_body += f"**Status:** {status}\n\n"
    md_body += f"**Gênero:** {subType}\n\n"
    md_body += f"**Rating online:** {onlineRating}\n\n"
    if coverUrl:
        md_body += f"![image]({coverUrl})\n"

    write_md(fname, yaml_obj, md_body)
    print(f"[OK] {title} — cover: {bool(coverUrl)}")
    return uid

# --------------------------------------------------------
# Main
# --------------------------------------------------------
# ... [mesmo código até a função main()]

def main():
    # Lista de livros, cada item é um dict com os dados
    books = []
    # Exemplo:
    # books = get_books_from_goodreads_api()

    # Filtrar apenas livros de terror/horror
    horror_books = [b for b in books if "terror" in b.get("genre", "").lower() or "horror" in b.get("genre", "").lower()]

    if not horror_books:
        print("[INFO] Nenhum livro de terror encontrado.")
        return

    # carregar checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            processed = set(json.load(f))
    else:
        processed = set()

    print(f"[INFO] Começando importação — {len(processed)} já processados. Total de terror: {len(horror_books)}")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_book = {executor.submit(process_book, b, processed): b for b in horror_books}

        for future in as_completed(future_to_book):
            uid = future.result()
            if uid:
                processed.add(uid)
                # salvar checkpoint incremental
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    json.dump(list(processed), f, ensure_ascii=False, indent=2)

    print("\n=== IMPORTAÇÃO DE LIVROS DE TERROR FINALIZADA ===")
