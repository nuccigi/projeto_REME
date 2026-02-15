# calculo.py
import numpy as np
import pandas as pd
from pesos import pesos_ahp


# ============================================================
#  NOVA FUNÇÃO: tratamento automático da base Consolidada_REME
# ============================================================
def carregar_base_reme(arquivo_excel):
    """
    Lê automaticamente o arquivo Consolidada_REME (com múltiplas abas)
    e retorna um DataFrame consolidado no formato longo:
    Pontos | Mes_Ano | Umidade_Relativa | Temperatura_Max | Temperatura_Media | Precipitacao
    """

    # === Leitura das abas ===
    abas = pd.ExcelFile(arquivo_excel).sheet_names

    def ler_aba(nome):
        for aba in abas:
            if nome.lower() in aba.lower():
                return pd.read_excel(arquivo_excel, sheet_name=aba)
        return None

    df_precipitacao = ler_aba("Precipitacao_total")
    df_temp_max = ler_aba("Temp_max")
    df_temp_media = ler_aba("Temp_média_final")
    df_umidade = ler_aba("Umidade_Relativa")

    # se alguma aba não for encontrada, erro amigável
    if df_precipitacao is None or df_temp_max is None or df_temp_media is None or df_umidade is None:
        raise ValueError("❌ Não foram encontradas todas as abas esperadas (Precipitacao_total, Temp_max, Temp_média_final, Umidade_Relativa).")

    # === padroniza coluna de identificação e guarda LAT/LON ===
    coords = None

    for df in [df_precipitacao, df_temp_max, df_temp_media, df_umidade]:
        if "Name" in df.columns:
            df.rename(columns={"Name": "Pontos"}, inplace=True)

        # salva as coordenadas só uma vez
        if ("LAT" in df.columns) and ("LON" in df.columns) and coords is None:
            coords = df[["Pontos", "LAT", "LON"]].drop_duplicates()

        # depois retira das abas para não atrapalhar o melt
        for col in ["LAT", "LON"]:
            if col in df.columns:
                df.drop(columns=[col], inplace=True)


    # === Função auxiliar para derreter ===
    def processar_df(df, value_name):
        df_longo = df.melt(id_vars="Pontos", var_name="Mes_Ano", value_name=value_name)
        meses_map = {
            "jan": "jan", "fev": "fev", "mar": "mar", "abr": "abr", "mai": "mai",
            "jun": "jun", "jul": "jul", "ago": "ago", "set": "set", "out": "out",
            "nov": "nov", "dez": "dez", "abril": "abr", "março": "mar", "março.": "mar", "dec": "dez"
        }

        # extrai nome padronizado de mês e ano
        df_longo["Mes_Ano"] = (
            df_longo["Mes_Ano"].astype(str).str.lower()
            .str.replace("tmin_", "").str.replace("t_max_", "").str.replace("umid_", "")
            .str.replace("precipitacao_", "").str.replace("temp_", "")
            .str.extract(r"([a-zç]+)_(\d{4})")[0] + "_" +
            df_longo["Mes_Ano"].astype(str).str.extract(r"([a-zç]+)_(\d{4})")[1]
        )
        df_longo["Mes_Ano"] = df_longo["Mes_Ano"].fillna("")

        # corrige abreviações de mês
        df_longo["Mes_Ano"] = df_longo["Mes_Ano"].apply(
            lambda x: f"{meses_map.get(x.split('_')[0], x.split('_')[0])}_{x.split('_')[1]}"
            if "_" in x else x
        )

        return df_longo

    # === Processa cada aba ===
    df_precipitacao_longo = processar_df(df_precipitacao, "Precipitacao")
    df_temp_max_longo = processar_df(df_temp_max, "Temperatura_Max")
    df_temp_media_longo = processar_df(df_temp_media, "Temperatura_Media")
    df_umidade_longo = processar_df(df_umidade, "Umidade_Relativa")

    # === Junta todas ===
    df_consolidado = (
        df_precipitacao_longo
        .merge(df_temp_max_longo, on=["Pontos", "Mes_Ano"], how="outer")
        .merge(df_temp_media_longo, on=["Pontos", "Mes_Ano"], how="outer")
        .merge(df_umidade_longo, on=["Pontos", "Mes_Ano"], how="outer")
    )

    df_consolidado.rename(columns={
        "Pontos": "talhao",
        "Mes_Ano": "mes",
        "Temperatura_Max": "temp_maxima",
        "Temperatura_Media": "temp_media",
        "Umidade_Relativa": "umidade",
        "Precipitacao": "precipitacao"
    }, inplace=True)

    # 👉 junta LAT/LON se existirem
    if coords is not None:
        coords = coords.rename(columns={
            "Pontos": "talhao",
            "LAT": "lat",
            "LON": "lon"
        })
        df_consolidado = df_consolidado.merge(coords, on="talhao", how="left")

    return df_consolidado


