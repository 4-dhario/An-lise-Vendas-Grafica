
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Análise de Vendas | Gráfica",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

# ---------- ESTILO RESPONSIVO ----------
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    padding-left: min(5%, 2rem);
    padding-right: min(5%, 2rem);
}
h1 {
    font-size: clamp(1.6rem, 4vw, 2.5rem);
}
[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,0.25);
    padding: 12px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)


# ---------- CONFIGURAÇÃO ----------
COLUNAS = [
    "data", "servico", "quantidade", "preco_unitario"
]

st.title("📊 Sistema de Análise de Vendas")
st.caption("Gráfica e Design | Painel estatístico")

st.sidebar.header("Menu de análise")

pagina = st.sidebar.radio(
    "Seleciona uma opção",
    [
        "Painel geral",
        "Consultar vendas",
        "Sobre o sistema"
    ]
)

ficheiro = st.sidebar.file_uploader(
    "Importar ficheiro CSV",
    type=["csv"]
)


# ---------- DADOS DE EXEMPLO ----------
def dados_exemplo():
    return pd.DataFrame({
        "data": [
            "2026-01-05", "2026-01-12",
            "2026-02-03", "2026-02-15",
            "2026-03-02", "2026-03-10",
            "2026-04-04", "2026-04-18",
            "2026-05-06", "2026-05-20"
        ],
        "servico": [
            "Flyers", "Cartões de visita",
            "Logótipos", "Banners",
            "Flyers", "Logótipos",
            "Banners", "Cartões de visita",
            "Flyers", "Banners"
        ],
        "quantidade": [
            100, 200, 2, 3, 150,
            1, 4, 250, 300, 2
        ],
        "preco_unitario": [
            50, 20, 15000, 12000, 45,
            18000, 10000, 18, 40, 14000
        ]
    })


# ---------- CARREGAMENTO E VALIDAÇÃO ----------
try:
    if ficheiro is not None:
        df = pd.read_csv(ficheiro)
    elif Path("vendas_grafica.csv").exists():
        df = pd.read_csv("vendas_grafica.csv")
    else:
        df = dados_exemplo()
        st.info(
            "A utilizar dados de exemplo simulados. "
            "Importa o teu CSV para analisar outros dados."
        )

    df.columns = df.columns.str.strip().str.lower()

    if not set(COLUNAS).issubset(df.columns):
        st.error(
            "O CSV deve conter as colunas: data, servico, "
            "quantidade e preco_unitario."
        )
        st.stop()

    df = df[COLUNAS].copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["quantidade"] = pd.to_numeric(
        df["quantidade"], errors="coerce"
    )
    df["preco_unitario"] = pd.to_numeric(
        df["preco_unitario"], errors="coerce"
    )
    df["servico"] = df["servico"].astype("string").str.strip()

    if df.empty:
        st.warning("O ficheiro não contém vendas.")
        st.stop()

    if df.isna().any().any():
        st.error(
            "Foram encontrados campos vazios ou inválidos. "
            "Corrige o CSV e tenta novamente."
        )
        st.stop()

    if (df["servico"] == "").any():
        st.error("Existe um serviço sem nome.")
        st.stop()

    if (df["quantidade"] <= 0).any():
        st.error("As quantidades devem ser superiores a zero.")
        st.stop()

    if (df["preco_unitario"] <= 0).any():
        st.error("Os preços devem ser superiores a zero.")
        st.stop()

    df["valor_total"] = (
        df["quantidade"] * df["preco_unitario"]
    )
    df["mes"] = df["data"].dt.to_period("M").astype(str)

except Exception as erro:
    st.error(f"Não foi possível carregar os dados: {erro}")
    st.stop()


# ---------- FILTROS ----------
st.sidebar.subheader("Filtros")

servicos = sorted(df["servico"].unique().tolist())

servicos_escolhidos = st.sidebar.multiselect(
    "Serviços",
    options=servicos,
    default=servicos
)

data_min = df["data"].min().date()
data_max = df["data"].max().date()

periodo = st.sidebar.date_input(
    "Período de análise",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max
)

