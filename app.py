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
        return client.open("conta1").sheet1
    except Exception as e:
        st.error(f"Error de conexión con Sheets: {e}")
        return None

# --- 2. CONFIGURACIÓN DE IA (Gemini) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Probamos con la ruta completa que exige la API v1
    model = genai.GenerativeModel('models/gemini-1.5-flash')
except Exception as e:
    st.error(f"Error al configurar Gemini: {e}")

def analizar_ticket_con_ia(imagen):
    prompt = """
    Analiza este ticket de bar. Extrae en JSON:
    {"proveedor": "NOMBRE", "total": 0.00, "fecha": "DD/MM/YYYY", "categoria": "TIPO"}
    Solo responde el JSON.
    """
    try:
        # Generar contenido con la imagen
        response = model.generate_content([prompt, imagen])
        res_text = response.text.strip()
        
        # Limpiar posibles bloques de código markdown
        res_text = res_text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(res_text)
    except Exception as e:
        # Si da el error 404, mostramos un mensaje más claro
        if "404" in str(e):
            st.error("Error 404: El modelo de Google no responde. Revisa que tu API KEY sea de 'Google AI Studio'.")
        else:
            st.error(f"Error de IA: {e}")
        return None

# --- 3. INTERFAZ ---
st.set_page_config(page_title="ContaBar IA", page_icon="🍻")
sheet = inicializar_gspread()

st.title("🍻 Contabilidad Bar con IA")

menu = st.sidebar.selectbox("Selecciona una opción", ["📸 Escanear Ticket", "📝 Registro Manual", "📊 Ver Historial"])

if sheet is not None:
    if menu == "📸 Escanear Ticket":
        st.subheader("Captura de Ticket")
        foto = st.camera_input("Haz una foto al ticket")
        
        if foto:
            img = Image.open(foto)
            with st.spinner("Leyendo ticket con IA..."):
                datos_ia = analizar_ticket_con_ia(img)
            
            if datos_ia:
                with st.form("confirmar_datos"):
                    prov = st.text_input("Proveedor", value=datos_ia.get("proveedor", ""))
                    cat = st.text_input("Categoría", value=datos_ia.get("categoria", ""))
                    total = st.number_input("Total (€)", value=float(datos_ia.get("total", 0.0)))
                    fecha = st.text_input("Fecha", value=datos_ia.get("fecha", ""))
                    
                    if st.form_submit_button("Guardar"):
                        sheet.append_row([cat.upper(), prov.upper(), 1, total, total, fecha])
                        st.success("¡Guardado!")
            else:
                st.warning("No se pudo procesar la imagen.")

    elif menu == "📝 Registro Manual":
        st.subheader("Entrada Manual")
        with st.form("manual"):
            p = st.text_input("Producto").upper()
            pr = st.text_input("Proveedor").upper()
            imp = st.number_input("Total (€)", min_value=0.0, step=0.01)
            f = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Añadir"):
                sheet.append_row([p, pr, 1, imp, imp, f.strftime('%d/%m/%Y')])
                st.success("Añadido.")

    elif menu == "📊 Ver Historial":
        st.subheader("Últimos registros")
        data = pd.DataFrame(sheet.get_all_records())
        st.dataframe(data.tail(20), use_container_width=True)
else:
    st.error("Conexión fallida.")
