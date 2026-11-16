import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# Configuración de página
st.set_page_config(page_title="Monitor Precios Yerba Mate", page_icon="🧉", layout="wide")

# Estilos CSS personalizados para tarjetas KPI y estética oscura
st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background-color: #1A212B;
        border-left: 4px solid #2ECC71;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).resolve().parent.parent
PATH_GONDOLA = BASE_DIR / "data" / "processed" / "yerba_gondola_procesada.csv"
PATH_MAESTRO = BASE_DIR / "data" / "processed" / "dataset_maestro_yerba.csv"

st.title("🧉 Monitor de Precios y Análisis Econométrico: Yerba Mate")
st.markdown("Análisis de dispersión en góndola (**Jumbo Argentina**), evolución real deflactada por **IPC (INDEC)** y brecha productor-góndola (**CEPA / INYM**).")

if not PATH_GONDOLA.exists() or not PATH_MAESTRO.exists():
    st.error("No se encontraron los archivos procesados en 'data/processed/'. Ejecutá primero el pipeline ETL.")
    st.stop()

df_gondola = pd.read_csv(PATH_GONDOLA)
df_maestro = pd.read_csv(PATH_MAESTRO)

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🌿 Filtros de Góndola")
marcas_disp = sorted(df_gondola["marca"].unique())
marcas_sel = st.sidebar.multiselect("Seleccionar Marcas:", marcas_disp, default=marcas_disp)

pres_disp = sorted(df_gondola["presentacion"].unique())
pres_sel = st.sidebar.multiselect("Presentación:", pres_disp, default=pres_disp)

df_filtrado = df_gondola[(df_gondola["marca"].isin(marcas_sel)) & (df_gondola["presentacion"].isin(pres_sel))]

# --- TARJETAS KPI ---
col1, col2, col3, col4 = st.columns(4)
promedio_kg = df_filtrado["precio_por_kg_ars"].mean() if not df_filtrado.empty else 0
mediana_kg = df_filtrado["precio_por_kg_ars"].median() if not df_filtrado.empty else 0
part_prod = df_maestro["participacion_productor_pct"].iloc[-1]

col1.metric("Precio Promedio / Kg", f"${promedio_kg:,.2f}")
col2.metric("Precio Mediano / Kg", f"${mediana_kg:,.2f}")
col3.metric("Participación Productor", f"{part_prod:.1f}%", delta="-18.8% vs Oct-23", delta_color="inverse")
col4.metric("Presentaciones Analizadas", len(df_filtrado))

st.divider()

# --- GRÁFICOS INTERACTIVOS (TEMA OSCURO) ---
c_izq, c_der = st.columns(2)

with c_izq:
    st.subheader("📊 Ranking de Precios por Kg según Marca")
    if not df_filtrado.empty:
        df_rank = df_filtrado.groupby("marca", as_index=False)["precio_por_kg_ars"].mean().sort_values("precio_por_kg_ars")
        fig1 = px.bar(
            df_rank, x="precio_por_kg_ars", y="marca", orientation="h",
            text_auto=".0f", color="precio_por_kg_ars",
            color_continuous_scale=["#1E8449", "#2ECC71", "#F1C40F", "#E67E22"],
            template="plotly_dark",
            labels={"precio_por_kg_ars": "Precio por Kg (ARS)", "marca": "Marca"}
        )
        fig1.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            height=450,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig1, use_container_width=True)

with c_der:
    st.subheader("📈 Precio Real (IPC) vs. Participación del Productor")
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_maestro["anio_mes"], y=df_maestro["participacion_productor_pct"],
        name="Participación Productor (%)", marker_color="#2ECC71", opacity=0.8, yaxis="y1"
    ))
    fig2.add_trace(go.Scatter(
        x=df_maestro["anio_mes"], y=df_maestro["precio_gondola_real_dic23"],
        name="Precio Real Góndola ($ Dic-23)", mode="lines+markers",
        line=dict(color="#F39C12", width=3), marker=dict(size=8), yaxis="y2"
    ))
    fig2.update_layout(
        template="plotly_dark",
        xaxis=dict(type="category"),
        yaxis=dict(title="Participación Productor (%)", range=[0, 45]),
        yaxis2=dict(title="Precio Real ($ Dic-23)", overlaying="y", side="right", range=[1000, 4000]),
        legend=dict(orientation="h", y=1.12),
        height=450,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- TABLA DE DATOS ---
st.subheader("📋 Detalle de Precios Relevados en Góndola")
st.dataframe(
    df_filtrado[["fecha_extraccion", "marca", "producto", "peso_kg", "precio_gondola_ars", "precio_por_kg_ars"]],
    use_container_width=True,
    hide_index=True
)
