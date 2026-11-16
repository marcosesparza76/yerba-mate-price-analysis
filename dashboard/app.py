import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Executive Monitor | Yerba Mate", layout="wide")

# Ensamblaje seguro de Google Fonts para evitar recortes de URL
FONT_URL = "".join([
    "https", "://", "://googleapis.com?",
    "family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@600;700&display=swap"
])

st.markdown(f"""
<style>
    @import url('{FONT_URL}');

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #F9FAFB;
    }}
    h1, h2, h3 {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: -0.02em;
        font-weight: 700 !important;
    }}
    h1 {{ font-size: 1.85rem !important; color: #FFFFFF; margin-bottom: 0.2rem !important; }}
    h3 {{
        font-size: 1.0rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9CA3AF !important;
        margin-bottom: 1rem !important;
    }}
    div[data-testid="stMetric"] {{
        background-color: #111827;
        border: 1px solid #1F2937;
        border-top: 3px solid #10B981;
        padding: 18px 22px;
        border-radius: 6px;
    }}
    div[data-testid="stMetricLabel"] {{
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9CA3AF !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        font-variant-numeric: tabular-nums;
        color: #F9FAFB !important;
    }}
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent.parent
PATH_GONDOLA = BASE_DIR / "data" / "processed" / "yerba_gondola_procesada.csv"
PATH_MAESTRO = BASE_DIR / "data" / "processed" / "dataset_maestro_yerba.csv"

st.title("MONITOR EJECUTIVO DE PRECIOS Y CADENA DE VALOR | YERBA MATE")
st.caption("RELEVAMIENTO MULTICANAL (JUMBO • CARREFOUR • COTO) • DEFLACTACIÓN IPC (INDEC) • BRECHA ORIGEN-GÓNDOLA (CEPA / INYM)")

if not PATH_GONDOLA.exists() or not PATH_MAESTRO.exists():
    st.error("Datasets procesados no disponibles en 'data/processed/'. Ejecute el pipeline ETL.")
    st.stop()

df_gondola = pd.read_csv(PATH_GONDOLA)
df_maestro = pd.read_csv(PATH_MAESTRO)

if "supermercado" not in df_gondola.columns:
    df_gondola["supermercado"] = "Jumbo"
if "presentacion" not in df_gondola.columns:
    df_gondola["presentacion"] = df_gondola["peso_kg"].apply(
        lambda x: "1 Kg" if x == 1.0 else ("500/550 g" if x in (0.5, 0.55) else "Otro")
    )

# --- BARRA LATERAL ---
st.sidebar.markdown("### PARÁMETROS DE ANÁLISIS")

cadenas_disp = sorted(df_gondola["supermercado"].dropna().unique())
cadenas_sel = st.sidebar.multiselect("Cadenas Minoristas", cadenas_disp, default=cadenas_disp)

marcas_disp = sorted(df_gondola["marca"].dropna().unique())
marcas_sel = st.sidebar.multiselect("Marcas Comerciales", marcas_disp, default=marcas_disp)

pres_disp = sorted(df_gondola["presentacion"].dropna().unique())
pres_sel = st.sidebar.multiselect("Formato de Envase", pres_disp, default=pres_disp)

df_filtrado = df_gondola[
    (df_gondola["supermercado"].isin(cadenas_sel)) &
    (df_gondola["marca"].isin(marcas_sel)) &
    (df_gondola["presentacion"].isin(pres_sel))
]

# --- INDICADORES CLAVE (KPIs) ---
col1, col2, col3, col4 = st.columns(4)
promedio_kg = df_filtrado["precio_por_kg_ars"].mean() if not df_filtrado.empty else 0.0
mediana_kg = df_filtrado["precio_por_kg_ars"].median() if not df_filtrado.empty else 0.0
part_prod = df_maestro["participacion_productor_pct"].iloc[-1]

col1.metric("Precio Promedio Góndola", f"${promedio_kg:,.2f} / kg")
col2.metric("Mediana de Mercado", f"${mediana_kg:,.2f} / kg")
col3.metric("Participación Productor", f"{part_prod:.1f}%", delta="-18.8 pp vs Oct-23", delta_color="inverse")
col4.metric("Muestra Activa (SKUs)", f"{len(df_filtrado)} unidades")

st.markdown("<hr style='border: 0; border-top: 1px solid #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

if df_filtrado.empty:
    st.warning("No hay productos que coincidan con los filtros seleccionados. Ajuste los parámetros en el panel izquierdo.")
    st.stop()

# --- FILA 1 DE GRÁFICOS ---
c_izq, c_der = st.columns(2)

with c_izq:
    st.subheader("Comparativa por Cadena Minorista (Mediana ARS / Kg)")
    df_cad = df_filtrado.groupby("supermercado", as_index=False)["precio_por_kg_ars"].median().sort_values("precio_por_kg_ars")
    fig_cad = px.bar(
        df_cad, x="supermercado", y="precio_por_kg_ars",
        text_auto=",.0f", color="supermercado",
        color_discrete_sequence=["#059669", "#10B981", "#D97706"],
        template="plotly_dark",
        labels={"precio_por_kg_ars": "Mediana ARS / Kg", "supermercado": ""}
    )
    fig_cad.update_traces(textposition="outside", width=0.45)
    fig_cad.update_layout(
        font=dict(family="Inter", color="#D1D5DB"),
        showlegend=False, height=400,
        margin=dict(l=10, r=10, t=25, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="#1F2937", range=[0, df_cad["precio_por_kg_ars"].max() * 1.18])
    )
    st.plotly_chart(fig_cad, use_container_width=True)

with c_der:
    st.subheader("Precio Real (Base Dic-23) vs. Participación Primaria")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_maestro["anio_mes"], y=df_maestro["participacion_productor_pct"],
        name="Participación Productor (%)", marker_color="#10B981", opacity=0.85, yaxis="y1"
    ))
    fig2.add_trace(go.Scatter(
        x=df_maestro["anio_mes"], y=df_maestro["precio_gondola_real_dic23"],
        name="Precio Real Góndola ($ Dic-23)", mode="lines+markers",
        line=dict(color="#F59E0B", width=2.5), marker=dict(size=7), yaxis="y2"
    ))
    fig2.update_layout(
        font=dict(family="Inter", color="#D1D5DB"),
        template="plotly_dark",
        xaxis=dict(type="category", showgrid=False),
        yaxis=dict(title="Participación (%)", range=[0, 50], showgrid=True, gridcolor="#1F2937"),
        yaxis2=dict(title="ARS Constantes (Dic-23)", overlaying="y", side="right", range=[0, 4000], showgrid=False),
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
        height=400, margin=dict(l=10, r=10, t=25, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- FILA 2: RANKING DE MARCAS Y MATRIZ ---
st.subheader("Top 15 Marcas Relevadas (Promedio ARS / Kg)")
df_rank = (
    df_filtrado.groupby("marca", as_index=False)["precio_por_kg_ars"]
    .mean()
    .sort_values("precio_por_kg_ars", ascending=True)
    .tail(15)
)
fig1 = px.bar(
    df_rank, x="precio_por_kg_ars", y="marca", orientation="h",
    text_auto=",.0f", color="precio_por_kg_ars",
    color_continuous_scale=["#065F46", "#10B981", "#D97706"],
    template="plotly_dark",
    labels={"precio_por_kg_ars": "ARS / Kg", "marca": ""}
)
fig1.update_traces(textposition="outside")
fig1.update_layout(
    font=dict(family="Inter", color="#D1D5DB"),
    showlegend=False, coloraxis_showscale=False, height=450,
    margin=dict(l=10, r=40, t=10, b=20),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=True, gridcolor="#1F2937", range=[0, df_rank["precio_por_kg_ars"].max() * 1.15]),
    yaxis=dict(showgrid=False)
)
st.plotly_chart(fig1, use_container_width=True)

st.subheader("Matriz de Relevamiento Minorista (Jumbo • Carrefour • Coto)")
st.dataframe(
    df_filtrado[["fecha_extraccion", "supermercado", "marca", "producto", "peso_kg", "precio_gondola_ars", "precio_por_kg_ars"]],
    use_container_width=True,
    hide_index=True
)

st.dataframe(
    df_filtrado[["fecha_extraccion", "supermercado", "marca", "producto", "peso_kg", "precio_gondola_ars", "precio_por_kg_ars"]],
    use_container_width=True,
    hide_index=True
)
