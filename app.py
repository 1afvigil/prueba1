import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
def inicializar_gspread():
    # Usamos el diccionario de los Secrets
    creds_info = st.secrets["gcp_service_account"]
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(creds)
    
    # CAMBIO AQUÍ: Nombre exacto de tu hoja
    return client.open("conta1").sheet1sheet = inicializar_gspread()

# --- LÓGICA DE LA APP ---
st.title("🍹 Gestión de Compras")

# Formulario para móvil
with st.form("registro_compra", clear_on_submit=True):
    prod = st.text_input("Producto").upper()
    prov = st.text_input("Proveedor").upper()
    imp = st.number_input("Importe Total (€)", min_value=0.0, step=0.01)
    cant = st.number_input("Cantidad", min_value=0.01, step=1.0)
    fecha = st.date_input("Fecha", datetime.now())
    
    boton = st.form_submit_button("Guardar en Google Sheets")

if boton:
    if prod and imp > 0:
        try:
            # Calcular precio unitario
            precio_u = imp / cant
            # Preparar fila para insertar
            nueva_fila = [prod, prov, cant, precio_u, imp, fecha.strftime('%d/%m/%Y')]
            
            # Enviar a Google Sheets
            sheet.append_row(nueva_fila)
            st.success(f"✅ ¡Guardado! {prod} registrado correctamente.")
            st.balloons()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    else:
        st.warning("Faltan datos por rellenar.")