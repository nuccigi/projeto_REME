# app.py
import re
import os
import pandas as pd
import streamlit as st
import altair as alt
import pydeck as pdk

from calculo import calcular_scores_mensais, carregar_base_reme
from pesos import pesos_ahp  # importado, mas não exibimos a tabela
from variaveis_talhao import variaveis_talhao

# ============================================================
#  MAPBOX KEY (via Secrets ou env var) + fallback de estilo
# ============================================================
mapbox_key = None
if "MAPBOX_API_KEY" in st.secrets:
    mapbox_key = st.secrets["MAPBOX_API_KEY"]
elif os.getenv("MAPBOX_API_KEY"):
    mapbox_key = os.getenv("MAPBOX_API_KEY")

if mapbox_key:
    pdk.settings.mapbox_api_key = mapbox_key

MAP_STYLE_MAPBOX = "mapbox://styles/mapbox/satellite-streets-v12"
MAP_STYLE_FALLBACK = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"

# ============================================================
#   Constantes e Mapeamentos
# ============================================================
MESES_ABREVIADOS = ["jan", "fev", "mar", "abr", "mai", "jun",
                    "jul", "ago", "set", "out", "nov", "dez"]
MESES_COMPLETOS = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MAP_MES_ABREV_TO_COMPLETO = dict(zip(MESES_ABREVIADOS, MESES_COMPLETOS))
MAP_MES_COMPLETO_TO_ABREV = dict(zip(MESES_COMPLETOS, MESES_ABREVIADOS))

# Faixas de Risco
R_BINS = [0, 20, 40, 60, 80, 100]
R_LABELS = ["R1", "R2", "R3", "R4", "R5"]
R_MAP = {lab: i + 1 for i, lab in enumerate(R_LABELS)}
R_RISK_LABELS = ["Risco Muito Baixo", "Risco Baixo", "Risco Moderado", "Risco Médio", "Risco Alto"]
R_RISK_MAP = dict(zip(R_LABELS, R_RISK_LABELS))

# ============================================================
#   Helpers de ordenação
# ============================================================
def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.findall(r'\d+|\D+', str(s))]

# ============================================================
#   Helpers de classificação
# ============================================================
def class_geral_from_score(s: pd.Series) -> pd.Categorical:
    return pd.cut(s, bins=R_BINS, labels=R_LABELS, include_lowest=True, right=True)

def add_reclassificacoes(df_resultado: pd.DataFrame) -> pd.DataFrame:
    df = df_resultado.copy()
    df["classe_geral"] = class_geral_from_score(df["score"])
    df["classe_geral_idx"] = df["classe_geral"].map(R_MAP)
    return df

# ============================================================
#   Funções de Mapa (PyDeck)
# ============================================================
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

def criar_mapa_pydeck(df_mapa: pd.DataFrame, titulo_mapa: str, tooltip_html: str):
    if df_mapa is None or df_mapa.empty:
        st.info(f"Não há dados para exibir no mapa: {titulo_mapa}")
        return

    df_mapa = df_mapa.copy()
    df_mapa["lat"] = pd.to_numeric(df_mapa["lat"], errors="coerce")
    df_mapa["lon"] = pd.to_numeric(df_mapa["lon"], errors="coerce")
    df_mapa["talhao"] = df_mapa["talhao"].astype(str)

    df_mapa = df_mapa.dropna(subset=["lat", "lon"])

    if df_mapa.empty:
        st.info(f"Sem coordenadas válidas para exibir no mapa: {titulo_mapa}")
        return

    initial_lat = float(df_mapa["lat"].mean())
    initial_lon = float(df_mapa["lon"].mean())

    view_state = pdk.ViewState(
        latitude=initial_lat,
        longitude=initial_lon,
        zoom=12,
        pitch=0
    )

    layer_scatter = pdk.Layer(
        "ScatterplotLayer",
        data=df_mapa,
        get_position="[lon, lat]",
        get_color="color_rgb",
        get_radius=200,
        pickable=True,
        auto_highlight=True,
    )

    layer_text = pdk.Layer(
        "TextLayer",
        data=df_mapa,
        get_position="[lon, lat]",
        get_text="talhao",
        get_color=[255, 255, 255, 255],
        get_size=16,
        get_alignment_baseline="center",
        get_pixel_offset=[0, 0],
        pickable=False,
    )

    st.subheader(f"🌍 {titulo_mapa}")

    # Se tiver token, usa Mapbox (satélite). Se não tiver, usa fallback público.
    map_style = MAP_STYLE_MAPBOX if mapbox_key else MAP_STYLE_FALLBACK

    r = pdk.Deck(
        layers=[layer_scatter, layer_text],
        initial_view_state=view_state,
        map_style=map_style,
        tooltip={"html": tooltip_html, "style": {"color": "white"}},
    )

    st.pydeck_chart(r, use_container_width=True)

