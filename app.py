import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURACIÓN DE CONEXIÓN ---
def inicializar_gspread():
    # Carga las credenciales desde los Secrets de Streamlit
    try:
        creds_info = st.secrets["gcp_service_account"]
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        
        # Abrir la hoja por su nombre
        return client.open("conta1").sheet1
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# Inicializamos la conexión
sheet = inicializar_gspread()

# --- 2. INTERFAZ DE LA APP ---
st.set_page_config(page_title="Contabilidad Bar", page_icon="🍺")
st.title("🍺 Gestión de Compras")

# Menú lateral para navegar
menu = st.sidebar.selectbox("Menú", ["Registrar Compra", "Ver Historial"])

if sheet is not None:
    if menu == "Registrar Compra":
        st.subheader("📝 Nueva Entrada")
        
        with st.form("form_registro", clear_on_submit=True):
            prod = st.text_input("Producto (ej: CERVEZA TERCIO)").upper()
            prov = st.text_input("Proveedor").upper()
            
            col1, col2 = st.columns(2)
            with col1:
                imp = st.number_input("Importe Total (€)", min_value=0.0, step=0.01, format="%.2f")
            with col2:
                cant = st.number_input("Cantidad", min_value=0.01, step=1.0)
            
            fecha = st.date_input("Fecha de Factura", datetime.now())
            
            boton_guardar = st.form_submit_button("Guardar en Google Sheets")

        if boton_guardar:
            if prod and imp > 0 and cant > 0:
                try:
                    # Leer datos actuales para comparar precios (Lógica rescatada del .exe)
                    datos_existentes = pd.DataFrame(sheet.get_all_records())
                    precio_u_actual = imp / cant
                    
                    # Comparar con el último registro de ese mismo producto
                    if not datos_existentes.empty and prod in datos_existentes['Producto'].values:
                        historial = datos_existentes[datos_existentes['Producto'] == prod]
                        ultimo_precio = pd.to_numeric(historial.iloc[-1]['Precio Unitario'])
                        
                        if precio_u_actual > (ultimo_precio + 0.001):
                            st.error(f"⚠️ ¡HA SUBIDO! Último: {ultimo_precio:.2f}€ | Hoy: {precio_u_actual:.2f}€")
                        elif precio_u_actual < (ultimo_precio - 0.001):
                            st.success(f"✅ ¡MÁS BARATO! Último: {ultimo_precio:.2f}€ | Hoy: {precio_u_actual:.2f}€")
                        else:
                            st.info(f"⚖️ Precio igual: {ultimo_precio:.2f}€")
                    else:
                        st.warning("🆕 Producto nuevo, no hay historial para comparar.")

                    # Guardar la nueva fila
                    nueva_fila = [
                        prod, 
                        prov, 
                        cant, 
                        round(precio_u_actual, 2), 
                        imp, 
                        fecha.strftime('%d/%m/%Y')
                    ]
                    sheet.append_row(nueva_fila)
                    
                    st.success(f"Registrado correctamente: {prod}")
                    st.balloons()
                    
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("Por favor, rellena todos los campos correctamente.")

    elif menu == "Ver Historial":
        st.subheader("📊 Últimos Registros")
        try:
            # Mostrar la tabla de Google Sheets
            data = pd.DataFrame(sheet.get_all_records())
            if not data.empty:
                # Buscador rápido
                filtro = st.text_input("🔍 Buscar producto...").upper()
                if filtro:
                    data = data[data['Producto'].str.contains(filtro, na=False)]
                
                st.dataframe(data.tail(20), use_container_width=True) # Muestra los últimos 20
            else:
                st.info("La hoja está vacía.")
        except Exception as e:
            st.error(f"Error al leer datos: {e}")
else:
    st.error("No se pudo establecer la conexión con Google Sheets. Revisa tus Secrets.")
