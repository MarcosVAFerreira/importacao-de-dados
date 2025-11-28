# -*- coding: utf-8 -*-
import os
import requests
from bs4 import BeautifulSoup
import yaml
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# --------------------------------------------------------
# Configurações
# --------------------------------------------------------
OUTPUT_DIR = r"C:\Users\Usuario\Documents\Gnosis\3- Bem estar\Hobbies e Inspirações\Coleções\Leituras\Livros"
os.makedirs(OUTPUT_DIR, exist_ok=True)
CHECKPOINT_FILE = os.path.join(OUTPUT_DIR, "checkpoint.json")
MAX_WORKERS = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# --------------------------------------------------------
# Utilitários
# --------------------------------------------------------
def safe_filename(s):
    return s.replace("/", "-").replace("\\", "-").replace(":", "-").strip()

def write_md(filename, yaml_obj, body_md=""):
    path = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(path):
        return  # evita sobrescrever arquivos existentes
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(yaml.safe_dump(yaml_obj, sort_keys=False, allow_unicode=True))
        f.write("---\n\n")
        f.write(body_md)

# --------------------------------------------------------
# Scraping de uma página da lista
# --------------------------------------------------------
def scrape_list_page(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    books = []
    
    # Cada livro está dentro de <div class="elementList">
    for book_row in soup.select("div.elementList"):
        title_tag = book_row.select_one("a.bookTitle span")
        author_tag = book_row.select_one("a.authorName span")
        rating_tag = book_row.select_one("span.minirating")
        cover_tag = book_row.select_one("img.bookCover")
        if not title_tag or not author_tag:
            continue
        title = title_tag.get_text(strip=True)
        author = author_tag.get_text(strip=True)
        avg_rating = None
        if rating_tag:
            text = rating_tag.get_text()
            avg_rating = text.split(" avg rating")[0].strip()
        cover_url = cover_tag['src'] if cover_tag and cover_tag.has_attr('src') else None
        books.append({
            "title": title,
            "author": author,
            "average_rating": avg_rating,
            "image_url": cover_url,
            "genre": "Terror/Horror",
        })
    return books

# --------------------------------------------------------
# Percorrer todas as páginas da lista
# --------------------------------------------------------
def get_all_books_from_list(list_url):
    books = []
    page = 1
    while True:
        url = f"{list_url}?page={page}"
        print(f"[INFO] Scraping {url}")
        page_books = scrape_list_page(url)
        if not page_books:
            break
        books.extend(page_books)
        page += 1
    return books

# --------------------------------------------------------
# Processar e gerar Markdown de cada livro
# --------------------------------------------------------
def process_book(book, processed_set):
    title = book.get("title")
    autor = book.get("author")
    uid = f"{title}_{autor}"
    if uid in processed_set:
        print("[SKIP]", title)
        return None

    yaml_obj = {
        "title": {title: None},
        "portugueseTitle": {title: None},
        "englishTitle": {title: None},
        "coverUrl": {book.get("image_url"): None},
        "onlineRating": {book.get("average_rating") or "Desconhecido": None},
        "type": "Livros",
        "subType": {"Terror": None},
        "status": {"Desconhecido": None},
        "rating": {"Desconhecido": None},
        "autor": {autor: None},
        "editora": {"Desconhecido": None},
        "ano": {"Desconhecido": None},
        "país": {"Desconhecido": None},
        "idioma": {"Desconhecido": None},
        "era": {"Desconhecido": None},
        "cronologia": {"Desconhecido": None},
        "tags": [
            "coleção/Livros",
            "gênero/Terror",
            f"autor/{autor}",
            "país/Desconhecido",
            "era/Desconhecido",
            "status/Desconhecido",
            f"Rating/{book.get('average_rating') or 'Desconhecido'}"
        ]
    }

    fname = safe_filename(f"{title}.md")
    md_body = f"# {title}\n\n**Autor:** {autor}\n\n**Gênero:** Terror\n\n**Rating online:** {book.get('average_rating')}\n\n"
    if book.get("image_url"):
        md_body += f"![cover]({book.get('image_url')})\n"

    write_md(fname, yaml_obj, md_body)
    print("[OK]", title)
    return uid

# --------------------------------------------------------
# Função principal
# --------------------------------------------------------
def main():
    list_url = "https://www.goodreads.com/list/show/2455.The_Most_Disturbing_Books_Ever_Written"
    books = get_all_books_from_list(list_url)
    print(f"[INFO] Achados {len(books)} livros na lista.")

    # Carregar checkpoint para evitar duplicatas
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            processed = set(json.load(f))
    else:
        processed = set()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(process_book, b, processed) for b in books]
        for future in as_completed(futures):
            uid = future.result()
            if uid:
                processed.add(uid)

    # Salvar checkpoint final
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed), f, ensure_ascii=False, indent=2)
    print("[INFO] Fim da importação.")

if __name__ == "__main__":
    main()
