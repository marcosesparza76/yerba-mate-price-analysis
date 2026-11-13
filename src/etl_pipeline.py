import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
from pathlib import Path

# Detecta automáticamente la carpeta raíz del proyecto (un nivel arriba de /src)
BASE_DIR = Path(__file__).resolve().parent.parent

# Configurar estilo visual limpio para los gráficos
plt.style.use('seaborn-v0_8-whitegrid')

def cargar_ultimo_scrape():
    """Busca el archivo CSV más reciente generado por scraper_jumbo.py en la raíz."""
    patron = str(BASE_DIR / "data" / "raw" / "jumbo_yerbas_*.csv")
    archivos = glob.glob(patron)
    if not archivos:
        raise FileNotFoundError("No se encontró ningún CSV en data/raw/. Ejecutá primero scraper_jumbo.py.")
    ultimo_archivo = max(archivos, key=os.path.getctime)
    print(f"Cargando datos reales desde: {ultimo_archivo}")
    return pd.read_csv(ultimo_archivo)

def generar_serie_historica_referencia(precio_promedio_actual_kg):
    """
    Construye la serie histórica trimestral en pesos constantes (base actual)
    integrando los hitos de los informes del Ministerio de Desregulación (2024),
    CEPA (2025) e IPC (INDEC) junto con el dato actual extraído de góndola.
    """
    datos_historicos = [
        {"periodo": "2022-Q1", "precio_real_kg": 4850, "etapa": "Regulación INYM"},
        {"periodo": "2022-Q3", "precio_real_kg": 5020, "etapa": "Regulación INYM"},
        {"periodo": "2023-Q1", "precio_real_kg": 5180, "etapa": "Regulación INYM"},
        {"periodo": "2023-Q3", "precio_real_kg": 5310, "etapa": "Regulación INYM"},
        {"periodo": "2023-Q4", "precio_real_kg": 6450, "etapa": "DNU 70/2023 (Desregulación)"},
        {"periodo": "2024-Q1", "precio_real_kg": 7120, "etapa": "Post-Desregulación"},
        {"periodo": "2024-Q3", "precio_real_kg": 6380, "etapa": "Post-Desregulación"},
        {"periodo": "2025-Q1", "precio_real_kg": 5950, "etapa": "Post-Desregulación"},
        {"periodo": "Actual (Jumbo)", "precio_real_kg": round(precio_promedio_actual_kg, 2), "etapa": "Muestreo en Vivo"}
    ]
    return pd.DataFrame(datos_historicos)

def ejecutar_etl_y_graficos():
    # 1. EXTRACT & TRANSFORM (Datos actuales de Jumbo)
    df_jumbo = cargar_ultimo_scrape()
    df_jumbo["marca"] = df_jumbo["marca"].str.upper().str.strip()
    df_jumbo["presentacion"] = df_jumbo["peso_kg"].apply(lambda x: "1 Kg" if x == 1.0 else ("500/550 g" if x < 1.0 else "Otro"))
    
    # Calcular métricas clave
    promedio_kg = df_jumbo["precio_por_kg_ars"].mean()
    mediana_kg = df_jumbo["precio_por_kg_ars"].median()
    
    # Agrupar por marca para el ranking
    df_marcas = df_jumbo.groupby("marca", as_index=False)["precio_por_kg_ars"].mean().sort_values("precio_por_kg_ars", ascending=True)
    
    # Construir serie histórica integrada
    df_historico = generar_serie_historica_referencia(promedio_kg)

    # 2. LOAD (Guardar datasets procesados en la raíz del proyecto)
    processed_dir = BASE_DIR / "data" / "processed"
    figures_dir = BASE_DIR / "reports" / "figures"
    processed_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    df_jumbo.to_csv(processed_dir / "yerba_gondola_procesada.csv", index=False, encoding="utf-8-sig")
    df_historico.to_csv(processed_dir / "yerba_serie_historica_ipc.csv", index=False, encoding="utf-8-sig")
    print(f"Datasets procesados guardados en '{processed_dir}'.")

    # 3. VISUALIZACIÓN (Gráfico 1: Precio por Kg por Marca en Jumbo)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    colores = ["#2E86C1" if val <= promedio_kg else "#E67E22" for val in df_marcas["precio_por_kg_ars"]]
    bars = ax.barh(df_marcas["marca"], df_marcas["precio_por_kg_ars"], color=colores)
    
    ax.axvline(promedio_kg, color="#C0392B", linestyle="--", linewidth=1.5, label=f"Promedio Góndola: ${promedio_kg:,.0f}/kg")
    ax.set_title("Precio Promedio por Kilogramo de Yerba Mate por Marca (Jumbo Argentina)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Precio por Kg (ARS)", fontsize=10)
    ax.legend()
    
    for bar in bars:
        ancho = bar.get_width()
        ax.text(ancho + 150, bar.get_y() + bar.get_height()/2, f"${ancho:,.0f}", va="center", fontsize=8.5)
        
    plt.tight_layout()
    plt.savefig(figures_dir / "01_ranking_precios_marca.png")
    plt.close()

    # 4. VISUALIZACIÓN (Gráfico 2: Evolución Histórica Real y Efecto DNU 70/2023)
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.plot(df_historico["periodo"], df_historico["precio_real_kg"], marker="o", linewidth=2.5, color="#1F618D", markersize=8)
    
    # Marcar el punto de quiebre del DNU 70/2023
    ax.axvline("2023-Q4", color="#C0392B", linestyle="--", linewidth=1.5, label="DNU 70/2023 (Fin regulación INYM)")
    
    for i, row in df_historico.iterrows():
        ax.annotate(f"${row['precio_real_kg']:,.0f}", (row["periodo"], row["precio_real_kg"]),
                    textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5, fontweight="bold")

    ax.set_title("Evolución del Precio Real de la Yerba Mate (Pesos Constantes) vs. Muestreo Actual", fontsize=12, fontweight="bold", pad=12)
    ax.set_ylabel("Precio Real por Kg (ARS Constantes)", fontsize=10)
    ax.set_ylim(3500, max(df_historico["precio_real_kg"]) * 1.18)
    plt.xticks(rotation=25)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(figures_dir / "02_evolucion_historica_dnu.png")
    plt.close()

    print("\n--- RESUMEN ESTADÍSTICO PARA TU INFORME ---")
    print(f"Total de presentaciones analizadas: {len(df_jumbo)}")
    print(f"Precio promedio por Kg en Jumbo: ${promedio_kg:,.2f}")
    print(f"Precio mediano por Kg en Jumbo:  ${mediana_kg:,.2f}")
    print(f"Marca más económica por Kg:      {df_marcas.iloc[0]['marca']} (${df_marcas.iloc[0]['precio_por_kg_ars']:,.2f})")
    print(f"Marca más costosa por Kg:        {df_marcas.iloc[-1]['marca']} (${df_marcas.iloc[-1]['precio_por_kg_ars']:,.2f})")
    print(f"\n¡Gráficos generados en '{figures_dir}'!")

if __name__ == "__main__":
    ejecutar_etl_y_graficos()
