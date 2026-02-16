# app.py
import re
import pandas as pd
import streamlit as st
import altair as alt
import pydeck as pdk

from calculo import calcular_scores_mensais, carregar_base_reme
from pesos import pesos_ahp
from variaveis_talhao import variaveis_talhao

# ============================
#   Constantes e Mapeamentos
# ============================
MESES_ABREVIADOS = ["jan", "fev", "mar", "abr", "mai", "jun",
                    "jul", "ago", "set", "out", "nov", "dez"]
MESES_COMPLETOS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MAP_MES_ABREV_TO_COMPLETO = dict(zip(MESES_ABREVIADOS, MESES_COMPLETOS))
MAP_MES_COMPLETO_TO_ABREV = dict(zip(MESES_COMPLETOS, MESES_ABREVIADOS))

R_BINS = [0, 20, 40, 60, 80, 100]
R_LABELS = ["R1", "R2", "R3", "R4", "R5"]
R_MAP = {lab: i + 1 for i, lab in enumerate(R_LABELS)}
R_RISK_LABELS = ["Risco Muito Baixo", "Risco Baixo", "Risco Moderado", "Risco Médio", "Risco Alto"]
R_RISK_MAP = dict(zip(R_LABELS, R_RISK_LABELS))

# ============================
#   Helpers
# ============================
def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.findall(r'\d+|\D+', str(s))]

def class_geral_from_score(s: pd.Series):
    return pd.cut(s, bins=R_BINS, labels=R_LABELS, include_lowest=True, right=True)

def add_reclassificacoes(df):
    df = df.copy()
    df["classe_geral"] = class_geral_from_score(df["score"])
    df["classe_geral_idx"] = df["classe_geral"].map(R_MAP)
    return df

# ============================
#   Mapa
# ============================
def get_color_from_index(idx):
    if idx <= 1.5:
        return [34, 139, 34, 200]
    if idx <= 2.5:
        return [173, 255, 47, 200]
    if idx <= 3.5:
        return [255, 165, 0, 200]
    if idx <= 4.5:
        return [255, 69, 0, 200]
    return [255, 0, 0, 200]

def criar_mapa_pydeck(df_mapa, titulo_mapa, tooltip_html):
    if df_mapa.empty:
        st.info(f"Não há dados para exibir no mapa: {titulo_mapa}")
        return

    view_state = pdk.ViewState(
        latitude=df_mapa["lat"].mean(),
        longitude=df_mapa["lon"].mean(),
        zoom=10,
        pitch=0
    )

    layer_scatter = pdk.Layer(
        "ScatterplotLayer",
        df_mapa,
        get_position=["lon", "lat"],
        get_color="color_rgb",
        get_radius=200,
        pickable=True,
        auto_highlight=True
    )

    layer_text = pdk.Layer(
        "TextLayer",
        df_mapa,
        get_position=["lon", "lat"],
        get_text="talhao",
        get_color=[255, 255, 255, 255],
        get_size=16,
        pickable=False
    )

    deck = pdk.Deck(
        layers=[layer_scatter, layer_text],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/satellite-streets-v12",
        tooltip={"html": tooltip_html, "style": {"color": "white"}}
    )

    st.subheader(f"🌍 {titulo_mapa}")
    st.pydeck_chart(deck, use_container_width=True)

# ============================
#   Layout
# ============================
st.set_page_config(page_title="Risco de Incêndios", page_icon="🔥", layout="wide")
st.title("🔥 Risco de Incêndios")

arquivo = st.file_uploader("📥 Envie a base", type=["xls", "xlsx"])

if arquivo:

    df_processado = carregar_base_reme(arquivo)
    resultado = add_reclassificacoes(calcular_scores_mensais(df_processado, variaveis_talhao))

    resultado["classe_geral_idx"] = resultado["classe_geral_idx"].astype(float)

    # ============================
    #   MAPA ANUAL
    # ============================
    df_mapa_anual = (
        resultado
        .groupby("talhao", as_index=False)
        .agg(
            lat=("lat", "first"),
            lon=("lon", "first"),
            score_medio=("score", "mean"),
            classe_media_idx=("classe_geral_idx", "mean")
        )
    )

    df_mapa_anual = df_mapa_anual.dropna(subset=["lat", "lon"])

    # 🔹 Arredonda antes do tooltip
    df_mapa_anual["score_medio"] = df_mapa_anual["score_medio"].round(1)

    df_mapa_anual["color_rgb"] = df_mapa_anual["classe_media_idx"].apply(get_color_from_index)
    df_mapa_anual["classe_media"] = class_geral_from_score(df_mapa_anual["score_medio"]).astype(str)
    df_mapa_anual["risco_medio_extenso"] = df_mapa_anual["classe_media"].map(R_RISK_MAP)

    criar_mapa_pydeck(
        df_mapa_anual,
        "Risco Médio Anual por Talhão",
        "<b>Talhão:</b> {talhao}<br/>"
        "<b>Score (médio):</b> {score_medio}<br/>"
        "<b>Classe:</b> {classe_media} ({risco_medio_extenso})"
    )

    # ============================
    #   MAPA MENSAL
    # ============================
    mes_sel = st.selectbox("Selecione o mês:", MESES_COMPLETOS)
    mes_abrev = MAP_MES_COMPLETO_TO_ABREV[mes_sel]

    df_mensal = (
        resultado[resultado["mes"].str.startswith(mes_abrev)]
        .groupby("talhao", as_index=False)
        .agg(
            lat=("lat", "first"),
            lon=("lon", "first"),
            score_mensal=("score", "mean"),
            classe_idx=("classe_geral_idx", "mean")
        )
    )

    df_mensal = df_mensal.dropna(subset=["lat", "lon"])

    # 🔹 Arredonda antes do tooltip
    df_mensal["score_mensal"] = df_mensal["score_mensal"].round(1)

    df_mensal["color_rgb"] = df_mensal["classe_idx"].apply(get_color_from_index)
    df_mensal["classe_mensal"] = class_geral_from_score(df_mensal["score_mensal"]).astype(str)
    df_mensal["risco_mensal_extenso"] = df_mensal["classe_mensal"].map(R_RISK_MAP)

    criar_mapa_pydeck(
        df_mensal,
        f"Risco Médio Mensal - {mes_sel}",
        "<b>Talhão:</b> {talhao}<br/>"
        "<b>Score (mês):</b> {score_mensal}<br/>"
        "<b>Classe:</b> {classe_mensal} ({risco_mensal_extenso})"
    )

else:
    st.info("Envie a planilha para iniciar.")

