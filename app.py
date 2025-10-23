# app.py — Accueil + préflight syntaxe des pages
# --- Defaults libpq pour toute connexion implicite (anti-root) ---
import os
os.environ.setdefault("PGUSER",     os.getenv("DB_USERNAME", ""))
os.environ.setdefault("PGPASSWORD", os.getenv("DB_PASSWORD", ""))
os.environ.setdefault("PGHOST",     os.getenv("DB_HOST", ""))
os.environ.setdefault("PGPORT",     os.getenv("DB_PORT", "5432"))
os.environ.setdefault("PGDATABASE", os.getenv("DB_DATABASE") or os.getenv("DB_NAME", ""))
os.environ.setdefault("PGSSLMODE",  os.getenv("DB_SSLMODE", "disable"))
# -----------------------------------------------------------------

import pathlib, traceback
import streamlit as st
import pandas as pd


import streamlit as st
import psycopg2
import os

import streamlit as st
st.set_page_config(page_title="Symbiose", layout="wide")

# --- DEBUG DB, n'empêche jamais l'app de démarrer ---
try:
    from db.conn import ping, debug_dsn, _current_dsn
    ok, msg = ping()
    st.write("Test de connexion à la base de données")
    st.success(msg) if ok else st.error(msg)
    st.caption(f"DB debug: {debug_dsn()}")
    with st.expander("Voir DSN (masqué)", expanded=False):
        st.code(_current_dsn())
except Exception as e:
    import traceback
    st.error(f"DB init failed: {e}")
    st.text("".join(traceback.format_exc()))
# -----------------------------------------------------

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require")
    )
    st.success("✅ Connexion réussie à la base PostgreSQL !")
    conn.close()
except Exception as e:
    st.error(f"❌ Erreur de connexion : {e}")

from db.conn import whoami
st.caption(f"DB user (via conn.py): {whoami()}")


# ---------- PRE-FLIGHT : détecte les erreurs de syntaxe dans pages/*.py ----------
def _preflight_pages():
    root = pathlib.Path(__file__).resolve().parent
    pages = sorted((root / "pages").glob("*.py"))
    bad = []
    for p in pages:
        code = p.read_text(encoding="utf-8", errors="replace")
        try:
            compile(code, str(p), "exec")
        except SyntaxError as e:
            st.set_page_config(page_title="Erreur de syntaxe", page_icon="🛑", layout="wide")
            st.title("🛑 Erreur de syntaxe dans une page Streamlit")
            st.error(f"Fichier : `{p.name}` — ligne **{e.lineno}**, colonne **{e.offset}**")
            st.code("".join(traceback.format_exception_only(e)), language="text")
            # extrait de code : 2 lignes avant/après
            lines = code.splitlines()
            i = max(0, (e.lineno or 1) - 1)
            snippet = "\n".join(lines[max(0, i-2): i+3])
            st.code(snippet, language="python")
            st.info("Corrige ce fichier dans GitHub → Commit → recharge l’app.")
            bad.append(p)
    if bad:
        st.stop()

_preflight_pages()
# ---------- FIN PRE-FLIGHT ------------------------------------------------------

# --- Accueil “Uploader unique” (ton code d’origine) ---
from common.design import apply_theme, section
from core.optimizer import read_input_excel_and_period_from_upload

apply_theme("Ferment Station — Accueil", "🥤")
section("Accueil", "🏠")
st.caption("Dépose ici ton fichier Excel. Il sera utilisé automatiquement dans tous les onglets.")

uploaded = st.file_uploader("Dépose un Excel (.xlsx / .xls)", type=["xlsx", "xls"])
col1, col2 = st.columns([1,1])
with col1:
    clear = st.button("♻️ Réinitialiser le fichier chargé", use_container_width=True)
with col2:
    show_head = st.toggle("Afficher un aperçu (20 premières lignes)", value=True)

if clear:
    for k in ("df_raw", "window_days", "file_name"):
        if k in st.session_state:
            del st.session_state[k]
    st.success("Fichier déchargé. Dépose un nouvel Excel pour continuer.")

if uploaded is not None:
    try:
        df_raw, window_days = read_input_excel_and_period_from_upload(uploaded)
        st.session_state.df_raw = df_raw
        st.session_state.window_days = window_days
        st.session_state.file_name = uploaded.name
        st.success(f"Fichier chargé ✅ : **{uploaded.name}** · Fenêtre détectée (B2) : **{window_days} jours**")
    except Exception as e:
        st.error(f"Erreur de lecture de l'Excel : {e}")

if "df_raw" in st.session_state:
    st.info(f"Fichier en mémoire : **{st.session_state.get('file_name','(sans nom)')}** — fenêtre : **{st.session_state.get('window_days', '—')} jours**")
    if show_head:
        st.dataframe(st.session_state.df_raw.head(20), use_container_width=True)
else:
    st.warning("Aucun fichier en mémoire. Dépose un Excel ci-dessus pour activer les autres onglets.")
