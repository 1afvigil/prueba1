import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from PIL import Image

# Configuración para que se vea bien en móviles
st.set_page_config(page_title="Gestión Bar Cloud", layout="centered")

st.title("📊 Control de Gastos Bar")

# 1. Conexión con Google Sheets
# Recuerda poner la URL en Settings -> Secrets de Streamlit Cloud
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
except Exception as e:
    st.error("Error de conexión. Revisa los Secrets y los permisos de la hoja.")
    st.stop()

# Menú lateral táctil
menu = st.sidebar.selectbox("Selecciona una opción", ["➕ Añadir Compra", "📸 Escanear Ticket", "📋 Ver Historial"])

if menu == "➕ Añadir Compra":
    st.subheader("Registro Manual")
    with st.form("form_registro", clear_on_submit=True):
        producto = st.text_input("PRODUCTO").upper()
        familia = st.text_input("FAMILIA").upper()
        proveedor = st.text_input("PROVEEDOR").upper()
        
        col1, col2 = st.columns(2)
        with col1:
            importe = st.number_input("IMPORTE TOTAL (€)", min_value=0.0, step=0.01, format="%.2f")
            cantidad = st.number_input("CANTIDAD", min_value=0.01, step=1.0, value=1.0)
        with col2:
            fecha = st.date_input("FECHA", datetime.now())
        
        btn_guardar = st.form_submit_button("💾 GUARDAR EN CLOUD")
        
        if btn_guardar:
            if producto and importe > 0:
                precio_u = importe / cantidad
                
                # Alerta de precio si el producto ya existe
                historial = df[df['Producto'] == producto]
                if not historial.empty:
                    ultimo_p = historial.iloc[-1]['Precio Unitario']
                    if precio_u > ultimo_p:
                        st.warning(f"⚠️ Más caro! (Antes: {ultimo_p:.2f}€)")
                    elif precio_u < ultimo_p:
                        st.success(f"✅ Más barato! (Antes: {ultimo_p:.2f}€)")

                # Nueva fila para Google Sheets
                nueva_fila = pd.DataFrame([{
                    "Producto": producto,
                    "Familia": familia,
                    "Proveedor": proveedor,
                    "Cantidad": cantidad,
                    "Precio Unitario": precio_u,
                    "Importe": importe,
                    "Fecha": fecha.strftime('%d/%m/%Y')
                }])
                
                # Actualizar Google Sheets
                df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                conn.update(data=df_actualizado)
                st.balloons()
                st.success("¡Datos guardados con éxito!")
            else:
                st.error("Faltan datos obligatorios (Producto e Importe)")

elif menu == "📋 Ver Historial":
    st.subheader("Historial de Compras")
    
    # Buscador rápido
    busqueda = st.text_input("🔍 Buscar producto...")
    if busqueda:
        df_filtrado = df[df['Producto'].str.contains(busqueda.upper(), na=False)]
        st.dataframe(df_filtrado.sort_index(ascending=False))
    else:
        st.dataframe(df.sort_index(ascending=False))

elif menu == "📸 Escanear Ticket":
    st.subheader("Escáner Inteligente")
    foto = st.camera_input("Toma una foto del ticket")
    
    if foto:
        st.info("🔄 Procesando imagen con OCR...")
        # Aquí es donde conectaremos tu archivo facturas_ocr.py
        # Por ahora te mostramos la imagen capturada
        img = Image.open(foto)
        st.image(img, caption="Ticket capturado", use_container_width=True)
        st.warning("⚠️ Lógica de OCR pendiente de enlazar con facturas_ocr.py")
