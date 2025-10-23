# common/storage.py
from __future__ import annotations
import json, os, tempfile, shutil, time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
import pandas as pd
import streamlit as st

# Limite "mémoire longue"
MAX_SLOTS = 6

# ---------------------------------------------------------------------
# Encodage / décodage des payloads (identique à ta version locale)
# ---------------------------------------------------------------------
def _encode_sp(sp: Dict[str, Any]) -> Dict[str, Any]:
    def _df(x):
        return x.to_json(orient="split") if isinstance(x, pd.DataFrame) else None
    return {
        "semaine_du": sp.get("semaine_du"),
        "ddm": sp.get("ddm"),
        "gouts": list(sp.get("gouts", [])),
        "df_min": _df(sp.get("df_min")),
        "df_calc": _df(sp.get("df_calc")),
    }

def _decode_sp(obj: Dict[str, Any]) -> Dict[str, Any]:
    def _df(s):
        return pd.read_json(s, orient="split") if isinstance(s, str) and s.strip() else None
    return {
        "semaine_du": obj.get("semaine_du"),
        "ddm": obj.get("ddm"),
        "gouts": obj.get("gouts") or [],
        "df_min": _df(obj.get("df_min")),
        "df_calc": _df(obj.get("df_calc")),
    }

# ---------------------------------------------------------------------
# Backend LOCAL (fallback quand pas de secrets GitHub)
# --> utile en dev local ; éphémère sur Streamlit Cloud
# ---------------------------------------------------------------------
_STATE_DIR  = Path(".streamlit")
_STATE_PATH = _STATE_DIR / "saved_productions.json"

def _local_ensure():
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not _STATE_PATH.exists():
        _STATE_PATH.write_text("[]", encoding="utf-8")

def _local_read_all() -> List[Dict[str, Any]]:
    _local_ensure()
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8") or "[]")
    except Exception:
        return []

def _local_write_all(data: List[Dict[str, Any]]):
    _local_ensure()
    fd, tmp = tempfile.mkstemp(dir=str(_STATE_DIR), prefix="sp_", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
    shutil.move(tmp, _STATE_PATH)

# ---------------------------------------------------------------------
# Backend GITHUB (persistant)
# ---------------------------------------------------------------------
def _gh_enabled() -> bool:
    return "GH_TOKEN" in st.secrets and "GH_REPO" in st.secrets

def _gh_ctx():
    from github import Github  # PyGithub
    gh = Github(st.secrets["GH_TOKEN"])
    repo = gh.get_repo(st.secrets["GH_REPO"])
    branch = st.secrets.get("GH_BRANCH", "main")
    path = st.secrets.get("GH_PATH_MEMOIRE", "data/memoire_longue.json")
    return repo, branch, path

def _gh_read_all() -> Tuple[List[Dict[str, Any]], str | None]:
    repo, branch, path = _gh_ctx()
    try:
        f = repo.get_contents(path, ref=branch)
        data = json.loads(f.decoded_content.decode("utf-8") or "[]")
        return data, f.sha
    except Exception:
        # fichier absent -> première écriture
        return [], None

def _gh_write_all(data: List[Dict[str, Any]], sha: str | None):
    repo, branch, path = _gh_ctx()
    content = json.dumps(data, ensure_ascii=False, indent=2)
    msg = f"chore(storage): update mémoire longue ({time.strftime('%Y-%m-%d %H:%M:%S')})"
    if sha is None:
        repo.create_file(path, msg, content, branch=branch)
    else:
        repo.update_file(path, msg, content, sha, branch=branch)

# Sélection dynamique du backend
def _read_all() -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if _gh_enabled():
        data, sha = _gh_read_all()
        return data, {"sha": sha, "backend": "github"}
    data = _local_read_all()
    return data, {"sha": None, "backend": "local"}

def _write_all(data: List[Dict[str, Any]], meta: Dict[str, Any]):
    if meta.get("backend") == "github":
        _gh_write_all(data, meta.get("sha"))
    else:
        _local_write_all(data)

# ---------------------------------------------------------------------
# API publique (inchangée pour tes pages)
# ---------------------------------------------------------------------
def list_saved() -> List[Dict[str, Any]]:
    """Retourne [{name, ts, gouts, semaine_du}] triés du plus récent au plus ancien."""
    data, _meta = _read_all()
    data.sort(key=lambda x: x.get("ts",""), reverse=True)
    out = []
    for it in data:
        p = it.get("payload", {})
        out.append({
            "name": it.get("name"),
            "ts": it.get("ts"),
            "gouts": (p.get("gouts") or [])[:],
            "semaine_du": p.get("semaine_du"),
        })
    return out

def save_snapshot(name: str, sp: Dict[str, Any]) -> Tuple[bool, str]:
    """Crée/remplace une proposition. Respecte MAX_SLOTS quand nouveau nom."""
    name = (name or "").strip()
    if not name:
        return False, "Nom vide."
    data, meta = _read_all()

    # remplace si même nom
    idx = next((i for i, it in enumerate(data) if it.get("name")==name), None)
    entry = {
        "name": name,
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "payload": _encode_sp(sp)
    }
    if idx is not None:
        data[idx] = entry
        _write_all(data, meta)
        return True, "Proposition mise à jour."

    # nouveau nom: respect limite
    if len(data) >= MAX_SLOTS:
        return False, f"Limite atteinte ({MAX_SLOTS}). Supprime ou renomme une entrée."
    data.append(entry)
    _write_all(data, meta)
    return True, "Proposition enregistrée."

def load_snapshot(name: str) -> Dict[str, Any] | None:
    data, _meta = _read_all()
    it = next((it for it in data if it.get("name")==name), None)
    return _decode_sp(it.get("payload", {})) if it else None

def delete_snapshot(name: str) -> bool:
    data, meta = _read_all()
    new = [it for it in data if it.get("name") != name]
    if len(new) == len(data):
        return False
    _write_all(new, meta)
    return True

def rename_snapshot(old: str, new: str) -> Tuple[bool, str]:
    new = (new or "").strip()
    if not new:
        return False, "Nouveau nom vide."
    data, meta = _read_all()
    if any(it.get("name")==new for it in data):
        return False, "Ce nom existe déjà."
    it = next((it for it in data if it.get("name")==old), None)
    if not it:
        return False, "Entrée introuvable."
    it["name"] = new
    _write_all(data, meta)
    return True, "Renommée."
