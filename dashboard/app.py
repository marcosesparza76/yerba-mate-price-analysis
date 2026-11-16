import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Configuración de página
st.set_page_config(page_title="Executive Monitor | Yerba Mate", layout="wide")

# Tipografía ejecutiva (Plus Jakarta Sans & Inter) y estilos de directorio
st.markdown("""
<style>
    @import url('https://googleapis.com');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #F9FAFB;
    }

    h1, h2, h3 {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: -0.02em;
        font-weight: 700 !important;
    }

    h1 {
        font-size: 1.85rem !important;
        color: #FFFFFF;
        margin-bottom: 0.2rem !important;
    }

    h3 {
        font-size: 1.05rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9CA3AF !important;
        margin-bottom: 1rem !important;
    }

    /* Tarjetas KPI estilo reporte financiero */
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-top: 3px solid #10B981;
        padding: 18px 22px;
        border-radius: 6px;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #9CA3AF !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        font-variant-numeric: tabular-nums;
        color: #F9FAFB !important;
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent.parent
PATH_GONDOLA = BASE_DIR / "data" / "processed" / "yerba_gondola_procesada.csv"
PATH_MAESTRO = BASE_DIR / "data" / "processed" / "dataset_maestro_yerba.csv"

st.title("MONITOR EJECUTIVO DE PRECIOS Y CADENA DE VALOR | YERBA MATE")
st.caption("INTELIGENCIA DE MERCADO MINORISTA (JUMBO) • DEFLACTACIÓN IPC (INDEC) • BRECHA ORIGEN-GÓNDOLA (CEPA / INYM)")

if not PATH_GONDOLA.exists() or not PATH_MAESTRO.exists():
    st.error("Datasets procesados no disponibles en 'data/processed/'. Ejecute el pipeline ETL.")
    st.stop()

df_gondola = pd.read_csv(PATH_GONDOLA)
df_maestro = pd.read_csv(PATH_MAESTRO)

# --- BARRA LATERAL ---
st.sidebar.markdown("### PARÁMETROS DE ANÁLISIS")
marcas_disp = sorted(df_gondola["marca"].unique())
marcas_sel = st.sidebar.multiselect("Marcas Comerciales", marcas_disp, default=marcas_disp)

pres_disp = sorted(df_gondola["presentacion"].unique())
pres_sel = st.sidebar.multiselect("Formato de Envase", pres_disp, default=pres_disp)

df_filtrado = df_gondola[(df_gondola["marca"].isin(marcas_sel)) & (df_gondola["presentacion"].isin(pres_sel))]

# --- INDICADORES CLAVE (KPIs) ---
col1, col2, col3, col4 = st.columns(4)
promedio_kg = df_filtrado["precio_por_kg_ars"].mean() if not df_filtrado.empty else 0
mediana_kg = df_filtrado["precio_por_kg_ars"].median() if not df_filtrado.empty else 0
part_prod = df_maestro["participacion_productor_pct"].iloc[-1]

col1.metric("Precio Promedio Góndola", f"${promedio_kg:,.2f} / kg")
col2.metric("Mediana de Mercado", f"${mediana_kg:,.2f} / kg")
col3.metric("Participación Productor", f"{part_prod:.1f}%", delta="-18.8 pp vs Oct-23", delta_color="inverse")
col4.metric("Muestra Activa (SKUs)", f"{len(df_filtrado)} unidades")

st.markdown("<hr style='border: 0; border-top: 1px solid #1F2937; margin: 1.5rem 0;'>", unsafe_allow_html=True)

# --- VISUALIZACIONES EJECUTIVAS ---
c_izq, c_der = st.columns(2)

with c_izq:
    st.subheader("Dispersión de Precios por Marca (ARS / Kg)")
    if not df_filtrado.empty:
        df_rank = df_filtrado.groupby("marca", as_index=False)["precio_por_kg_ars"].mean().sort_values("precio_por_kg_ars")
        fig1 = px.bar(
            df_rank, x="precio_por_kg_ars", y="marca", orientation="h",
            text_auto=",.0f", color="precio_por_kg_ars",
            color_continuous_scale=["#065F46", "#10B981", "#D97706"],
            template="plotly_dark",
            labels={"precio_por_kg_ars": "ARS / Kg", "marca": ""}
        )
        fig1.update_traces(textposition="outside", textfont=dict(family="Inter", size=11, color="#D1D5DB"))
        fig1.update_layout(
            font=dict(family="Inter", color="#D1D5DB"),
            showlegend=False,
            coloraxis_showscale=False,
            height=440,
            margin=dict(l=10, r=40, t=10, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="#1F2937", zeroline=False),
            yaxis=dict(showgrid=False)
        )
        st.plotly_chart(fig1, use_container_width=True)

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
        yaxis=dict(title="Participación (%)", range=[0, 45], showgrid=True, gridcolor="#1F2937"),
        yaxis2=dict(title="ARS Constantes (Dic-23)", overlaying="y", side="right", range=[1000, 4000], showgrid=False),
        legend=dict(orientation="h", y=1.12, x=0, font=dict(size=11)),
        height=440,
        margin=dict(l=10, r=10, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- MATRIZ DE DATOS ---
st.subheader("Matriz de Relevamiento Minorista")
st.dataframe(
    df_filtrado[["fecha_extraccion", "marca", "producto", "peso_kg", "precio_gondola_ars", "precio_por_kg_ars"]],
    use_container_width=True,
    hide_index=True
)

