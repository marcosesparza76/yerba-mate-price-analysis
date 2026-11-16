import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent

BASE_URL_CARREFOUR = "https://www.carrefour.com.ar/yerba?_q=yerba&map=ft"

MARCAS_CONOCIDAS = [
    "PLAYADITO", "TARAGÜI", "TARAGUI", "LA MERCED", "MAÑANITA", "CBSE", "CBSÉ",
    "NOBLEZA GAUCHA", "CRUZ DE MALTA", "AMANDA", "CANARIAS", "ROSAMONTE",
    "UNIÓN", "UNION", "PIPORÉ", "PIPORE", "CHAMIGO", "LIEBIG", "ANDRESITO",
    "LA TRANQUERA", "VERDEFLOR", "CACHAMATE", "ROMANCE", "KURUPÍ", "KURUPI",
    "BALDO", "SARA", "DEL CEBADOR", "CARREFOUR", "COSMICO", "BUENAS Y SANTAS",
    "DON BASILIO", "SOL DE ACUARIO", "KRAUS", "ROAPIPÓ", "ROAPIPO", "TITRAYJU"
]

# Excluir únicamente accesorios reales (sin la palabra "mate " que bloqueaba "Yerba mate")
PALABRAS_EXCLUIR = {
    "bombilla", "termo ", "matera", "set matero", "kit matero",
    "yerbera", "azucarera", "bolso", "mochila", "taza", "vaso", "galletitas", "alfajor"
}

def extraer_gramaje_kg(texto):
    texto_low = str(texto).replace('\xa0', ' ').lower()
    match_g = re.search(r'(\d+)\s*(?:g|gr|grs|gramos)\b', texto_low)
    if match_g:
        return float(match_g.group(1)) / 1000.0
    match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo|kilos|k)\b', texto_low)
    if match_kg:
        return float(match_kg.group(1).replace(',', '.'))
    return None

def extraer_precio_bloque(texto_tarjeta):
    texto_limpio = texto_tarjeta.replace('\xa0', ' ')
    matches = re.findall(r'\$\s*([\d\.]+(?:,\d{1,2})?)', texto_limpio)
    for m in matches:
        val_str = m.replace('.', '').replace(',', '.')
        try:
            val = float(val_str)
            if val > 500:
                return val
        except ValueError:
            continue
    return 0.0

def detectar_marca(nombre):
    nombre_up = nombre.upper()
    for m in MARCAS_CONOCIDAS:
        if m in nombre_up:
            return m.replace("TARAGUI", "TARAGÜI").replace("CBSÉ", "CBSE").replace("PIPORE", "PIPORÉ").replace("UNION", "UNIÓN")
    # Limpiar "YERBA MATE" para tomar la primera palabra real si no está en la lista
    limpio = re.sub(r'^YERBA\s+(?:MATE\s+|NEGRA\s+|ORGÁNICA\s+|ORGANICA\s+|COMPUESTA\s+)?', '', nombre_up).strip()
    palabras = limpio.split()
    return palabras[0] if palabras else "SIN ESPECIFICAR"

def recolectar_precios_carrefour():
    print("Abriendo catálogo de Yerbas en Carrefour Argentina...")
    lista_yerbas = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}
        )
        page = context.new_page()
        selector_producto = "section[class*='vtex-product-summary-2-x-container']"

        for num_pagina in range(1, 8):
            url_pag = f"{BASE_URL_CARREFOUR}&page={num_pagina}"
            print(f"Extrayendo página {num_pagina} de Carrefour...")
            page.goto(url_pag, wait_until="domcontentloaded", timeout=60000)

            try:
                page.wait_for_selector(selector_producto, state="visible", timeout=15000)
                page.wait_for_timeout(2000)
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)
            except Exception:
                print(f"Fin del catálogo alcanzado en página {num_pagina}.")
                break

            tarjetas = page.query_selector_all(selector_producto)
            if not tarjetas:
                break

            nuevos_en_pagina = 0
            for card in tarjetas:
                try:
                    texto_tarjeta = card.inner_text().replace('\xa0', ' ')
                    texto_low = texto_tarjeta.lower()

                    if "yerba" not in texto_low:
                        continue
                    if any(excl in texto_low for excl in PALABRAS_EXCLUIR):
                        continue

                    precio_actual = extraer_precio_bloque(texto_tarjeta)

                    lineas = [l.strip() for l in texto_tarjeta.split("\n") if l.strip()]
                    textos_validos = [
                        l for l in lineas
                        if "$" not in l
                        and "sin impuestos" not in l.lower()
                        and "agregar" not in l.lower()
                        and len(l) > 8
                    ]

                    if not textos_validos:
                        continue

                    nombre = max(textos_validos, key=len)
                    peso_kg = extraer_gramaje_kg(nombre) or extraer_gramaje_kg(texto_tarjeta)

                    if precio_actual > 0 and peso_kg and 0.1 <= peso_kg <= 5.0:
                        precio_por_kg = round(precio_actual / peso_kg, 2)
                        
                        # Filtrar precios por kilo coherentes de yerba mate (descarta termos/kits)
                        if not (1500 <= precio_por_kg <= 25000):
                            continue

                        marca = detectar_marca(nombre)

                        lista_yerbas.append({
                            "fecha_extraccion": fecha_hoy,
                            "supermercado": "Carrefour",
                            "marca": marca,
                            "producto": nombre,
                            "peso_kg": peso_kg,
                            "precio_gondola_ars": precio_actual,
                            "precio_por_kg_ars": precio_por_kg
                        })
                        nuevos_en_pagina += 1
                except Exception:
                    continue

            print(f"  -> {nuevos_en_pagina} yerbas válidas capturadas en página {num_pagina}.")

        browser.close()

    if not lista_yerbas:
        print("No se extrajeron yerbas de Carrefour.")
        return

    df = pd.DataFrame(lista_yerbas).drop_duplicates(subset=["producto"])
    raw_dir = BASE_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    nombre_archivo = raw_dir / f"carrefour_yerbas_{fecha_hoy}.csv"
    df.to_csv(nombre_archivo, index=False, encoding="utf-8-sig")

    print(f"\n¡Extracción Carrefour completada! Se guardaron {len(df)} yerbas únicas en: {nombre_archivo}\n")
    print(df[["marca", "producto", "peso_kg", "precio_gondola_ars", "precio_por_kg_ars"]].head(25))

if __name__ == "__main__":
    recolectar_precios_carrefour()
