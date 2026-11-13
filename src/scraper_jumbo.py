import pandas as pd
import re
from datetime import datetime
import os
from playwright.sync_api import sync_playwright

URL_YERBAS = "https://www.jumbo.com.ar/almacen/desayuno-y-merienda/yerbas?initialMap=c,c,c&initialQuery=almacen/desayuno-y-merienda/yerbas&map=category-1,category-2,category-3&query=/almacen/desayuno-y-merienda/yerbas&searchState"

def extraer_gramaje_kg(nombre_producto):
    """Detecta el peso en el nombre del producto y lo convierte a kilogramos."""
    nombre = str(nombre_producto).lower()
    match_g = re.search(r'(\d+)\s*(?:g|gr|grs|gramos)\b', nombre)
    if match_g:
        return float(match_g.group(1)) / 1000.0
    match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo|kilos)\b', nombre)
    if match_kg:
        return float(match_kg.group(1).replace(',', '.'))
    return None

def limpiar_precio(texto_precio):
    """Convierte '$ 4.590,50' en número flotante 4590.50."""
    limpio = re.sub(r'[^\d,]', '', texto_precio).replace(',', '.')
    try:
        return float(limpio)
    except ValueError:
        return 0.0

def recolectar_precios_jumbo():
    print("Abriendo catálogo real de Yerbas en Jumbo Argentina...")
    lista_yerbas = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL_YERBAS, timeout=60000)
        
        print("Esperando que carguen las yerbas y precios...")
        page.wait_for_selector("article", timeout=25000)
        page.wait_for_timeout(3000)
        
        for _ in range(4):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(1500)

        tarjetas = page.query_selector_all("article")
        print(f"Se detectaron {len(tarjetas)} tarjetas en pantalla.")
        palabras_ignorar = {"ver producto", "compra rápida", "agregar", "sin stock", "oferta"}

        for card in tarjetas:
            try:
                texto_tarjeta = card.inner_text()
                
                # Verificar que la tarjeta corresponda a una yerba mate
                if "yerba" not in texto_tarjeta.lower():
                    continue
                
                lineas = [l.strip() for l in texto_tarjeta.split("\n") if l.strip()]
                
                precio_str = next((l for l in lineas if l.startswith("$")), None)
                if not precio_str:
                    continue
                
                precio_actual = limpiar_precio(precio_str)
                textos_validos = [
                    l for l in lineas 
                    if not l.startswith("$") 
                    and l.lower() not in palabras_ignorar 
                    and "%" not in l 
                    and "x kg" not in l.lower()
                    and "precio sin impuestos" not in l.lower()
                    and len(l) > 2
                ]
                
                if not textos_validos:
                    continue
                
                # El nombre completo es el texto más largo; la marca es el más corto restante
                nombre = max(textos_validos, key=len)
                otros_textos = [t for t in textos_validos if t != nombre]
                marca = otros_textos[0] if otros_textos else "Sin especificar"

                if precio_actual > 0:
                    peso_kg = extraer_gramaje_kg(nombre)
                    precio_por_kg = round(precio_actual / peso_kg, 2) if peso_kg else None

                    lista_yerbas.append({
                        "fecha_extraccion": fecha_hoy,
                        "supermercado": "Jumbo",
                        "marca": marca,
                        "producto": nombre,
                        "peso_kg": peso_kg,
                        "precio_gondola_ars": precio_actual,
                        "precio_por_kg_ars": precio_por_kg
                    })
            except Exception:
                continue

        browser.close()

    if not lista_yerbas:
        print("No se extrajeron yerbas. Verificá si cambió la estructura de la página.")
        return

    df = pd.DataFrame(lista_yerbas).drop_duplicates(subset=["producto"])
    os.makedirs("data/raw", exist_ok=True)
    nombre_archivo = f"data/raw/jumbo_yerbas_{fecha_hoy}.csv"
    df.to_csv(nombre_archivo, index=False, encoding="utf-8-sig")

    print(f"\n¡Extracción limpia! Se guardaron {len(df)} yerbas en: {nombre_archivo}\n")
    print(df[["marca", "producto", "peso_kg", "precio_gondola_ars", "precio_por_kg_ars"]])

if __name__ == "__main__":
    recolectar_precios_jumbo()
