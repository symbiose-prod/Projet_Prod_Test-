# pages/02_Optimisation.py
import pandas as pd
import streamlit as st

from common.design import apply_theme, section, kpi
from common.data import get_paths
from core.optimizer import (
    load_flavor_map_from_path,
    apply_canonical_flavor,
    compute_losses_table_v48,
)

apply_theme("Optimisation & pertes — Ferment Station", "📉")
section("Optimisation & pertes", "📉")

# Besoin du fichier en mémoire
if "df_raw" not in st.session_state or "window_days" not in st.session_state:
    st.warning("Aucun fichier chargé. Va dans **Accueil** pour déposer l'Excel, puis reviens.")
    st.stop()

_, flavor_map, _ = get_paths()
df_raw = st.session_state.df_raw
window_days = st.session_state.window_days

# ---- SIDEBAR: prix moyen au choix ----
with st.sidebar:
    st.header("Paramètres pertes")
    price_hL = st.number_input(
        "Prix moyen (€/hL)",
        min_value=0.0,
        value=500.0,
        step=10.0,
        format="%.0f",
    )

st.caption(
    f"Fichier courant : **{st.session_state.get('file_name','(sans nom)')}** — "
    f"Fenêtre (B2) : **{window_days} jours** — "
    f"Prix moyen : **€{price_hL:.0f}/hL**"
)

# ---- Calculs ----
fm = load_flavor_map_from_path(flavor_map)
df_in = apply_canonical_flavor(df_raw, fm)
pertes = compute_losses_table_v48(df_in, window_days, price_hL)

colA, colB = st.columns([2, 1])
with colA:
    if isinstance(pertes, pd.DataFrame) and not pertes.empty:
        st.dataframe(pertes, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune perte estimée sur 7 jours (données insuffisantes ou stock suffisant).")

with colB:
    total = float(pertes["Perte (€)"].sum()) if isinstance(pertes, pd.DataFrame) and not pertes.empty else 0.0
    kpi("Perte totale (7 j)", f"€{total:,.0f}")
