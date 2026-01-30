import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytesseract
import cv2
import numpy as np
from PIL import Image
import re

# Configuración de página optimizada para móviles
st.set_page_config(page_title="Bar Cloud OCR", layout="centered")

# --- CONEXIÓN GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
except Exception as e:
    st.error("Error de conexión. Revisa los Secrets y permisos de la hoja.")
    st.stop()

st.title("🍺 Gestión de Bar Cloud")

# Menú lateral
menu = st.sidebar.selectbox("Menú", ["➕ Añadir Manual", "📸 Escanear Ticket", "📋 Historial"])

# --- LÓGICA DE EXTRACCIÓN OCR ---
def extraer_datos_ticket(texto):
    """Busca el importe total (último número con decimales)"""
    precios = re.findall(r'\d+[.,]\d{2}', texto)
    if precios:
        ultimo_precio = precios[-1].replace(',', '.')
        return float(ultimo_precio)
    return 0.0

# --- PANTALLA: MANUAL ---
if menu == "➕ Añadir Manual":
    st.subheader("📝 Registro Manual")
    with st.form("registro_manual", clear_on_submit=True):
        producto = st.text_input("PRODUCTO").upper()
        proveedor = st.text_input("PROVEEDOR").upper()
        col1, col2 = st.columns(2)
        with col1:
            importe = st.number_input("IMPORTE TOTAL (€)", min_value=0.0, format="%.2f")
        with col2:
            cantidad = st.number_input("CANTIDAD", min_value=0.1, value=1.0)
        
        fecha = st.date_input("FECHA", datetime.now())
        
        if st.form_submit_button("💾 GUARDAR EN GOOGLE SHEETS"):
            if producto and importe > 0:
                nueva_fila = pd.DataFrame([{
                    "Producto": producto, "Familia": "MANUAL", "Proveedor": proveedor,
                    "Cantidad": cantidad, "Precio Unitario": importe/cantidad,
                    "Importe": importe, "Fecha": fecha.strftime('%d/%m/%Y')
                }])
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_actualizado)
                st.success("¡Guardado correctamente!")
                st.balloons()

# --- PANTALLA: OCR (ESCÁNER) ---
elif menu == "📸 Escanear Ticket":
    st.subheader("📸 Escáner de Tickets")
    foto = st.camera_input("Enfoca bien el ticket y con luz")
    
    if foto:
        try:
            with st.spinner("🔍 Analizando ticket..."):
                # 1. Procesar imagen para que no sea pesada
                img = Image.open(foto)
                img.thumbnail((800, 800)) # Reducir resolución para velocidad
                img_array = np.array(img)
                
                # 2. Convertir a escala de grises para mejor lectura
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                
                # 3. OCR
                texto_detectado = pytesseract.image_to_string(gray, lang='spa')
                importe_sugerido = extraer_datos_ticket(texto_detectado)
            
            st.success("✅ Lectura finalizada")
            
            # Formulario de confirmación
            with st.form("confirmar_ocr"):
                st.write("**Datos detectados:**")
                prod_ocr = st.text_input("PRODUCTO / PROVEEDOR", value="TICKET ESCANEADO").upper()
                imp_ocr = st.number_input("IMPORTE (€)", value=importe_sugerido, format="%.2f")
                
                if st.form_submit_button("🚀 CONFIRMAR Y SUBIR"):
                    nueva_fila = pd.DataFrame([{
                        "Producto": prod_ocr, "Familia": "OCR", "Proveedor": "TICKET",
                        "Cantidad": 1, "Precio Unitario": imp_ocr,
                        "Importe": imp_ocr, "Fecha": datetime.now().strftime('%d/%m/%Y')
                    }])
                    df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                    conn.update(data=df_actualizado)
                    st.success("¡Enviado a Google Sheets!")
            
            with st.expander("Ver texto extraído por el móvil"):
                st.text(texto_detectado)

        except Exception as e:
            st.error(f"Error técnico: {e}")
            st.info("Asegúrate de haber hecho el 'Reboot' tras crear el archivo packages.txt")

# --- PANTALLA: HISTORIAL ---
elif menu == "📋 Historial":
    st.subheader("📋 Últimos registros en la nube")
    st.dataframe(df.sort_index(ascending=False), use_container_width=True)