# ============================================================
#   Layout Streamlit
# ============================================================
st.set_page_config(page_title="Risco de Incêndios", page_icon="🔥", layout="wide")
st.title("🔥 Risco de Incêndios - Fazenda Sabiá e Lagoa dos Buritis")

# Debug leve (pode comentar depois)
# st.caption(f"Mapbox key carregada? {'SIM' if mapbox_key else 'NÃO'}")

st.markdown("### Legenda de Classificação de Risco")
col_legendas = st.columns(len(R_LABELS))

cores_hex = ["#228B22", "#ADFF2F", "#FFA500", "#FF4500", "#FF0000"]

for i, label in enumerate(R_LABELS):
    with col_legendas[i]:
        st.markdown(f"""
        <div style='background-color:{cores_hex[i]}; color:white; padding: 5px; border-radius: 5px; text-align: center;'>
            <b>{label}</b>
        </div>
        <p style='text-align: center; margin-top: 5px;'>{R_RISK_MAP[label]} </p>
        """, unsafe_allow_html=True)

st.markdown("---")
st.markdown("📂 Faça upload da base (.xls ou .xlsx) para calcular os scores de risco.")

arquivo = st.file_uploader("📥 Envie a base", type=["xls", "xlsx"])

if arquivo is not None:
    try:
        df_processado = carregar_base_reme(arquivo)
        st.success("Base carregada com sucesso.")

        resultado_raw = calcular_scores_mensais(df_processado, variaveis_talhao)
        resultado = add_reclassificacoes(resultado_raw)

        resultado["classe_geral_idx"] = pd.to_numeric(resultado["classe_geral_idx"], errors="coerce").astype(float)

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

        df_mapa_anual["talhao"] = df_mapa_anual["talhao"].astype(str)
        df_mapa_anual["lat"] = pd.to_numeric(df_mapa_anual["lat"], errors="coerce")
        df_mapa_anual["lon"] = pd.to_numeric(df_mapa_anual["lon"], errors="coerce")
        df_mapa_anual = df_mapa_anual.dropna(subset=["lat", "lon"])

        if not df_mapa_anual.empty:
            df_mapa_anual["color_rgb"] = df_mapa_anual["classe_media_idx"].apply(get_color_from_index)

        df_mapa_anual["classe_media"] = class_geral_from_score(df_mapa_anual["score_medio"]).astype(str)
        df_mapa_anual["risco_medio_extenso"] = df_mapa_anual["classe_media"].map(R_RISK_MAP)

        df_mapa_mensal_base = resultado.copy()

    except Exception as e:
        st.error(f"Erro ao processar a planilha: {e}")
        st.stop()

    talhoes = sorted(
        pd.Series(resultado["talhao"].astype(str)).dropna().unique().tolist(),
        key=natural_key
    )

    col_mapa_anual, col_mapa_mensal = st.columns(2)

    with col_mapa_mensal:
        ordem_meses_disponiveis = df_mapa_mensal_base["mes"].astype(str).unique().tolist()
        meses_abreviados_disponiveis = [m.split('_')[0] for m in ordem_meses_disponiveis]
        meses_selecionaveis = [
            MAP_MES_ABREV_TO_COMPLETO[m]
            for m in MESES_ABREVIADOS if m in meses_abreviados_disponiveis
        ]

        if meses_selecionaveis:
            mes_sel_completo = st.selectbox("Selecione o Mês para o Mapa de Risco:", meses_selecionaveis)
            mes_sel_abrev = MAP_MES_COMPLETO_TO_ABREV[mes_sel_completo]

            df_risco_mensal = (
                df_mapa_mensal_base[df_mapa_mensal_base["mes"].str.startswith(mes_sel_abrev)]
                .groupby("talhao", as_index=False)
                .agg(
                    lat=("lat", "first"),
                    lon=("lon", "first"),
                    score_mensal=("score", "mean"),
                    classe_geral_idx=("classe_geral_idx", "mean")
                )
            )

            df_risco_mensal["talhao"] = df_risco_mensal["talhao"].astype(str)
            df_risco_mensal["lat"] = pd.to_numeric(df_risco_mensal["lat"], errors="coerce")
            df_risco_mensal["lon"] = pd.to_numeric(df_risco_mensal["lon"], errors="coerce")
            df_risco_mensal = df_risco_mensal.dropna(subset=["lat", "lon"])

            if not df_risco_mensal.empty:
                df_risco_mensal["color_rgb"] = df_risco_mensal["classe_geral_idx"].apply(get_color_from_index)
                df_risco_mensal["classe_mensal"] = class_geral_from_score(df_risco_mensal["score_mensal"]).astype(str)
                df_risco_mensal["risco_mensal_extenso"] = df_risco_mensal["classe_mensal"].map(R_RISK_MAP)

                st.write("Talhões no mapa anual:", df_mapa_anual["talhao"].unique())
                st.write("Qtd talhões:", df_mapa_anual["talhao"].nunique())


                criar_mapa_pydeck(
                    df_risco_mensal,
                    f"Risco Médio Mensal em {mes_sel_completo.upper()}",
                    "<b>Talhão:</b> {talhao}<br/><b>Risco Mensal:</b> {score_mensal:.1f}<br/><b>Classe:</b> {classe_mensal} ({risco_mensal_extenso})"
                )
            else:
                st.info(f"Não há dados de risco para o mês de {mes_sel_completo.upper()}.")
        else:
            st.info("Não há meses válidos disponíveis para seleção.")

    with col_mapa_anual:
        criar_mapa_pydeck(
            df_mapa_anual,
            "Risco Médio Anual por Talhão",
            "<b>Talhão:</b> {talhao}<br/><b>Risco Médio:</b> {score_medio:.1f}<br/><b>Classe:</b> {classe_media} ({risco_medio_extenso})"
        )
        st.markdown("---")
        talhao_sel = st.selectbox("Selecione o talhão para Detalhes:", talhoes)

    st.markdown("---")
    st.subheader(f"Detalhes do Talhão {talhao_sel}:")

    df_talhao = resultado[resultado["talhao"].astype(str) == str(talhao_sel)].copy()

    col1, col2 = st.columns([3, 2])

    with col1:
        ordem_meses = MESES_ABREVIADOS
        df_t = df_talhao[df_talhao["mes"].str.startswith(tuple(ordem_meses))].copy()
        df_t["mes_simples"] = df_t["mes"].str.split('_').str[0].str.lower()
        df_t = df_t[df_t["mes_simples"].isin(ordem_meses)].copy()
        df_t["mes_simples"] = pd.Categorical(df_t["mes_simples"], categories=ordem_meses, ordered=True)
        df_t = df_t.sort_values("mes_simples")

        for col in ["classe_geral_idx", "score"]:
            df_t[col] = pd.to_numeric(df_t[col], errors='coerce')

        if df_t.empty:
            st.info("Não há dados válidos para este talhão.")
        else:
            base = df_t.groupby("mes_simples", as_index=False).agg(
                classe_geral_idx=("classe_geral_idx", "mean"),
                score=("score", "mean")
            )

            base["score"] = base["score"].astype(float)
            base["classe_geral"] = class_geral_from_score(base["score"]).astype(str)
            base["classe_geral_idx"] = class_geral_from_score(base["score"]).map(R_MAP)
            base["mes_completo"] = base["mes_simples"].map(MAP_MES_ABREV_TO_COMPLETO)

            ordem_meses_completos_para_eixo = [
                MAP_MES_ABREV_TO_COMPLETO[m] for m in ordem_meses if m in base["mes_simples"].unique()
            ]

            x_axis = alt.X(
                "mes_completo:O",
                scale=alt.Scale(domain=ordem_meses_completos_para_eixo),
                axis=alt.Axis(title="Mês", grid=False, labelAngle=0, labelFontSize=13)
            )

            st.subheader("📈 Risco médio histórico por Mês")

            y_geral = alt.Y(
                "classe_geral_idx:Q",
                scale=alt.Scale(domain=[1, 5]),
                axis=alt.Axis(title="Classe geral (R1–R5)", grid=False, ticks=True, values=[1, 2, 3, 4, 5])
            )

            graf_geral = (
                alt.Chart(base)
                .mark_circle(size=140)
                .encode(
                    x=x_axis,
                    y=y_geral,
                    color=alt.Color(
                        "classe_geral:N",
                        scale=alt.Scale(domain=R_LABELS,
                                        range=["#7fbf7b", "#c2e699", "#fec44f", "#fe9929", "#e31a1c"]),
                        legend=alt.Legend(title="Classe geral")
                    ),
                    tooltip=[
                        alt.Tooltip("mes_completo:O", title="Mês"),
                        alt.Tooltip("score:Q", title="Score", format=".1f"),
                        alt.Tooltip("classe_geral:N", title="Classe geral (0–100)")
                    ]
                )
                .properties(height=260)
            )

            rot_geral = (
                alt.Chart(base)
                .mark_text(align="center", dy=-12, fontSize=12)
                .encode(
                    x="mes_completo:O",
                    y="classe_geral_idx:Q",
                    text="classe_geral:N"
                )
            )

            st.altair_chart(graf_geral + rot_geral, use_container_width=True)

    with col2:
        resumo_anual = df_mapa_anual[df_mapa_anual["talhao"] == str(talhao_sel)].iloc[0]

        st.subheader("🏷️ Classificação Média Anual")

        classe_media = resumo_anual['classe_media']
        risco_extenso = resumo_anual['risco_medio_extenso']

        if classe_media in ["R1", "R2"]:
            st.success(f"🟢 **{risco_extenso}** ({classe_media})")
        elif classe_media in ["R3", "R4"]:
            st.warning(f"🟠 **{risco_extenso}** ({classe_media})")
        else:
            st.error(f"🔴 **{risco_extenso}** ({classe_media})")

        st.subheader("⚙️ Variáveis fixas do talhão")

        nomes_bonitos = {
            "umidade": "Umidade Relativa", "eucalipto": "Eucalipto",
            "precipitacao": "Precipitação", "temp_maxima": "Temperatura Máxima",
            "temp_media": "Temperatura Média", "area_umida": "Área Úmida",
            "represas_rios": "Represas / Rios", "estrada": "Estrada",
            "eletrica": "Rede Elétrica", "moradores": "Moradores",
            "cerrado": "Cerrado", "barreira_natural": "Barreira Natural"
        }

        attrs = variaveis_talhao.get(str(talhao_sel), {})

        if attrs:
            for nome, valor in attrs.items():
                nome_bonito = nomes_bonitos.get(nome, nome.replace("_", " ").title())
                if valor:
                    st.markdown(f"- ✅ **{nome_bonito}**")
                else:
                    st.markdown(f"- <span style='color:#ff4b4b'>❌ {nome_bonito}</span>", unsafe_allow_html=True)
        else:
            st.info("Nenhuma variável cadastrada para este talhão.")

else:
    st.info("Envie a planilha para iniciar o cálculo.")

