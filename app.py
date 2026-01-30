import streamlit as st
import pandas as pd
from datetime import datetime
# Importamos tus funciones recuperadas
from excel_utils import cargar_excel, guardar_datos 

st.set_page_config(page_title="Gestión Bar", layout="centered")

st.title("📊 Contabilidad de Bar")

# --- BARRA LATERAL ---
menu = st.sidebar.selectbox("Menú", ["Añadir Compra", "Historial de Precios", "Escanear Ticket"])

# Cargar datos usando tu lógica original
df = cargar_excel()

if menu == "Añadir Compra":
    st.subheader("📝 Registrar Nuevo Producto")
    
    with st.form("registro"):
        producto = st.text_input("Producto").upper()
        familia = st.text_input("Familia").upper()
        proveedor = st.text_input("Proveedor").upper()
        
        col1, col2 = st.columns(2)
        with col1:
            importe = st.number_input("Importe Total (€)", min_value=0.0, step=0.01)
            cantidad = st.number_input("Cantidad", min_value=0.01, step=1.0)
        with col2:
            fecha = st.date_input("Fecha", datetime.now())
        
        submit = st.form_submit_button("Guardar en Excel")
        
        if submit:
            if producto and importe and cantidad:
                precio_u = importe / cantidad
                
                # Crear el diccionario con tu estructura original
                nuevo = {
                    'Producto': producto,
                    'Familia': familia,
                    'Proveedor': proveedor,
                    'Cantidad': cantidad,
                    'Precio Unitario': precio_u,
                    'Importe': importe,
                    'Fecha': fecha.strftime('%d/%m/%Y')
                }
                
                # Usar tu función de excel_utils para guardar
                df_nuevo = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
                guardar_datos(df_nuevo)
                st.success(f"✅ {producto} guardado. Precio Unitario: {precio_u:.2f}€")
            else:
                st.error("Faltan campos obligatorios")

elif menu == "Historial de Precios":
    st.subheader("🔍 Buscador de Productos")
    busqueda = st.text_input("Escribe el nombre del producto...")
    
    if busqueda:
        # Filtro idéntico al de tu función buscar_filtrado()
        filtro = df[df['Producto'].str.contains(busqueda.upper(), na=False)]
        st.dataframe(filtro)
    else:
        st.write("Mostrando últimos registros:")
        st.dataframe(df.tail(10))

elif menu == "Escanear Ticket":
    st.subheader("📸 Cargar Factura")
    archivo = st.camera_input("Toma una foto al ticket")
    if archivo:
        st.info("Imagen recibida. Procesando con la lógica de facturas_ocr.py...")
        # Aquí llamaríamos a mostrar_ventana_facturas pero adaptado a web
