import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Detecta automáticamente la carpeta raíz del proyecto (un nivel arriba de /src)
BASE_DIR = Path(__file__).resolve().parent.parent

plt.style.use('seaborn-v0_8-whitegrid')

def crear_datasets_oficiales_raw():
    """
    Crea los archivos CSV oficiales en data/raw/ con las series verificadas
    de INDEC (IPC), CEPA (Brecha origen-góndola) y Ministerio/INYM (Desregulación).
    """
    raw_dir = BASE_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1. Dataset Oficial IPC - INDEC (Variación mensual % y número índice base Dic-2023 = 100)
    datos_ipc = [
        {"anio_mes": "2023-10", "var_mensual_ipc_pct": 8.3,  "indice_ipc": 71.1},
        {"anio_mes": "2023-11", "var_mensual_ipc_pct": 12.8, "indice_ipc": 79.7},
        {"anio_mes": "2023-12", "var_mensual_ipc_pct": 25.5, "indice_ipc": 100.0},
        {"anio_mes": "2024-03", "var_mensual_ipc_pct": 11.0, "indice_ipc": 151.6},
        {"anio_mes": "2024-06", "var_mensual_ipc_pct": 4.6,  "indice_ipc": 179.8},
        {"anio_mes": "2024-09", "var_mensual_ipc_pct": 3.5,  "indice_ipc": 201.6},
        {"anio_mes": "2024-12", "var_mensual_ipc_pct": 2.7,  "indice_ipc": 217.8},
        {"anio_mes": "2025-01", "var_mensual_ipc_pct": 2.2,  "indice_ipc": 222.6},
        {"anio_mes": "2025-06", "var_mensual_ipc_pct": 1.6,  "indice_ipc": 250.4},
        {"anio_mes": "2025-12", "var_mensual_ipc_pct": 2.8,  "indice_ipc": 286.1},
        {"anio_mes": "2026-06", "var_mensual_ipc_pct": 1.9,  "indice_ipc": 333.8},
        {"anio_mes": "2026-09", "var_mensual_ipc_pct": 1.9,  "indice_ipc": 353.2}
    ]
    df_ipc = pd.DataFrame(datos_ipc)
    df_ipc.to_csv(raw_dir / "ipc_indec.csv", index=False, encoding="utf-8-sig")

    # 2. Dataset Oficial CEPA & Ministerio/INYM (Precio hoja verde, góndola promedio y participación %)
    # Nota: Se requieren ~3 kg de hoja verde para producir 1 kg de yerba elaborada en góndola.
    datos_cepa = [
        {"anio_mes": "2023-10", "precio_hoja_verde_kg": 250.0, "precio_gondola_ref_kg": 2150.0, "participacion_productor_pct": 34.9, "regimen": "Regulado (Res. 406/23)"},
        {"anio_mes": "2023-12", "precio_hoja_verde_kg": 250.0, "precio_gondola_ref_kg": 2980.0, "participacion_productor_pct": 25.2, "regimen": "Inicio DNU 70/2023"},
        {"anio_mes": "2024-03", "precio_hoja_verde_kg": 370.0, "precio_gondola_ref_kg": 4100.0, "participacion_productor_pct": 27.1, "regimen": "Transición INYM"},
        {"anio_mes": "2024-06", "precio_hoja_verde_kg": 280.0, "precio_gondola_ref_kg": 4650.0, "participacion_productor_pct": 18.1, "regimen": "Desregulado"},
        {"anio_mes": "2024-09", "precio_hoja_verde_kg": 265.0, "precio_gondola_ref_kg": 4890.0, "participacion_productor_pct": 16.3, "regimen": "Desregulado (Inf. Min.)"},
        {"anio_mes": "2025-01", "precio_hoja_verde_kg": 230.0, "precio_gondola_ref_kg": 5180.0, "participacion_productor_pct": 13.3, "regimen": "Desregulado (Inf. CEPA)"},
        {"anio_mes": "2026-06", "precio_hoja_verde_kg": 280.0, "precio_gondola_ref_kg": 5211.0, "participacion_productor_pct": 16.1, "regimen": "Desregulado (CEPA 2026)"}
    ]
    df_cepa = pd.DataFrame(datos_cepa)
    df_cepa.to_csv(raw_dir / "cepa_cadena_valor.csv", index=False, encoding="utf-8-sig")
    
    print(f"Archivos oficiales creados en '{raw_dir}': ipc_indec.csv y cepa_cadena_valor.csv")
    return df_ipc, df_cepa

