import pandas as pd
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent

BASE_URL_COTO = "".join(["https", "://", "www.", "coto.com.ar", "/productos/yerba"])

MARCAS_CONOCIDAS = [
    "PLAYADITO", "TARAGÜI", "TARAGUI", "LA MERCED", "MAÑANITA", "CBSE", "CBSÉ",
    "NOBLEZA GAUCHA", "CRUZ DE MALTA", "AMANDA", "CANARIAS", "ROSAMONTE",
    "UNIÓN", "UNION", "PIPORÉ", "PIPORE", "CHAMIGO", "LIEBIG", "ANDRESITO",
    "LA TRANQUERA", "VERDEFLOR", "CACHAMATE", "ROMANCE", "KURUPÍ", "KURUPI",
    "BALDO", "SARA", "DEL CEBADOR", "COTO", "CIUDAD DEL LAGO", "COSMICO",
    "BUENAS Y SANTAS", "DON BASILIO", "SOL DE ACUARIO", "KRAUS", "ROAPIPÓ", "ROAPIPO",
    "AGUANTADORA", "PRIMICIA", "SINCERIDAD", "CUMBRECITA"
]

PALABRAS_EXCLUIR = {
    "lata ", "lata yerba", "saquitos", "mate cocido", "bombilla", "termo ",
    "matera", "set matero", "kit matero", "yerbera", "azucarera", "bolso",
    "mochila", "taza", "vaso", "galletitas", "alfajor"
}

def extraer_gramaje_kg(texto):
    texto_low = str(texto).replace('\xa0', ' ').lower()
    if "saquito" in texto_low or "x 3" in texto_low or "x3" in texto_low:
        return None
    match_g = re.search(r'(\d+)\s*(?:g|gr|grs|grm|gramos)\b', texto_low)
    if match_g:
        return float(match_g.group(1)) / 1000.0
    match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo|kilos|k)\b', texto_low)
    if match_kg:
        return float(match_kg.group(1).replace(',', '.'))
    return None

def extraer_precio_coto(texto_tarjeta):
    texto_limpio = texto_tarjeta.replace('\xa0', ' ')
    lineas = [l.strip() for l in texto_limpio.split('\n') if l.strip()]
    
    for l in lineas:
        l_low = l.lower()
        if "x kg" in l_low or "por kg" in l_low or "2da" in l_low or "llevando" in l_low or "sin impuestos" in l_low:
            continue
        match = re.search(r'\$\s*([\d\.]+(?:,\d{1,2})?)', l)
        if match:
            val_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                val = float(val_str)
                if val > 800:
                    return val
            except ValueError:
                continue

    matches = re.findall(r'\$\s*([\d\.]+(?:,\d{1,2})?)', texto_limpio)
    for m in matches:
        val_str = m.replace('.', '').replace(',', '.')
        try:
            val = float(val_str)
            if val > 800:
                return val
        except ValueError:
            continue
    return 0.0

def detectar_marca(nombre):
    nombre_up = nombre.upper()
    for m in MARCAS_CONOCIDAS:
        if m in nombre_up:
            return m.replace("TARAGUI", "TARAGÜI").replace("CBSÉ", "CBSE").replace("PIPORE", "PIPORÉ").replace("UNION", "UNIÓN")
    limpio = re.sub(r'^YERBA\s+(?:MATE\s+|NEGRA\s+|ORGÁNICA\s+|ORGANICA\s+|COMPUESTA\s+)?', '', nombre_up).strip()
    palabras = limpio.split()
    return palabras[0] if palabras else "SIN ESPECIFICAR"

def recolectar_precios_coto():
    print(f"Abriendo catálogo de Yerbas en Coto ({BASE_URL_COTO})...")
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

        for num_pagina in range(1, 9):
            url_pag = f"{BASE_URL_COTO}?page={num_pagina}"
            print(f"Extrayendo página {num_pagina} de Coto...")

            try:
                page.goto(url_pag, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_function("() => document.body.innerText.includes('$')", timeout=15000)
                page.wait_for_timeout(2000)
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(1000)
            except Exception:
                print(f"Fin del catálogo alcanzado en página {num_pagina}.")
                break

            tarjetas = page.query_selector_all("article, div[class*='product-card'], div[class*='producto'], section[class*='product-summary']")
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

                    precio_actual = extraer_precio_coto(texto_tarjeta)

                    lineas = [l.strip() for l in texto_tarjeta.split("\n") if l.strip()]
                    textos_validos = [
                        l for l in lineas
                        if "$" not in l
                        and "agregar" not in l.lower()
                        and "precio" not in l.lower()
                        and "sin impuestos" not in l.lower()
                        and "código" not in l.lower()
                        and "plu" not in l.lower()
                        and "cuota" not in l.lower()
                        and "ver planes" not in l.lower()
                        and len(l) > 8
                    ]

                    if not textos_validos:
                        continue

                    lineas_yerba = [l for l in textos_validos if "yerba" in l.lower()]
                    nombre = max(lineas_yerba, key=len) if lineas_yerba else max(textos_validos, key=len)

                    if "yerba" not in nombre.lower():
                        continue

                    peso_kg = extraer_gramaje_kg(nombre) or extraer_gramaje_kg(texto_tarjeta)

                    if precio_actual > 0 and peso_kg and 0.25 <= peso_kg <= 3.0:
                        precio_por_kg = round(precio_actual / peso_kg, 2)
                        if not (2000 <= precio_por_kg <= 22000):
                            continue

                        marca = detectar_marca(nombre)

                        lista_yerbas.append({
                            "fecha_extraccion": fecha_hoy,
                            "supermercado": "Coto",
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
        print("No se extrajeron yerbas de Coto.")
        return

    df = pd.DataFrame(lista_yerbas).drop_duplicates(subset=["producto"])
    raw_dir = BASE_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    nombre_archivo = raw_dir / f"coto_yerbas_{fecha_hoy}.csv"
    df.to_csv(nombre_archivo, index=False, encoding="utf-8-sig")

    print(f"\n¡Extracción Coto completada! Se guardaron {len(df)} yerbas únicas en: {nombre_archivo}\n")
    print(df[["marca", "producto", "peso_kg", "precio_gondola_ars", "precio_por_kg_ars"]].head(20))

if __name__ == "__main__":
    recolectar_precios_coto()
