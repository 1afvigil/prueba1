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

# --- 2. CONFIGURACIÓN DE IA (Gemini con fallback de modelo) ---
def configurar_ia():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Intentamos varios nombres comunes del modelo por si uno falla (404)
        nombres_modelo = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-1.5-flash-latest']
        
        for nombre in nombres_modelo:
            try:
                model = genai.GenerativeModel(nombre)
                # Prueba rápida de conexión
                return model
            except:
                continue
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error al configurar Gemini: {e}")
        return None

model = configurar_ia()

def analizar_ticket_con_ia(imagen):
    prompt = """
    Analiza la imagen de este ticket de bar. Extrae los datos y responde UNICAMENTE en este formato JSON:
    {"proveedor": "NOMBRE", "total": 0.00, "fecha": "DD/MM/YYYY", "categoria": "TIPO"}
    Si no ves la fecha, usa la de hoy. Si no ves el total, pon 0.00.
    """
    try:
        # Configuramos una temperatura baja para que no invente datos
        response = model.generate_content([prompt, imagen])
        res_text = response.text.strip()
        
        # Limpiar posibles bloques de código de la respuesta
        res_text = res_text.replace('```json', '').replace('```', '').strip()
        
        # Buscar el primer '{' y el último '}' para extraer solo el JSON
        inicio = res_text.find('{')
        fin = res_text.rfind('}') + 1
        if inicio != -1:
            return json.loads(res_text[inicio:fin])
        return None
    except Exception as e:
        st.error(f"Error de la IA: {e}")
        return None

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="ContaBar IA", page_icon="🍻")
sheet = inicializar_gspread()

st.title("🍻 Gestión de Bar con IA")

menu = st.sidebar.selectbox("Menú", ["📸 Escanear Ticket", "📝 Registro Manual", "📊 Ver Historial"])

if sheet is not None:
    if menu == "📸 Escanear Ticket":
        st.subheader("Escanear factura/ticket")
        foto = st.camera_input("Haz la foto al ticket")
        
        if foto:
            img = Image.open(foto)
            with st.spinner("La IA está leyendo los datos..."):
                datos_ia = analizar_ticket_con_ia(img)
            
            if datos_ia:
                with st.form("confirmacion_ia"):
                    prov = st.text_input("Proveedor", value=datos_ia.get("proveedor", ""))
                    cat = st.text_input("Categoría/Producto", value=datos_ia.get("categoria", ""))
                    col1, col2 = st.columns(2)
                    with col1:
                        total = st.number_input("Total (€)", value=float(datos_ia.get("total", 0.0)))
                    with col2:
                        fecha = st.text_input("Fecha", value=datos_ia.get("fecha", datetime.now().strftime('%d/%m/%Y')))
                    
                    if st.form_submit_button("Guardar en conta1"):
                        # Guardar en Sheets
                        sheet.append_row([cat.upper(), prov.upper(), 1, total, total, fecha])
                        st.success(f"Guardado correctamente en Google Sheets")
                        st.balloons()
            else:
                st.error("No se pudo extraer información. Prueba con otra foto o rellena manual.")

    elif menu == "📝 Registro Manual":
        st.subheader("Entrada Manual")
        with st.form("form_manual"):
            p = st.text_input("Producto/Categoría").upper()
            pr = st.text_input("Proveedor").upper()
            imp = st.number_input("Total (€)", min_value=0.0, step=0.01)
            f = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Guardar"):
                sheet.append_row([p, pr, 1, imp, imp, f.strftime('%d/%m/%Y')])
                st.success("Añadido.")

    elif menu == "📊 Ver Historial":
        st.subheader("Últimas compras")
        try:
            data = pd.DataFrame(sheet.get_all_records())
            st.dataframe(data.tail(20), use_container_width=True)
        except:
            st.write("Aún no hay datos registrados.")
else:
    st.error("Fallo de conexión. Revisa tus credenciales en Secrets.")
