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
        # Asegúrate de que tu hoja en Google Drive se llama "conta1"
        return client.open("conta1").sheet1
    except Exception as e:
        st.error(f"Error de conexión con Sheets: {e}")
        return None

# --- 2. CONFIGURACIÓN DE IA (Gemini) ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # Configuramos el modelo para que sea menos estricto con el contenido
    model = genai.GenerativeModel('gemini-1.5-flash')
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
        # Enviamos la imagen y el prompt
        response = model.generate_content([prompt, imagen])
        
        # Limpieza de la respuesta para evitar errores de formato
        res_text = response.text.strip()
        start = res_text.find('{')
        end = res_text.rfind('}') + 1
        if start != -1 and end != 0:
            return json.loads(res_text[start:end])
        return None
    except Exception as e:
        st.error(f"La IA no pudo leer el ticket: {e}")
        return None

# --- 3. INTERFAZ DE USUARIO ---
st.set_page_config(page_title="ContaBar IA", page_icon="🍻", layout="centered")
sheet = inicializar_gspread()

st.title("🍻 Sistema Contable con IA")

menu = st.sidebar.selectbox("Selecciona una opción", ["📸 Escanear Ticket", "📝 Registro Manual", "📊 Ver Historial"])

if sheet is not None:
    # --- ESCÁNER CON IA ---
    if menu == "📸 Escanear Ticket":
        st.subheader("Captura de Ticket")
        foto = st.camera_input("Haz una foto al ticket del proveedor")
        
        if foto:
            img = Image.open(foto)
            with st.spinner("Gemini analizando el ticket..."):
                datos_ia = analizar_ticket_con_ia(img)
            
            if datos_ia:
                st.success("¡Lectura exitosa!")
            else:
                st.warning("La IA no detectó datos automáticos. Rellena el formulario manualmente.")
                datos_ia = {}

            # Formulario de confirmación (se rellena con lo que diga la IA o vacío)
            with st.form("confirmar_datos"):
                prov = st.text_input("Proveedor", value=datos_ia.get("proveedor", "")).upper()
                prod = st.text_input("Producto/Familia", value=datos_ia.get("categoria", "")).upper()
                col1, col2 = st.columns(2)
                with col1:
                    total = st.number_input("Importe Total (€)", value=float(datos_ia.get("total", 0.0)), step=0.01)
                with col2:
                    fecha = st.text_input("Fecha", value=datos_ia.get("fecha", datetime.now().strftime('%d/%m/%Y')))
                
                if st.form_submit_button("Guardar en Google Sheets"):
                    # Comparar con el último precio (Lógica original)
                    try:
                        historial = pd.DataFrame(sheet.get_all_records())
                        if not historial.empty and prod in historial['Producto'].values:
                            ultimo_p = pd.to_numeric(historial[historial['Producto'] == prod].iloc[-1]['Precio Unitario'])
                            if total > ultimo_p: st.error(f"⚠️ ¡HA SUBIDO! (Antes: {ultimo_p}€)")
                            elif total < ultimo_p: st.success(f"✅ ¡HA BAJADO! (Antes: {ultimo_p}€)")
                    except: pass

                    # Guardar fila
                    sheet.append_row([prod, prov, 1, total, total, fecha])
                    st.success(f"Guardado: {prov} - {total}€")
                    st.balloons()

    # --- REGISTRO MANUAL ---
    elif menu == "📝 Registro Manual":
        st.subheader("Entrada de datos manual")
        with st.form("manual"):
            p = st.text_input("Producto").upper()
            pr = st.text_input("Proveedor").upper()
            imp = st.number_input("Total (€)", min_value=0.0, step=0.01)
            f = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Añadir"):
                sheet.append_row([p, pr, 1, imp, imp, f.strftime('%d/%m/%Y')])
                st.success("Añadido.")

    # --- HISTORIAL ---
    elif menu == "📊 Ver Historial":
        st.subheader("Últimos 20 registros")
        try:
            data = pd.DataFrame(sheet.get_all_records())
            st.dataframe(data.tail(20), use_container_width=True)
        except:
            st.write("No hay datos o la hoja está mal configurada.")

else:
    st.error("No se detecta la conexión. Revisa los Secrets y el nombre de la hoja 'conta1'.")
