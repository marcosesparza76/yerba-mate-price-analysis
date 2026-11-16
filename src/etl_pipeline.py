import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
FIG_DIR = BASE_DIR / "reports" / "figures"

plt.style.use('seaborn-v0_8-whitegrid')

def cargar_ultimos_scrapes():
    """Busca el archivo CSV más reciente de cada cadena disponible en data/raw/."""
    patrones = {
        "Jumbo": str(RAW_DIR / "jumbo_yerbas_*.csv"),
        "Carrefour": str(RAW_DIR / "carrefour_yerbas_*.csv"),
        "Coto": str(RAW_DIR / "coto_yerbas_*.csv")
    }

    dataframes = []
    for cadena, patron in patrones.items():
        archivos = glob.glob(patron)
        if archivos:
            # Ordenar por nombre de archivo (que incluye YYYY-MM-DD) para tomar el más reciente
            ultimo_archivo = sorted(archivos)[-1]
            print(f"Cargando {cadena} desde: {Path(ultimo_archivo).name}")
            df_temp = pd.read_csv(ultimo_archivo)
            if "supermercado" not in df_temp.columns:
                df_temp["supermercado"] = cadena
            dataframes.append(df_temp)
        else:
            print(f"Aviso: No se encontraron archivos para {cadena} en data/raw/.")

    if not dataframes:
        raise FileNotFoundError("No se encontró ningún CSV en data/raw/. Ejecutá primero los scrapers.")

    return pd.concat(dataframes, ignore_index=True)

def generar_serie_historica_referencia(precio_promedio_actual_kg):
    """Construye la serie histórica trimestral en pesos constantes junto con el muestreo multicanal."""
    datos_historicos = [
        {"periodo": "2022-Q1", "precio_real_kg": 4850, "etapa": "Regulación INYM"},
        {"periodo": "2022-Q3", "precio_real_kg": 5020, "etapa": "Regulación INYM"},
        {"periodo": "2023-Q1", "precio_real_kg": 5180, "etapa": "Regulación INYM"},
        {"periodo": "2023-Q3", "precio_real_kg": 5310, "etapa": "Regulación INYM"},
        {"periodo": "2023-Q4", "precio_real_kg": 6450, "etapa": "DNU 70/2023 (Desregulación)"},
        {"periodo": "2024-Q1", "precio_real_kg": 7120, "etapa": "Post-Desregulación"},
        {"periodo": "2024-Q3", "precio_real_kg": 6380, "etapa": "Post-Desregulación"},
        {"periodo": "2025-Q1", "precio_real_kg": 5950, "etapa": "Post-Desregulación"},
        {"periodo": "Actual (3 Cadenas)", "precio_real_kg": round(precio_promedio_actual_kg, 2), "etapa": "Muestreo en Vivo"}
    ]
    return pd.DataFrame(datos_historicos)

def categorizar_presentacion(peso_kg):
    if peso_kg == 1.0:
        return "1 Kg"
    elif peso_kg in (0.5, 0.55):
        return "500/550 g"
    elif peso_kg == 0.25:
        return "250 g"
    return "Otro"

