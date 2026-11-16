import os
import smtplib
import requests
import pandas as pd
from email.message import EmailMessage
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def generar_resumen_texto():
    df_gondola = pd.read_csv(BASE_DIR / "data" / "processed" / "yerba_gondola_procesada.csv")
    df_maestro = pd.read_csv(BASE_DIR / "data" / "processed" / "dataset_maestro_yerba.csv")
    
    fecha = df_gondola["fecha_extraccion"].iloc[0]
    prom = df_gondola["precio_por_kg_ars"].mean()
    med = df_gondola["precio_por_kg_ars"].median()
    min_row = df_gondola.loc[df_gondola["precio_por_kg_ars"].idxmin()]
    max_row = df_gondola.loc[df_gondola["precio_por_kg_ars"].idxmax()]
    part_prod = df_maestro["participacion_productor_pct"].iloc[-1]
    precio_real = df_maestro["precio_gondola_real_dic23"].iloc[-1]

    mensaje = (
        f"🧉 REPORTE AUTOMÁTICO YERBA MATE ({fecha})\n\n"
        f"• Presentaciones relevadas: {len(df_gondola)}\n"
        f"• Precio promedio / kg: ${prom:,.2f}\n"
        f"• Precio mediano / kg: ${med:,.2f}\n"
        f"• Más económica: {min_row['marca']} (${min_row['precio_por_kg_ars']:,.2f}/kg)\n"
        f"• Más costosa: {max_row['marca']} (${max_row['precio_por_kg_ars']:,.2f}/kg)\n"
        f"• Participación productor en góndola: {part_prod:.1f}%\n"
        f"• Precio real deflactado (Base Dic-23): ${precio_real:,.2f}/kg\n\n"
        f"🔗 Ver tablero interactivo: https://yerba-mate-price-analysis-monitor.streamlit.app/"
    )
    return mensaje

def enviar_telegram(texto):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram no configurado (faltan variables TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return

    # Enviar texto resumen
    url_msg = f"https://telegram.org{token}/sendMessage"
    resp_msg = requests.post(url_msg, data={"chat_id": chat_id, "text": texto})
    print(f"Mensaje Telegram estado: {resp_msg.status_code}")

    # Enviar los 3 gráficos adjuntos
    figuras_dir = BASE_DIR / "reports" / "figures"
    url_photo = f"https://telegram.org{token}/sendPhoto"
    for img_path in sorted(figuras_dir.glob("*.png")):
        with open(img_path, "rb") as img:
            resp_img = requests.post(url_photo, data={"chat_id": chat_id}, files={"photo": img})
            print(f"Gráfico {img_path.name} enviado: {resp_img.status_code}")

def enviar_correo(texto):
    remitente = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    destinatario = os.getenv("EMAIL_TO", remitente)
    if not remitente or not password:
        print("Correo no configurado (faltan variables EMAIL_USER / EMAIL_PASS).")
        return

    msg = EmailMessage()
    msg["Subject"] = "🧉 Actualización Precios Yerba Mate - Reporte ETL"
    msg["From"] = remitente
    msg["To"] = destinatario
    msg.set_content(texto)

    # Adjuntar los 3 gráficos PNG
    figuras_dir = BASE_DIR / "reports" / "figures"
    for img_file in sorted(figuras_dir.glob("*.png")):
        with open(img_file, "rb") as f:
            msg.add_attachment(f.read(), maintype="image", subtype="png", filename=img_file.name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(remitente, password)
        smtp.send_message(msg)
    print("Correo electrónico enviado exitosamente.")

if __name__ == "__main__":
    resumen = generar_resumen_texto()
    print(resumen)
    enviar_telegram(resumen)
    enviar_correo(resumen)
