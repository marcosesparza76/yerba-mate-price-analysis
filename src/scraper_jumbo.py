import requests
import pandas as pd
import re
from datetime import datetime
import os

# URL del endpoint de catálogo de Jumbo Argentina (Categoría: Almacén / Desayuno y Merienda / Yerbas)
API_URL = "https://jumbo.com.ar"

# Parámetros para traer los primeros 50 productos (del 0 al 49)
params = {
    "_from": 0,
    "_to": 49
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def extraer_gramaje_kg(nombre_producto):
    """Detecta el peso en el nombre del producto y lo devuelve en kilogramos (ej: 500g -> 0.5)."""
    nombre = nombre_producto.lower()
    
    # Buscar patrones en gramos (ej: 500g, 500 gr, 250g)
    match_g = re.search(r'(\d+)\s*(?:g|gr|gramos)\b', nombre)
    if match_g:
        return float(match_g.group(1)) / 1000.0
    
    # Buscar patrones en kilos (ej: 1kg, 1 kg, 2kg)
    match_kg = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg|kilo|kilos)\b', nombre)
    if match_kg:
        return float(match_kg.group(1).replace(',', '.'))
    
    return None  # Si no especifica peso en el título

def recolectar_precios_jumbo():
    print("Conectando con el catálogo de Jumbo Argentina...")
    response = requests.get(API_URL, params=params, headers=headers)
    
    if response.status_code not in:
        print(f"Error al consultar la API: Código {response.status_code}")
        return
    
    productos_json = response.json()
    lista_yerbas = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    for prod in productos_json:
        try:
            nombre = prod.get("productName", "Sin nombre")
            marca = prod.get("brand", "Sin marca")
            
            # Navegar la estructura JSON de VTEX para llegar al precio de lista y oferta
            items = prod.get("items", [])
            if not items:
                continue
                
            sellers = items[0].get("sellers", [])
            if not sellers:
                continue
                
            oferta = sellers[0].get("commertialOffer", {})
            precio_actual = oferta.get("Price", 0)
            precio_lista = oferta.get("ListPrice", 0)
            disponible = oferta.get("IsAvailable", False)
            
            # Solo guardamos productos con stock y precio válido
            if disponible and precio_actual > 0:
                peso_kg = extraer_gramaje_kg(nombre)
                precio_por_kg = round(precio_actual / peso_kg, 2) if peso_kg else None
                
                lista_yerbas.append({
                    "fecha_extraccion": fecha_hoy,
                    "supermercado": "Jumbo",
                    "marca": marca,
                    "producto": nombre,
                    "peso_kg": peso_kg,
                    "precio_gondola_ars": precio_actual,
                    "precio_lista_ars": precio_lista,
                    "precio_por_kg_ars": precio_por_kg
                })
        except Exception as e:
            continue

    # Convertir a DataFrame de Pandas y guardar en CSV
    df = pd.DataFrame(lista_yerbas)
    
    os.makedirs("data/raw", exist_ok=True)
    nombre_archivo = f"data/raw/jumbo_yerbas_{fecha_hoy}.csv"
    df.to_csv(nombre_archivo, index=False, encoding="utf-8-sig")
    
    print(f"¡Éxito! Se recolectaron {len(df)} yerbas con stock.")
    print(f"Archivo guardado en: {nombre_archivo}\n")
    print(df[["marca", "producto", "precio_gondola_ars", "precio_por_kg_ars"]].head(10))

if __name__ == "__main__":
    recolectar_precios_jumbo()