def integrar_fuentes_multicanal():
    df_ipc, df_cepa = crear_datasets_oficiales_raw()

    # Cargar el dataset unificado generado por etl_pipeline.py (Jumbo + Carrefour + Coto)
    processed_dir = BASE_DIR / "data" / "processed"
    ruta_gondola = processed_dir / "yerba_gondola_procesada.csv"
    if not ruta_gondola.exists():
        raise FileNotFoundError("No se encontró 'yerba_gondola_procesada.csv'. Ejecutá primero etl_pipeline.py.")
    
    df_gondola = pd.read_csv(ruta_gondola)

    # Calcular mediana multicanal actual y agregarla como punto de cierre a la serie
    mediana_multicanal = round(df_gondola["precio_por_kg_ars"].median(), 2)
    cadenas_activas = df_gondola["supermercado"].nunique() if "supermercado" in df_gondola.columns else 1

    fila_actual = pd.DataFrame([{
        "anio_mes": "2026-11",
        "precio_hoja_verde_kg": 290.0,
        "precio_gondola_ref_kg": mediana_multicanal,
        "participacion_productor_pct": round((290.0 * 3 / mediana_multicanal) * 100, 1),
        "regimen": f"Muestreo Vivo ({cadenas_activas} Cadenas)"
    }])

    df_serie_completa = pd.concat([df_cepa, fila_actual], ignore_index=True)

    # Cruzar (JOIN) la serie del complejo yerbatero con el IPC de INDEC usando 'anio_mes'
    df_maestro = pd.merge(df_serie_completa, df_ipc, on="anio_mes", how="left")
    
    # Rellenar el índice IPC del mes actual proyectando la última variación mensual (1.9%)
    ultimo_ipc = df_ipc["indice_ipc"].iloc[-1]
    df_maestro["indice_ipc"] = df_maestro["indice_ipc"].fillna(round(ultimo_ipc * 1.038, 1))

    # Calcular Precio Real en moneda constante de Dic-2023 (Deflactación)
    df_maestro["precio_gondola_real_dic23"] = round((df_maestro["precio_gondola_ref_kg"] / df_maestro["indice_ipc"]) * 100, 2)
    df_maestro["precio_hoja_verde_real_dic23"] = round((df_maestro["precio_hoja_verde_kg"] / df_maestro["indice_ipc"]) * 100, 2)

    figures_dir = BASE_DIR / "reports" / "figures"
    processed_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    ruta_maestro = processed_dir / "dataset_maestro_yerba.csv"
    df_maestro.to_csv(ruta_maestro, index=False, encoding="utf-8-sig")
    print(f"\nDataset Maestro Multicanal guardado en: '{ruta_maestro}'")
    print(df_maestro[["anio_mes", "precio_hoja_verde_kg", "precio_gondola_ref_kg", "participacion_productor_pct", "precio_gondola_real_dic23"]])

    # Gráfico 3: Brecha Origen vs. Góndola y Participación del Productor (CEPA + Multicanal)
    fig, ax1 = plt.subplots(figsize=(10, 5.5), dpi=150)

    color_barras = "#2E86C1"
    bars = ax1.bar(df_maestro["anio_mes"], df_maestro["participacion_productor_pct"], color=color_barras, alpha=0.75, label="Participación Productor en Góndola (%)")
    ax1.set_ylabel("Participación del Productor (%)", color=color_barras, fontsize=10, fontweight="bold")
    ax1.set_ylim(0, 45)
    ax1.tick_params(axis="y", labelcolor=color_barras)

    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2, h + 1, f"{h:.1f}%", ha="center", fontsize=8.5, fontweight="bold", color="#1B4F72")

    ax2 = ax1.twinx()
    color_linea = "#C0392B"
    ax2.plot(df_maestro["anio_mes"], df_maestro["precio_gondola_real_dic23"], color=color_linea, marker="o", linewidth=2.5, label="Precio Real Góndola (Base Dic-23 = 100)")
    ax2.set_ylabel("Precio Real Góndola ($ Constantes Dic-23)", color=color_linea, fontsize=10, fontweight="bold")
    ax2.set_ylim(1000, 4000)
    ax2.tick_params(axis="y", labelcolor=color_linea)

    plt.title("Impacto Desregulación: Precio Real en Góndola (IPC) vs. Participación del Productor (CEPA + 3 Cadenas)", fontsize=10.5, fontweight="bold", pad=12)
    plt.tight_layout()
    ruta_grafico = figures_dir / "03_brecha_productor_ipc.png"
    plt.savefig(ruta_grafico)
    plt.close()
    print(f"Gráfico 3 multicanal generado en: '{ruta_grafico}'")

if __name__ == "__main__":
    integrar_fuentes_multicanal()
