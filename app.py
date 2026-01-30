import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytesseract
import cv2
import numpy as np
from PIL import Image
import re

# Configuración de página para móvil
st.set_page_config(page_title="Bar Cloud OCR", layout="centered")

# --- CONEXIÓN GOOGLE SHEETS ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
except Exception as e:
    st.error("Error de conexión con Google Sheets. Revisa los Secrets.")
    st.stop()

st.title("🍺 Gestión de Bar Cloud")

# Menú lateral
menu = st.sidebar.selectbox("Menú", ["➕ Añadir Manual", "📸 Escanear Ticket", "📋 Historial"])

# --- FUNCIÓN DE LIMPIEZA OCR ---
def extraer_datos_ticket(texto):
    """Lógica para extraer el importe total del texto del ticket"""
    # Busca patrones de precios (ej: 10,50 o 10.50)
    precios = re.findall(r'\d+[.,]\d{2}', texto)
    if precios:
        # Normalmente el importe total es el último que aparece en el ticket
        ultimo_precio = precios[-1].replace(',', '.')
        return float(ultimo_precio)
    return 0.0

# --- PANTALLA: AÑADIR MANUAL ---
if menu == "➕ Añadir Manual":
    st.subheader("Registro de Producto")
    with st.form("registro_manual", clear_on_submit=True):
        producto = st.text_input("PRODUCTO").upper()
        proveedor = st.text_input("PROVEEDOR").upper()
        col1, col2 = st.columns(2)
        with col1:
            importe = st.number_input("IMPORTE TOTAL (€)", min_value=0.0, format="%.2f")
        with col2:
            cantidad = st.number_input("CANTIDAD", min_value=0.1, value=1.0)
        
        fecha = st.date_input("FECHA", datetime.now())
        
        if st.form_submit_button("💾 Guardar"):
            if producto and importe > 0:
                nueva_fila = pd.DataFrame([{
                    "Producto": producto, "Proveedor": proveedor, "Cantidad": cantidad,
                    "Precio Unitario": importe/cantidad, "Importe": importe,
                    "Fecha": fecha.strftime('%d/%m/%Y'), "Familia": "MANUAL"
                }])
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_actualizado)
                st.success("¡Guardado!")
                st.balloons()

# --- PANTALLA: ESCANEAR TICKET (OCR) ---
elif menu == "📸 Escanear Ticket":
    st.subheader("Escáner de Tickets")
    foto = st.camera_input("Toma una foto al ticket")
    
    if foto:
        st.info("🔍 Procesando imagen...")
        # Procesamiento de imagen
        img = Image.open(foto)
        img_array = np.array(img)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Ejecutar OCR (Tesseract)
        texto_detectado = pytesseract.image_to_string(img_cv, lang='spa')
        importe_sugerido = extraer_datos_ticket(texto_detectado)
        
        st.divider()
        st.write("**Texto extraído del ticket:**")
        st.caption(texto_detectado[:200] + "...") # Muestra un resumen del texto
        
        # Formulario rápido con datos detectados
        with st.form("confirmar_ocr"):
            prod_ocr = st.text_input("Producto/Proveedor detectado", value="TICKET OCR").upper()
            imp_ocr = st.number_input("Importe Detectado (€)", value=importe_sugerido)
            st.info("Verifica el importe antes de guardar.")
            
            if st.form_submit_button("✅ Confirmar y subir a la nube"):
                nueva_fila = pd.DataFrame([{
                    "Producto": prod_ocr, "Proveedor": "ESCANEADO", "Cantidad": 1,
                    "Precio Unitario": imp_ocr, "Importe": imp_ocr,
                    "Fecha": datetime.now().strftime('%d/%m/%Y'), "Familia": "OCR"
                }])
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_actualizado)
                st.success("¡Ticket guardado en Google Sheets!")

# --- PANTALLA: HISTORIAL ---
elif menu == "📋 Historial":
    st.subheader("Últimos Registros")
    busqueda = st.text_input("Filtrar por nombre...")
    if busqueda:
        df_mostrar = df[df['Producto'].str.contains(busqueda.upper(), na=False)]
    else:
        df_mostrar = df
    
    st.dataframe(df_mostrar.sort_index(ascending=False), use_container_width=True)
