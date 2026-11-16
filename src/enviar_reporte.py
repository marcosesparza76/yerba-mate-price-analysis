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
    
    fecha = df_gondola["fecha_extraccion"].max()
    prom = df_gondola["precio_por_kg_ars"].mean()
    med = df_gondola["precio_por_kg_ars"].median()
    min_row = df_gondola.loc[df_gondola["precio_por_kg_ars"].idxmin()]
    max_row = df_gondola.loc[df_gondola["precio_por_kg_ars"].idxmax()]
    part_prod = df_maestro["participacion_productor_pct"].iloc[-1]
    precio_real = df_maestro["precio_gondola_real_dic23"].iloc[-1]

    desglose_cadenas = ""
    if "supermercado" in df_gondola.columns:
        resumen_cad = df_gondola.groupby("supermercado")["precio_por_kg_ars"].agg(["count", "median"]).sort_values("median")
        for cad, fila in resumen_cad.iterrows():
            desglose_cadenas += f"  • {cad}: ${fila['median']:,.2f}/kg ({int(fila['count'])} SKUs)\n"
        min_cadena = f" [{min_row['supermercado']}]"
        max_cadena = f" [{max_row['supermercado']}]"
    else:
        min_cadena = ""
        max_cadena = ""

    url_tablero = "".join(["https", "://", "yerba-mate-price-analysis-monitor.streamlit.app/"])

    mensaje = (
        f"🧉 REPORTE MULTICANAL YERBA MATE ({fecha})\n\n"
        f"• Total relevado: {len(df_gondola)} presentaciones\n"
        f"• Precio promedio general / kg: ${prom:,.2f}\n"
        f"• Precio mediano general / kg: ${med:,.2f}\n\n"
        f"🏪 Mediana por Supermercado:\n{desglose_cadenas}\n"
        f"• Más económica: {min_row['marca']}{min_cadena} (${min_row['precio_por_kg_ars']:,.2f}/kg)\n"
        f"• Más costosa: {max_row['marca']}{max_cadena} (${max_row['precio_por_kg_ars']:,.2f}/kg)\n"
        f"• Participación productor en góndola: {part_prod:.1f}%\n"
        f"• Precio real deflactado (Base Dic-23): ${precio_real:,.2f}/kg\n\n"
        f"🔗 Ver tablero ejecutivo: {url_tablero}"
    )
    return mensaje

def enviar_telegram(texto):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram no configurado (faltan variables TELEGRAM_TOKEN / TELEGRAM_CHAT_ID).")
        return

    base_tg = "".join(["https", "://", "api.telegram.org/bot", str(token).strip()])

    try:
        url_msg = base_tg + "/sendMessage"
        resp_msg = requests.post(url_msg, data={"chat_id": chat_id, "text": texto}, timeout=20)
        print(f"Mensaje Telegram estado: {resp_msg.status_code}")

        figuras_dir = BASE_DIR / "reports" / "figures"
        url_photo = base_tg + "/sendPhoto"
        for img_path in sorted(figuras_dir.glob("*.png")):
            with open(img_path, "rb") as img:
                resp_img = requests.post(url_photo, data={"chat_id": chat_id}, files={"photo": img}, timeout=25)
                print(f"Gráfico {img_path.name} enviado: {resp_img.status_code}")
    except Exception as e:
        print(f"Aviso: No se pudo completar el envío a Telegram ({e}).")

def enviar_correo(texto):
    remitente = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    destinatario = os.getenv("EMAIL_TO", remitente)
    if not remitente or not password:
        print("Correo no configurado (faltan variables EMAIL_USER / EMAIL_PASS).")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = "🧉 Actualización Multicanal Yerba Mate - Reporte ETL"
        msg["From"] = remitente
        msg["To"] = destinatario
        msg.set_content(texto)

        figuras_dir = BASE_DIR / "reports" / "figures"
        for img_file in sorted(figuras_dir.glob("*.png")):
            with open(img_file, "rb") as f:
                msg.add_attachment(f.read(), maintype="image", subtype="png", filename=img_file.name)

        servidor_smtp = "".join(["smtp", ".", "gmail.com"])
        with smtplib.SMTP_SSL(servidor_smtp, 465, timeout=25) as smtp:
            smtp.login(remitente, password)
            smtp.send_message(msg)
        print("Correo electrónico enviado exitosamente.")
    except Exception as e:
        print(f"Aviso: No se pudo completar el envío por correo ({e}).")

if __name__ == "__main__":
    resumen = generar_resumen_texto()
    print(resumen)
    enviar_telegram(resumen)
    enviar_correo(resumen)