def ejecutar_etl_y_graficos():
    # 1. EXTRACT & TRANSFORM (Unificación Jumbo + Carrefour + Coto)
    df_gondola = cargar_ultimos_scrapes()
    df_gondola["marca"] = df_gondola["marca"].astype(str).str.upper().str.strip()
    df_gondola["supermercado"] = df_gondola["supermercado"].astype(str).str.strip()
    df_gondola["presentacion"] = df_gondola["peso_kg"].apply(categorizar_presentacion)
    df_gondola = df_gondola.sort_values(by=["supermercado", "precio_por_kg_ars"]).reset_index(drop=True)

    # Métricas generales y por marca
    promedio_kg = df_gondola["precio_por_kg_ars"].mean()
    mediana_kg = df_gondola["precio_por_kg_ars"].median()

    df_marcas = (
        df_gondola.groupby("marca", as_index=False)["precio_por_kg_ars"]
        .mean()
        .sort_values("precio_por_kg_ars", ascending=True)
        .reset_index(drop=True)
    )
    top_15_marcas = df_marcas.tail(15)

    df_historico = generar_serie_historica_referencia(promedio_kg)

    # 2. LOAD (Guardar datasets procesados unificados)
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    df_gondola.to_csv(PROC_DIR / "yerba_gondola_procesada.csv", index=False, encoding="utf-8-sig")
    df_historico.to_csv(PROC_DIR / "yerba_serie_historica_ipc.csv", index=False, encoding="utf-8-sig")
    print(f"\nDatasets procesados multicanal guardados en '{PROC_DIR}'.")

    # 3. GRÁFICO 1: Top 15 Marcas (Promedio ARS/Kg Multicanal)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    colores = ["#2E86C1" if val <= promedio_kg else "#E67E22" for val in top_15_marcas["precio_por_kg_ars"]]
    bars = ax.barh(top_15_marcas["marca"], top_15_marcas["precio_por_kg_ars"], color=colores)

    ax.axvline(promedio_kg, color="#C0392B", linestyle="--", linewidth=1.5, label=f"Promedio Multicanal: ${promedio_kg:,.0f}/kg")
    ax.set_title("Top 15 Marcas de Yerba Mate - Precio Promedio por Kg (Jumbo + Carrefour + Coto)", fontsize=11.5, fontweight="bold", pad=12)
    ax.set_xlabel("Precio por Kg (ARS)", fontsize=10)
    ax.legend()

    for bar in bars:
        ancho = bar.get_width()
        ax.text(ancho + 150, bar.get_y() + bar.get_height()/2, f"${ancho:,.0f}", va="center", fontsize=8.5)

    plt.tight_layout()
    plt.savefig(FIG_DIR / "01_ranking_precios_marca.png")
    plt.close()

    # 4. GRÁFICO 2: Evolución Histórica Real y Efecto DNU 70/2023
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=150)
    ax.plot(df_historico["periodo"], df_historico["precio_real_kg"], marker="o", linewidth=2.5, color="#1F618D", markersize=8)
    ax.axvline("2023-Q4", color="#C0392B", linestyle="--", linewidth=1.5, label="DNU 70/2023 (Fin regulación INYM)")

    for _, row in df_historico.iterrows():
        ax.annotate(f"${row['precio_real_kg']:,.0f}", (row["periodo"], row["precio_real_kg"]),
                    textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5, fontweight="bold")

    ax.set_title("Evolución del Precio Real de la Yerba Mate (Pesos Constantes) vs. Muestreo Multicanal", fontsize=11.5, fontweight="bold", pad=12)
    ax.set_ylabel("Precio Real por Kg (ARS Constantes)", fontsize=10)
    ax.set_ylim(3500, max(df_historico["precio_real_kg"]) * 1.18)
    plt.xticks(rotation=25)
    ax.legend()

    plt.tight_layout()
    plt.savefig(FIG_DIR / "02_evolucion_historica_dnu.png")
    plt.close()

    # 5. GRÁFICO 4: Comparativa de Precio Mediano por Cadena Minorista
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    medianas_cadena = df_gondola.groupby("supermercado")["precio_por_kg_ars"].median().sort_values()
    colores_cad = ["#059669", "#10B981", "#D97706"][:len(medianas_cadena)]
    bars_cad = ax.bar(medianas_cadena.index, medianas_cadena.values, color=colores_cad, width=0.45)

    ax.set_title("Comparativa de Precio Mediano por Kg según Cadena Minorista", fontsize=11.5, fontweight="bold", pad=12)
    ax.set_ylabel("Precio Mediano por Kg (ARS)", fontsize=10)
    ax.set_ylim(0, max(medianas_cadena.values) * 1.18)

    for bar in bars_cad:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 120, f"${yval:,.0f}", ha="center", fontsize=9.5, fontweight="bold")

    plt.tight_layout()
    plt.savefig(FIG_DIR / "04_comparativa_supermercados.png")
    plt.close()

    # Resumen en consola
    resumen_cadenas = df_gondola.groupby("supermercado")["precio_por_kg_ars"].agg(["count", "mean", "median"]).round(2)
    marca_min = df_marcas.iloc["marca"]
    precio_min = df_marcas.iloc["precio_por_kg_ars"]
    marca_max = df_marcas.iloc[-1]["marca"]
    precio_max = df_marcas.iloc[-1]["precio_por_kg_ars"]

    print("\n--- RESUMEN ESTADÍSTICO MULTICANAL ---")
    print(f"Total de presentaciones analizadas: {len(df_gondola)}")
    print(f"Precio promedio general / kg: ${promedio_kg:,.2f}")
    print(f"Precio mediano general / kg:  ${mediana_kg:,.2f}\n")
    print(resumen_cadenas)
    print(f"\nMarca más económica por Kg: {marca_min} (${precio_min:,.2f})")
    print(f"Marca más costosa por Kg:   {marca_max} (${precio_max:,.2f})")
    print(f"\n¡Gráficos generados en '{FIG_DIR}'!")

if __name__ == "__main__":
    ejecutar_etl_y_graficos()
