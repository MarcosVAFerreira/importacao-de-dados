import os
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://howtotrainyourdragon.fandom.com"
CLASSES_URL = BASE + "/wiki/Dragon_Classes_(Franchise)"

OUTPUT_FOLDER = r"C:\Users\Usuario\Documents\Gnosis\3- Bem estar\Hobbies e Inspirações\Coleções\Criaturas e seres\Dreamwork Dragons"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# -----------------------------
# TEXT CLEANERS
# -----------------------------
def clean(txt):
    if not txt:
        return ""
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()

def clean_field(value):
    if not value:
        return ""
    v = clean(value)
    v = re.sub(r"^[A-Za-z ]+:\s*", "", v)
    v = re.sub(r"\([^)]*\)", "", v)
    return clean(v)

# -----------------------------
# 1. EXTRACT DRAGON NAMES
# -----------------------------
def extract_dragon_names():
    print("[+] Fetching Dragon Classes page…")
    html = requests.get(CLASSES_URL, headers=HEADERS).text
    soup = BeautifulSoup(html, "html.parser")

    dragon_names = set()

    for header in soup.find_all(["h2", "h3"]):
        next_tag = header.find_next_sibling()

        while next_tag:
            if next_tag.name in ["h2", "h3"]:
                break

            if next_tag.name == "ul":
                for li in next_tag.find_all("li"):
                    name = clean(li.get_text())
                    name = name.split("(")[0].strip()
                    if len(name) > 2:
                        dragon_names.add(name)

            next_tag = next_tag.find_next_sibling()

    return sorted(dragon_names)

# -----------------------------
# 2. FETCH DRAGON PAGE
# -----------------------------
def get_dragon_page(name):
    url = BASE + "/wiki/" + name.replace(" ", "_")
    r = requests.get(url, headers=HEADERS)
    return (url, r.text)

# -----------------------------
# 3. PARSE INFOBOX
# -----------------------------
def parse_infobox(html):
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one(".portable-infobox")
    if not box:
        return {}

    data = {}

    for item in box.select(".pi-item"):
        key = item.get("data-source")
        if key:
            data[key.lower()] = clean(item.get_text(" "))

    img = box.select_one("img")
    data["cover"] = img.get("src", "") if img else ""

    return data

# -----------------------------
# 4. BUILD MARKDOWN WITH YAML
# -----------------------------
def make_md(name, info):
    yaml_block = [
        "---",
        f"type: Creatures",
        f"subType: Dragon",
        f"title: {name}",
        f"coverUrl: {info.get('cover','')}",
        f"class: {clean_field(info.get('class',''))}",
        f"fireType: {clean_field(info.get('fire type',''))}",
        f"colors: {clean_field(info.get('color',''))}",
        f"size: {clean_field(info.get('size',''))}",
        f"weight: {clean_field(info.get('weight',''))}",
        f"wingspan: {clean_field(info.get('wingspan',''))}",
        f"diet: {clean_field(info.get('diet',''))}",
        f"habitat: {clean_field(info.get('habitat',''))}",
        f"distribution: {clean_field(info.get('distribution',''))}",
        f"trainable: {clean_field(info.get('trainable',''))}",
        "---",
        ""
    ]

    stats = f"""
## Statistics
- **Attack:** {clean_field(info.get('attack',''))}
- **Speed:** {clean_field(info.get('speed',''))}
- **Armor:** {clean_field(info.get('armor',''))}
- **Firepower:** {clean_field(info.get('firepower',''))}
- **Shot Limit:** {clean_field(info.get('shot limit',''))}
- **Venom:** {clean_field(info.get('venom',''))}
- **Jaw Strength:** {clean_field(info.get('jaw strength',''))}
- **Stealth:** {clean_field(info.get('stealth',''))}
"""

    return "\n".join(yaml_block) + stats.strip() + "\n"

# -----------------------------
# 5. SAVE FILE
# -----------------------------
def save(name, text):
    safe = name.replace("/", "-")
    path = os.path.join(OUTPUT_FOLDER, f"{safe}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

# -----------------------------
# MAIN
# -----------------------------
def main():
    names = extract_dragon_names()
    print(f"[+] Found {len(names)} dragons!")

    for name in names:
        print("Scraping:", name)
        url, html = get_dragon_page(name)
        info = parse_infobox(html)
        md = make_md(name, info)
        save(name, md)

    print("\nDone! All dragons exported.\n")

main()
