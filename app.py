import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
from PIL import Image
import google.generativeai as genai
import json

# --- 1. CONFIGURACIÓN DE CONEXIÓN (Google Sheets) ---
def inicializar_gspread():
    try:
        creds_info = st.secrets["gcp_service_account"]
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        # Asegúrate de que tu hoja en Google Drive se llama exactamente "conta1"
        return client.open("conta1").sheet1
    except Exception as e:
        st.error(f"Error de conexión con Sheets: {e}")
        return None

# --- 2. CONFIGURACIÓN DE IA (Gemini) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Corregido a 'gemini-1.5-flash-latest' para evitar el error 404
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"Error al configurar Gemini: {e}")

def analizar_ticket_con_ia(imagen):
    prompt = """
    Eres un experto contable. Analiza esta imagen de un ticket de compra.
    Extrae: 
    1. Nombre del establecimiento (Proveedor).
    2. Importe total con IVA.
    3. Fecha de la compra (DD/MM/YYYY).
    4. Categoría breve (ej: BEBIDA, CARNE, LIMPIEZA).

    Responde EXCLUSIVAMENTE en formato JSON plano:
    {"proveedor": "NOMBRE", "total": 0.00, "fecha": "DD/MM/YYYY", "categoria": "TIPO"}
    """
    try:
        response = model.generate_content([prompt, imagen])
        res_text = response.text.strip()
        
        # Limpieza de formato JSON (elimina posibles marcas de Markdown)
        start = res_text.find('{')
        end = res_text.rfind('}') + 1
        if start != -1 and end != 0:
            return json.loads(res_text[start:end])
        return None
    except Exception as e:
        st.error(f"La IA tuvo un problema al procesar la imagen: {e}")
        return None

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="ContaBar IA", page_icon="🍻")
sheet = inicializar_gspread()

st.title("🍻 Contabilidad Bar con IA")

menu = st.sidebar.selectbox("Selecciona una opción", ["📸 Escanear Ticket", "📝 Registro Manual", "📊 Ver Historial"])

if sheet is not None:
    # --- OPCIÓN: ESCÁNER CON IA ---
    if menu == "📸 Escanear Ticket":
        st.subheader("Captura de Ticket")
        foto = st.camera_input("Haz una foto al ticket")
        
        if foto:
            img = Image.open(foto)
            with st.spinner("Gemini analizando el ticket..."):
                datos_ia = analizar_ticket_con_ia(img)
            
            if datos_ia:
                st.success("¡Lectura exitosa!")
            else:
                st.warning("No se detectaron datos automáticos. Rellena el formulario.")
                datos_ia = {}

            with st.form("confirmar_datos"):
                prov = st.text_input("Proveedor", value=datos_ia.get("proveedor", "")).upper()
                prod = st.text_input("Producto/Categoría", value=datos_ia.get("categoria", "")).upper()
                col1, col2 = st.columns(2)
                with col1:
                    total = st.number_input("Importe Total (€)", value=float(datos_ia.get("total", 0.0)), step=0.01)
                with col2:
                    fecha_str = st.text_input("Fecha", value=datos_ia.get("fecha", datetime.now().strftime('%d/%m/%Y')))
                
                if st.form_submit_button("Guardar en Google Sheets"):
                    # Lógica de comparación de precios
                    try:
                        historial = pd.DataFrame(sheet.get_all_records())
                        if not historial.empty and prod in historial['Producto'].values:
                            ultimo_p = pd.to_numeric(historial[historial['Producto'] == prod].iloc[-1]['Precio Unitario'])
                            if total > ultimo_p: 
                                st.error(f"⚠️ ¡Precio más alto! (Antes: {ultimo_p}€)")
                            elif total < ultimo_p: 
                                st.success(f"✅ ¡Precio más bajo! (Antes: {ultimo_p}€)")
                    except: pass

                    sheet.append_row([prod, prov, 1, total, total, fecha_str])
                    st.success(f"Guardado: {prov} por {total}€")
                    st.balloons()

    # --- OPCIÓN: REGISTRO MANUAL ---
    elif menu == "📝 Registro Manual":
        st.subheader("Entrada Manual")
        with st.form("manual"):
            p = st.text_input("Producto").upper()
            pr = st.text_input("Proveedor").upper()
            imp = st.number_input("Total (€)", min_value=0.0, step=0.01)
            f = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Añadir"):
                sheet.append_row([p, pr, 1, imp, imp, f.strftime('%d/%m/%Y')])
                st.success("Añadido correctamente.")

    # --- OPCIÓN: HISTORIAL ---
    elif menu == "📊 Ver Historial":
        st.subheader("Últimos 20 registros en conta1")
        try:
            data = pd.DataFrame(sheet.get_all_records())
            if not data.empty:
                st.dataframe(data.tail(20), use_container_width=True)
            else:
                st.info("La hoja está vacía.")
        except Exception as e:
            st.error(f"No se pudo cargar el historial: {e}")

else:
    st.error("Error crítico: No hay conexión con Google Sheets.")
