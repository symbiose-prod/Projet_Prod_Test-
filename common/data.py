import os, yaml, pandas as pd
from functools import lru_cache

CONFIG_DEFAULT = {
    "data_files": {
        "main_table": "data/production.xlsx",
        "flavor_map": "data/flavor_map.csv",
    },
    "images_dir": "assets",
}

def load_config() -> dict:
    path = "config.yaml"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return {**CONFIG_DEFAULT, **(yaml.safe_load(f) or {})}
    return CONFIG_DEFAULT

@lru_cache(maxsize=1)
def get_paths():
    cfg = load_config()
    return (
        cfg["data_files"]["main_table"],
        cfg["data_files"]["flavor_map"],
        cfg["images_dir"],
    )

@lru_cache(maxsize=2)
def read_table():
    main_table, _, _ = get_paths()
    import os, pandas as pd

    if not os.path.exists(main_table):
        # Pas de fichier -> DataFrame vide
        return pd.DataFrame()

    lower = main_table.lower()
    try:
        if lower.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
            # Formats Excel modernes -> openpyxl
            return pd.read_excel(main_table, engine="openpyxl", header=None)
        elif lower.endswith(".xls"):
            # Ancien Excel -> xlrd (nécessite xlrd dans requirements)
            return pd.read_excel(main_table, engine="xlrd", header=None)
        elif lower.endswith((".csv", ".txt")):
            # CSV/TXT du repo (séparateur ; si besoin adapte)
            try:
                return pd.read_csv(main_table, sep=";", engine="python", header=None)
            except Exception:
                return pd.read_csv(main_table, sep=",", engine="python", header=None)
        else:
            # Fallback: on tente openpyxl puis xlrd
            try:
                return pd.read_excel(main_table, engine="openpyxl", header=None)
            except Exception:
                return pd.read_excel(main_table, engine="xlrd", header=None)
    except Exception as e:
        # On remonte une table vide pour que l'accueil n’explose pas,
        # et on affiche l’erreur côté pages quand on relira le fichier proprement.
        return pd.DataFrame()

@lru_cache(maxsize=2)
def read_flavor_map():
    _, flavor_map, _ = get_paths()
    if not os.path.exists(flavor_map):
        return pd.DataFrame(columns=["name","canonical"])
    # essaie différents séparateurs si besoin
    try:
        return pd.read_csv(flavor_map, encoding="utf-8")
    except Exception:
        return pd.read_csv(flavor_map, encoding="utf-8", sep=";")

