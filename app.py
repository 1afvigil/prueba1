import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
from PIL import Image
import pytesseract
import re

# --- 1. CONFIGURACIÓN DE CONEXIÓN (Google Sheets) ---
def inicializar_gspread():
    try:
        creds_info = st.secrets["gcp_service_account"]
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        # Nombre de tu hoja compartido anteriormente
        return client.open("conta1").sheet1
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

sheet = inicializar_gspread()

# --- 2. LÓGICA OCR RESCATADA DE TU CÓDIGO ORIGINAL ---
def detectar_proveedor(texto):
    texto = texto.upper()
    proveedores = ["MERCADONA", "COCA-COLA", "COCA COLA", "CANDELAS", "DISBESA", "VOLDIS", "CIFUENTES", "LACTALIS"]
    for p in proveedores:
        if p in texto:
            return p
    return "DESCONOCIDO"

def extraer_total_inteligente(texto):
    # Basado en tu regex original: NUM = '-?\\d+(?:[.,]\\d+)?'
    # Buscamos patrones de precio comunes en tickets
    numeros = re.findall(r'\d+[.,]\d{2}', texto)
    if numeros:
        # Limpiamos y convertimos a float, devolviendo el más alto (suele ser el total)
        valores = [float(n.replace(',', '.')) for n in numeros]
        return max(valores)
    return 0.0

# --- 3. INTERFAZ STREAMLIT ---
st.set_page_config(page_title="App Bar Conta", page_icon="🍺")
st.title("🍺 Gestión de Compras Bar")

menu = st.sidebar.selectbox("Menú", ["Registrar Compra", "📸 Escanear Ticket", "📊 Ver Historial"])

if sheet is not None:
    # --- OPCIÓN: REGISTRO MANUAL ---
    if menu == "Registrar Compra":
        st.subheader("📝 Registro Manual")
        with st.form("form_manual", clear_on_submit=True):
            prod = st.text_input("Producto").upper()
            prov = st.text_input("Proveedor").upper()
            col1, col2 = st.columns(2)
            with col1:
                imp = st.number_input("Importe Total (€)", min_value=0.0, step=0.01)
            with col2:
                cant = st.number_input("Cantidad", min_value=0.01, step=1.0)
            fecha = st.date_input("Fecha", datetime.now())
            
            if st.form_submit_button("Guardar en conta1"):
                if prod and imp > 0:
                    datos = pd.DataFrame(sheet.get_all_records())
                    precio_u = imp / cant
                    
                    # Alerta de precios (Tu lógica original)
                    if not datos.empty and prod in datos['Producto'].values:
                        ultimo = pd.to_numeric(datos[datos['Producto'] == prod].iloc[-1]['Precio Unitario'])
                        if precio_u > ultimo: st.error(f"⚠️ Sube de {ultimo:.2f}€ a {precio_u:.2f}€")
                        elif precio_u < ultimo: st.success(f"✅ Baja de {ultimo:.2f}€ a {precio_u:.2f}€")
                    
                    sheet.append_row([prod, prov, cant, round(precio_u, 2), imp, fecha.strftime('%d/%m/%Y')])
                    st.success("Guardado correctamente")
                    st.balloons()

    # --- OPCIÓN: ESCÁNER (MOVIL) ---
    elif menu == "📸 Escanear Ticket":
        st.subheader("📸 Escáner con Cámara")
        foto = st.camera_input("Toma una foto al ticket")
        
        if foto:
            with st.spinner("Analizando ticket..."):
                img = Image.open(foto)
                texto_ocr = pytesseract.image_to_string(img)
                
                prov_auto = detectar_proveedor(texto_ocr)
                total_auto = extraer_total_inteligente(texto_ocr)
            
            st.info(f"Detección: {prov_auto} | Total: {total_auto}€")
            
            with st.form("confirmar_ocr"):
                c1, c2 = st.columns(2)
                f_prod = c1.text_input("Producto", value="VARIOS").upper()
                f_prov = c2.text_input("Proveedor", value=prov_auto).upper()
                f_imp = c1.number_input("Importe (€)", value=total_auto)
                f_cant = c2.number_input("Cantidad", value=1.0)
                
                if st.form_submit_button("Confirmar Lectura"):
                    precio_u = f_imp / f_cant
                    sheet.append_row([f_prod, f_prov, f_cant, round(precio_u, 2), f_imp, datetime.now().strftime('%d/%m/%Y')])
                    st.success("Ticket registrado")

    # --- OPCIÓN: HISTORIAL ---
    elif menu == "📊 Ver Historial":
        st.subheader("📋 Últimos movimientos en conta1")
        try:
            df_historial = pd.DataFrame(sheet.get_all_records())
            if not df_historial.empty:
                busqueda = st.text_input("Filtrar producto...").upper()
                if busqueda:
                    df_historial = df_historial[df_historial['Producto'].str.contains(busqueda)]
                st.dataframe(df_historial.tail(15), use_container_width=True)
            else:
                st.write("No hay datos todavía.")
        except Exception as e:
            st.error(f"Error al leer historial: {e}")

else:
    st.warning("Configura los Secrets y comparte la hoja 'conta1' con el email de la cuenta de servicio.")