filtrado = df[df["servico"].isin(servicos_escolhidos)].copy()

if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
    inicio, fim = periodo
    filtrado = filtrado[
        filtrado["data"].dt.date.between(inicio, fim)
    ]

if filtrado.empty:
    st.warning(
        "Não existem vendas para os filtros selecionados."
    )
    st.stop()


# ---------- PAINEL GERAL ----------
if pagina == "Painel geral":
    st.subheader("Resumo estatístico")

    total_vendas = len(filtrado)
    faturacao = filtrado["valor_total"].sum()
    media = filtrado["valor_total"].mean()
    unidades = filtrado["quantidade"].sum()

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    c1.metric("Número de vendas", f"{total_vendas:,}")
    c2.metric("Faturação total", f"{faturacao:,.2f}")
    c3.metric("Venda média", f"{media:,.2f}")
    c4.metric("Quantidade vendida", f"{unidades:,.0f}")

    st.divider()
    st.subheader("Análise gráfica")

    por_servico = (
        filtrado.groupby("servico", as_index=False)["valor_total"]
        .sum()
        .sort_values("valor_total", ascending=False)
    )

    por_mes = (
        filtrado.groupby("mes", as_index=False)["valor_total"]
        .sum()
        .sort_values("mes")
    )

    st.markdown("**Faturação por serviço**")
    grafico_servicos = px.bar(
        por_servico,
        x="servico",
        y="valor_total",
        labels={
            "servico": "Serviço",
            "valor_total": "Faturação"
        },
        title="Comparação da faturação por serviço"
    )
    grafico_servicos.update_layout(
        autosize=True,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    st.plotly_chart(
        grafico_servicos,
        use_container_width=True
    )

    st.markdown("**Evolução mensal**")
    grafico_mensal = px.line(
        por_mes,
        x="mes",
        y="valor_total",
        markers=True,
        labels={
            "mes": "Mês",
            "valor_total": "Faturação"
        },
        title="Faturação ao longo dos meses"
    )
    grafico_mensal.update_layout(
        autosize=True,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    st.plotly_chart(
        grafico_mensal,
        use_container_width=True
    )

    st.subheader("Principais resultados")

    melhor = por_servico.iloc[0]

    st.write(
        f"O serviço com maior faturação no período selecionado "
        f"foi **{melhor['servico']}**, com "
        f"**{melhor['valor_total']:,.2f}**."
    )

    st.caption(
        "Os indicadores dependem dos dados e filtros selecionados. "
        "A faturação não corresponde necessariamente ao lucro."
    )


# ---------- CONSULTAR VENDAS ----------
elif pagina == "Consultar vendas":
    st.subheader("Registo de vendas")

    tabela = filtrado[
        [
            "data", "servico", "quantidade",
            "preco_unitario", "valor_total"
        ]
    ].sort_values("data", ascending=False).copy()

    tabela["data"] = tabela["data"].dt.strftime("%Y-%m-%d")

    tabela = tabela.rename(columns={
        "data": "Data",
        "servico": "Serviço",
        "quantidade": "Quantidade",
        "preco_unitario": "Preço unitário",
        "valor_total": "Valor total"
    })

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True
    )

    csv_saida = tabela.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "Descarregar vendas filtradas",
        data=csv_saida,
        file_name="vendas_analisadas.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.write(f"Registos apresentados: {len(tabela)}")


# ---------- SOBRE ----------
elif pagina == "Sobre o sistema":
    st.subheader("Sobre o projeto")

    st.write("""
    Este sistema foi desenvolvido em Python para apoiar a análise
    estatística das vendas de uma gráfica e empresa de design.

    Funcionalidades:
    - Cálculo de indicadores de vendas;
    - Análise da faturação por serviço;
    - Análise mensal;
    - Filtragem por serviço e período;
    - Consulta e exportação de dados.
    """)

    st.warning(
        "Os dados de exemplo são simulados e servem apenas "
        "para demonstrar o funcionamento do sistema."
    )

st.divider()
st.caption(
    "Projeto académico | Sistema de análise estatística de vendas"
)
