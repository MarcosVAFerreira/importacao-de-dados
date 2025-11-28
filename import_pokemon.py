# -*- coding: utf-8 -*-
"""
Importador PokeAPI -> Obsidian Markdown (YAML frontmatter)
Compatível com Windows (UTF-8 garantido)
"""

import os
import time
import requests
import yaml
import sys

# --------------------------------------------------------
# CONFIG (Windows)
# --------------------------------------------------------

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except:
    pass

OUTPUT_DIR = (
    r"C:\Users\Usuario\Documents\Gnosis\3- Bem estar\Hobbies e Inspirações\Coleções\Creatures (Fiction)\Pokemons"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

POKEAPI_BASE = "https://pokeapi.co/api/v2"
SLEEP_BETWEEN = 0.11

session = requests.Session()
session.headers.update({"User-Agent": "PokemonImporter-Windows-UTF8/3.1"})


# --------------------------------------------------------
# UTILIDADES
# --------------------------------------------------------

def get_json(url):
    r = session.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def safe_title(s):
    if not s:
        return ""
    return s.replace("-", " ").replace("_", " ").title()


def write_md(filename, yaml_obj, body_md=""):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(yaml.safe_dump(yaml_obj, sort_keys=False, allow_unicode=True))
        f.write("---\n\n")
        if body_md:
            f.write(body_md)


# --------------------------------------------------------
# TABELA DE TIPOS
# --------------------------------------------------------

def build_type_chart():
    print("[INFO] Construindo tabela de tipos...")
    types = get_json(f"{POKEAPI_BASE}/type?limit=1000")["results"]

    chart = {}

    for t in types:
        data = get_json(t["url"])
        rel = data["damage_relations"]
        name = t["name"]

        chart[name] = {
            "double_from": [x["name"] for x in rel["double_damage_from"]],
            "half_from": [x["name"] for x in rel["half_damage_from"]],
            "zero_from": [x["name"] for x in rel["no_damage_from"]],
        }

        time.sleep(SLEEP_BETWEEN)

    return chart


TYPE_CHART = build_type_chart()
ALL_TYPES = list(TYPE_CHART.keys())


def calc_type_effectiveness(pokemon_types):
    result = {t: 1.0 for t in ALL_TYPES}

    for ptype in pokemon_types:
        rel = TYPE_CHART.get(ptype.lower())
        if not rel:
            continue

        for t in rel["double_from"]:
            result[t] *= 2
        for t in rel["half_from"]:
            result[t] *= 0.5
        for t in rel["zero_from"]:
            result[t] *= 0

    return {k.title(): v for k, v in result.items()}


# --------------------------------------------------------
# FORMAS
# --------------------------------------------------------

def classify_form_name(variety_name, default_name):
    name = variety_name.lower()

    if name == default_name.lower():
        return ("default", "")

    if "mega" in name:
        return ("mega", "Mega")
    if "gmax" in name or "gigantamax" in name:
        return ("gmax", "Gigantamax")
    if "alola" in name:
        return ("alolan", "Alolan")
    if "galar" in name:
        return ("galarian", "Galarian")
    if "hisui" in name:
        return ("hisuian", "Hisuian")

    return ("variant", safe_title(variety_name))


# --------------------------------------------------------
# MOVES
# --------------------------------------------------------

def parse_moves(pjson):
    moves = {}

    for mv in pjson.get("moves", []):
        move_name = mv["move"]["name"].replace("-", " ").title()

        for detail in mv["version_group_details"]:
            method = detail["move_learn_method"]["name"]
            vg = detail["version_group"]["name"]
            level = detail["level_learned_at"]

            moves.setdefault(method, []).append(
                {"move": move_name, "version_group": vg, "level": level}
            )

    norm = {
        "level_up": sorted(
            moves.get("level-up", []), key=lambda x: (x["version_group"], x["level"])
        ),
        "machine": moves.get("machine", []),
        "tutor": moves.get("tutor", []),
        "egg": moves.get("egg", []),
        "other": [],
    }

    for k in moves:
        if k not in ["level-up", "machine", "tutor", "egg"]:
            norm["other"].extend(moves[k])

    return norm


# --------------------------------------------------------
# PROGRAMA PRINCIPAL
# --------------------------------------------------------

def main():

    print("[INFO] Baixando lista completa de Pokémon...")
    master = get_json(f"{POKEAPI_BASE}/pokemon?limit=20000")["results"]

    for entry in master:
        name_raw = entry["name"]

        try:
            p = get_json(entry["url"])
            species = get_json(p["species"]["url"])

            generation = safe_title(species["generation"]["name"])
            color = safe_title(species["color"]["name"])
            habitat = safe_title(species["habitat"]["name"]) if species.get("habitat") else ""

            genus = next(
                (g["genus"] for g in species["genera"] if g["language"]["name"] == "en"),
                ""
            )

            flavor_entries = []
            for ft in species["flavor_text_entries"]:
                if ft["language"]["name"] == "en":
                    txt = ft["flavor_text"].replace("\n", " ").replace("\f", " ").strip()
                    flavor_entries.append({"version": ft["version"]["name"], "text": txt})

            evo_chain = []
            if species.get("evolution_chain"):
                chain = get_json(species["evolution_chain"]["url"])

                def walk(node):
                    evo_chain.append(safe_title(node["species"]["name"]))
                    for nxt in node["evolves_to"]:
                        walk(nxt)

                walk(chain["chain"])

            for var in species["varieties"]:
                pv = get_json(var["pokemon"]["url"])
                time.sleep(SLEEP_BETWEEN)

                var_name_raw = pv["name"]
                var_name = safe_title(var_name_raw)

                form_key, form_label = classify_form_name(var_name_raw, name_raw)

                pid = species["id"]
                base_name = safe_title(species["name"])

                final_name = (
                    base_name if form_key == "default"
                    else f"{base_name} ({form_label or var_name})"
                )

                sprites = pv["sprites"]
                official = sprites.get("other", {}).get("official-artwork", {}).get("front_default")
                sprite_default = sprites.get("front_default")
                sprite_shiny = sprites.get("front_shiny")

                types = [t["type"]["name"].title() for t in pv["types"]]

                stats_raw = {s["stat"]["name"]: s["base_stat"] for s in pv["stats"]}
                total = sum(stats_raw.values())

                abilities = [a["ability"]["name"].replace("-", " ").title() for a in pv["abilities"]]

                moves = parse_moves(pv)

                height_m = pv["height"] / 10
                weight_kg = pv["weight"] / 10

                type_eff = calc_type_effectiveness([t.lower() for t in types])

                # --------------------------------------------------------
                # YAML FINAL (agora com coverUrl)
                # --------------------------------------------------------

                yaml_obj = {
                    "type": "creatures",
                    "subType": "pokemon",
                    "id": pid,
                    "dex_id": pid,

                    "name": final_name,
                    "species_name": base_name,

                    "form_of": base_name if form_key != "default" else None,
                    "form_type": form_label if form_key != "default" else None,

                    "coverUrl": official or sprite_default or sprite_shiny,

                    "image": official or sprite_default or sprite_shiny,
                    "sprites": {
                        "official_artwork": official,
                        "default": sprite_default,
                        "shiny": sprite_shiny,
                    },

                    "types": types,
                    "generation": generation,
                    "color": color,
                    "category": genus,
                    "habitat": habitat,

                    "height_m": height_m,
                    "weight_kg": weight_kg,

                    "abilities": abilities,

                    "stats": {
                        "total": total,
                        "hp": stats_raw.get("hp"),
                        "attack": stats_raw.get("attack"),
                        "defense": stats_raw.get("defense"),
                        "special_attack": stats_raw.get("special-attack"),
                        "special_defense": stats_raw.get("special-defense"),
                        "speed": stats_raw.get("speed"),
                    },

                    "moves": moves,
                    "pokedex_entries": flavor_entries,
                    "type_effectiveness": type_eff,
                    "evolution_chain": evo_chain,
                }

                yaml_obj = {k: v for k, v in yaml_obj.items() if v is not None}

                fname = f"{pid:04d} - {final_name}.md"
                fname = fname.replace("/", "-").replace("\\", "-")

                md_body = f"# {final_name}\n\n"
                md_body += f"**Types:** {', '.join(types)}\n\n"
                md_body += f"**Abilities:** {', '.join(abilities)}\n\n"

                write_md(fname, yaml_obj, md_body)

                print(f"[OK] {fname} salvo.")

        except Exception as e:
            print(f"[ERRO] Pokémon {name_raw}: {e}")
            time.sleep(0.5)

    print("\n=== IMPORTAÇÃO FINALIZADA ===")


if __name__ == "__main__":
    main()