# ============================================================
#   FUNÇÕES DO MODELO AHP (inalteradas)
# ============================================================
def normalizar_escala(v: pd.Series, inverter=False) -> pd.Series:
    v = v.astype(float)
    vmin, vmax = v.min(), v.max()
    if vmax == vmin:
        out = pd.Series(0.0, index=v.index)
    else:
        out = (v - vmin) / (vmax - vmin)
    if inverter:
        out = 1 - out
    return out

def calcular_scores_mensais(df: pd.DataFrame, variaveis_talhao: dict) -> pd.DataFrame:
    """
    Calcula o score AHP médio por MÊS (jan, fev, mar...) agregando os dados históricos.
    Exemplo: usa todos os junhos de todos os anos para estimar o risco médio de junho.
    """

    df = df.copy()

    # extrai só o nome do mês (ex: "junho_2022" -> "junho")
    df["mes_simplificado"] = (
        df["mes"]
        .astype(str)
        .str.extract(r"([a-zç]+)")[0]
        .str.lower()
        .replace({
            "janeiro": "jan", "fevereiro": "fev", "março": "mar", "abril": "abr",
            "maio": "mai", "junho": "jun", "julho": "jul", "agosto": "ago",
            "setembro": "set", "outubro": "out", "novembro": "nov", "dezembro": "dez"
        })
    )

    # 🔹 garante que variáveis climáticas e coords são numéricas
    for col in ["umidade", "precipitacao", "temp_maxima", "temp_media", "lat", "lon"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 🔹 dicionário flexível de agregações
    agg_dict = {
        "umidade": ("umidade", "mean"),
        "precipitacao": ("precipitacao", "mean"),
        "temp_maxima": ("temp_maxima", "mean"),
        "temp_media": ("temp_media", "mean"),
    }

    # adiciona lat/lon se existirem
    if "lat" in df.columns and "lon" in df.columns:
        agg_dict["lat"] = ("lat", "first")
        agg_dict["lon"] = ("lon", "first")

    # médias históricas por mês (independente do ano)
    ag = df.groupby(["talhao", "mes_simplificado"], as_index=False).agg(**agg_dict)

    # normalizações globais (todos os meses juntos)
    ag["umidade_n"] = normalizar_escala(ag["umidade"], inverter=True)
    ag["precipitacao_n"] = normalizar_escala(ag["precipitacao"], inverter=True)
    ag["temp_maxima_n"] = normalizar_escala(ag["temp_maxima"])
    ag["temp_media_n"] = normalizar_escala(ag["temp_media"])

    # variáveis fixas do talhão
    bool_vars = ["eucalipto", "area_umida", "represas_rios", "estrada", "eletrica", "moradores", "cerrado"]
    for var in bool_vars:
        ag[var] = ag["talhao"].map(
            lambda t: bool(variaveis_talhao.get(str(t), {}).get(var, False))
        ).astype(int)

    # pesos e cálculo
    ordem = list(pesos_ahp.keys())
    valores_cols = {
        "umidade": "umidade_n",
        "precipitacao": "precipitacao_n",
        "temp_maxima": "temp_maxima_n",
        "temp_media": "temp_media_n",
        "eucalipto": "eucalipto",
        "area_umida": "area_umida",
        "represas_rios": "represas_rios",
        "estrada": "estrada",
        "eletrica": "eletrica",
        "moradores": "moradores",
        "cerrado": "cerrado",
    }

    X = np.column_stack([ag[valores_cols[k]].to_numpy(float) for k in ordem])
    w = np.array([pesos_ahp[k] for k in ordem], float)
    s_bruto = (X * w).sum(axis=1)

    # normalização 0–100
    s_min, s_max = (np.zeros_like(w) * w).sum(), (np.ones_like(w) * w).sum()
    mn, mx = min(s_min, s_max), max(s_min, s_max)
    s_final = (s_bruto - mn) / (mx - mn) * 100 if mx != mn else np.zeros_like(s_bruto)
    s_final = np.clip(s_final, 0, 100)

    # monta saída
    cols_out = ["talhao", "mes_simplificado"]
    if "lat" in ag.columns and "lon" in ag.columns:
        cols_out += ["lat", "lon"]

    out = ag[cols_out].copy()
    out.rename(columns={"mes_simplificado": "mes"}, inplace=True)
    out["score"] = s_final

    return out.sort_values(["talhao", "mes"]).reset_index(drop=True)
