import streamlit as st
import pandas as pd
from db import *
from datetime import datetime

st.set_page_config(
    page_title="Sistema Profesional de Inventario",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; border-bottom: 1px solid #FFF; margin-bottom: 1rem; }
    .stTabs { margin-top: 1rem; }
    .success-box { padding: 1rem; background-color: #d4edda; border-color: #c3e6cb; color: #155724; border-radius: 0.25rem; margin: 1rem 0; }
    .warning-box { padding: 1rem; background-color: #fff3cd; border-color: #ffeeba; color: #856404; border-radius: 0.25rem; margin: 1rem 0; }
    .stButton>button { width: 100%; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Gestión de Inventario</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.image("https://i2.wp.com/nubix.cloud/wp-content/uploads/2020/08/TRANSPARENTE_NUBIX-COLOR.png?fit=1506%2C1236&ssl=1", use_container_width=True)
    st.markdown("<div style='margin-top: -20px;'></div>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div style='text-align: center; margin: 10px 0;'><strong style='font-size: 1.1rem;'>Resumen de Inventario</strong></div>", unsafe_allow_html=True)
    
    metricas = get_metricas()
    
    st.markdown(f"""
    <div style='padding: 10px 0;'>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>Total en inventario:</strong> <span>{metricas['total_en_inventario']}</span></div>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>Envios realizados:</strong> <span>{metricas['total_envios']}</span></div>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>SDs configuradas:</strong> <span>{metricas['sds_configuradas']}</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(f"<div style='text-align: center; padding: 10px 0;'><strong>Fecha de hoy:</strong> {datetime.now().strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.button("Recargar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Realizar Envio",
    "Inventario Fisico",
    "Historial de Envios",
    "Configurar SD",
    "Agregar al inventario"
])

# ========== TAB 1: REALIZAR ENVIO ==========
with tab1:
    st.subheader("Realizar Nuevo Envio")
    
    productos = get_productos()
    if not productos:
        st.warning("No hay productos en el catálogo. Ve a 'Agregar al inventario' para crear productos y agregar stock.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            producto_opciones = {f"{p['codigo_sku']} - {p['nombre']}": p['id'] for p in productos}
            producto_seleccionado = st.selectbox("Seleccionar producto:", options=list(producto_opciones.keys()), key="prod_select")
            producto_id = producto_opciones[producto_seleccionado]
            
            stock_disponible = len(obtener_stock_disponible(producto_id=producto_id))
            st.caption(f"Stock disponible: {stock_disponible}")
            
            cantidad = st.number_input("Cantidad:", min_value=1, max_value=stock_disponible if stock_disponible > 0 else 1, value=1, step=1)
            
            if st.button("Agregar al envío", use_container_width=True):
                if stock_disponible >= cantidad:
                    existing = next((item for item in st.session_state.carrito if item['producto_id'] == producto_id), None)
                    if existing:
                        existing['cantidad'] += cantidad
                    else:
                        nombre = next(p['nombre'] for p in productos if p['id'] == producto_id)
                        st.session_state.carrito.append({
                            'producto_id': producto_id,
                            'nombre': nombre,
                            'cantidad': cantidad,
                            'disponible': stock_disponible
                        })
                    st.success(f"Agregado {cantidad} x {nombre}")
                    st.rerun()
                else:
                    st.error("No hay suficiente stock disponible.")
        
        with col2:
            st.markdown("##### Carrito actual")
            if st.session_state.carrito:
                total_items = sum(item['cantidad'] for item in st.session_state.carrito)
                st.markdown(f"**Total productos: {total_items}**")
                
                for i, item in enumerate(st.session_state.carrito):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"{item['nombre']} x{item['cantidad']}")
                    with col_b:
                        if st.button("🗑️", key=f"del_{i}"):
                            st.session_state.carrito.pop(i)
                            st.rerun()
                
                if st.button("Vaciar carrito", use_container_width=True):
                    st.session_state.carrito = []
                    st.rerun()
            else:
                st.info("Carrito vacío")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            folio = st.text_input("Número de Folio:", placeholder="Ej: FOL-2024-001")
        with col2:
            destino = st.text_input("Destino (opcional):", placeholder="Cliente o ubicación")
        
        descripcion = st.text_area("Descripción del envío (opcional):", placeholder="Notas adicionales...")
        
        if st.button("Procesar Envío", use_container_width=True, type="primary"):
            if not folio:
                st.error("El número de folio es obligatorio.")
            elif not st.session_state.carrito:
                st.error("El carrito está vacío. Agrega productos.")
            else:
                try:
                    with st.spinner("Procesando envío..."):
                        items_envio = [{'producto_id': item['producto_id'], 'cantidad': item['cantidad']} for item in st.session_state.carrito]
                        resultado = procesar_envio(items_envio, folio, destino, descripcion)
                    
                    st.success(f"**Envío procesado exitosamente**\n- Folio: {resultado['folio']}\n- ID de envío: {resultado['envio_id']}\n- Items enviados: {resultado['items_procesados']}")
                    st.balloons()
                    st.session_state.carrito = []
                    st.cache_data.clear()
                    st.rerun()
                    
                except ValueError as e:
                    st.error(f"Error: {str(e)}")
                except Exception as e:
                    st.error(f"Error inesperado: {str(e)}")

# ========== TAB 2: INVENTARIO FISICO ==========
with tab2:
    st.subheader("Estado del Inventario Fisico")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_estado = st.selectbox("Filtrar por estado:", ["TODOS", "DISPONIBLE", "CONFIGURADO", "ENVIADO", "DEFECTUOSO"])
    with col2:
        filtro_tipo = st.selectbox("Filtrar por tipo:", ["TODOS", "RASPBERRY", "SD", "CABLE_USB", "CABLE_ETHERNET"])
    with col3:
        search_term = st.text_input("Buscar:", placeholder="SKU, nombre...")
    
    inventario = obtener_todo_el_inventario()
    
    if inventario:
        df_inv = pd.DataFrame(inventario)
        
        if filtro_estado != "TODOS":
            df_inv = df_inv[df_inv['estado'] == filtro_estado]
        if filtro_tipo != "TODOS":
            df_inv = df_inv[df_inv['tipo'] == filtro_tipo]
        if search_term:
            mask = (df_inv['codigo_sku'].astype(str).str.contains(search_term, case=False, na=False) |
                    df_inv['producto_nombre'].astype(str).str.contains(search_term, case=False, na=False))
            df_inv = df_inv[mask]
        
        st.dataframe(df_inv, use_container_width=True, hide_index=True, column_config={
            "id": "ID", "codigo_sku": "SKU", "producto_nombre": "Producto", "tipo": "Tipo",
            "estado": "Estado", "fecha_ingreso": "Fecha Ingreso", "config_final": "Config Final",
            "fecha_configuracion": "Fecha Config", "observaciones": "Observaciones"
        })
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"Mostrando {len(df_inv)} items")
        with col2:
            disponibles = len(df_inv[df_inv['estado'] == 'DISPONIBLE'])
            st.success(f"{disponibles} disponibles")
        with col3:
            configurados = len(df_inv[df_inv['estado'] == 'CONFIGURADO'])
            st.warning(f"{configurados} configurados")
    else:
        st.info("No hay items en el inventario")

# ========== TAB 3: HISTORIAL DE ENVIOS ==========
with tab3:
    st.subheader("Historial de Envios")
    
    envios = get_envios()
    
    if envios:
        df_envios = pd.DataFrame(envios)
        
        search_folio = st.text_input("Buscar por folio:", key="search_envios")
        if search_folio:
            mask = df_envios['folio'].astype(str).str.contains(search_folio, case=False, na=False)
            df_envios = df_envios[mask]
        
        st.dataframe(df_envios, use_container_width=True, hide_index=True, column_config={
            "id": "ID", "folio": "Folio", "fecha_salida": "Fecha Salida", "destino": "Destino",
            "descripcion": "Descripción", "total_items": "Items", "created_at": "Registrado"
        })
        
        st.markdown("---")
        st.subheader("Ver Detalle de Envio")
        
        selected_envio = st.selectbox(
            "Seleccionar envio:",
            options=df_envios['id'].tolist(),
            format_func=lambda x: f"Folio: {df_envios[df_envios['id']==x]['folio'].iloc[0]} - {df_envios[df_envios['id']==x]['fecha_salida'].iloc[0]}"
        )
        
        if selected_envio:
            detalle = get_detalle_envio(selected_envio)
            if detalle:
                st.markdown("##### Items enviados:")
                df_detalle = pd.DataFrame(detalle)
                st.dataframe(df_detalle, use_container_width=True, hide_index=True, column_config={
                    "producto_nombre": "Producto", "codigo_sku": "SKU", "tipo": "Tipo",
                    "config_final": "Config SD", "estado": "Estado"
                })
    else:
        st.info("No hay envios registrados")

# ========== TAB 4: CONFIGURAR SD ==========
with tab4:
    st.subheader("Configurar Tarjetas SD")
    
    sds_disponibles = obtener_stock_disponible(tipo='SD')
    
    if sds_disponibles:
        st.markdown("##### SDs disponibles para configurar:")
        df_sds = pd.DataFrame(sds_disponibles)
        st.dataframe(df_sds[['id', 'codigo_sku', 'producto_nombre', 'fecha_ingreso']], use_container_width=True, hide_index=True, column_config={
            "id": "ID", "codigo_sku": "SKU", "producto_nombre": "SD", "fecha_ingreso": "Fecha Ingreso"
        })
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            sd_seleccionada = st.selectbox(
                "Seleccionar SD a configurar:",
                options=[s['id'] for s in sds_disponibles],
                format_func=lambda x: f"ID {x} - {next(s['producto_nombre'] for s in sds_disponibles if s['id']==x)}"
            )
        with col2:
            config_final = st.date_input("Fecha de configuracion final:", value=datetime.now().date())
        
        if st.button("Configurar SD", use_container_width=True, type="primary"):
            try:
                configurar_sd(sd_seleccionada, config_final)
                st.success("SD configurada exitosamente y marcada como configurada")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    else:
        st.warning("No hay SDs disponibles para configurar")

# ========== TAB 5: RECEPCION DE MERCANCIA (con creación de productos) ==========
with tab5:
    st.subheader("Agregar al Inventario")
    
    # Expansor para crear un nuevo producto
    with st.expander("Agregar producto al inventario"):
        with st.form("nuevo_producto"):
            nombre = st.text_input("Nombre del producto:", placeholder="Ej: Raspberry Pi 5 4GB")
            tipo = st.selectbox("Tipo:", ["RASPBERRY", "SD", "CABLE_USB", "CABLE_ETHERNET", "ACCESORIO"])
            descripcion = st.text_area("Descripción (opcional):")
            
            st.info("El SKU se generará automáticamente según el tipo de producto.")
            
            if st.form_submit_button("Crear producto"):
                if not nombre:
                    st.error("El nombre es obligatorio.")
                else:
                    try:
                        nuevo_id = crear_producto(nombre, tipo, descripcion)
                        st.success(f"Producto '{nombre}' creado con SKU autogenerado. Ahora puedes agregar stock.")
                        st.cache_data.clear()
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
    
    st.markdown("---")
    
    # Recepción de stock
    productos = get_productos()
    if not productos:
        st.info("No hay productos en el catálogo. Utiliza el formulario de arriba para crear el primer producto.")
    else:
        with st.expander("Agregar stock de producto existente al inventario"):
            with st.form("agregar_inventario"):
                col1, col2 = st.columns(2)
                with col1:
                    producto_seleccionado = st.selectbox(
                        "Seleccionar producto existente:",
                        options=[p['id'] for p in productos],
                        format_func=lambda x: f"{next(p['codigo_sku'] for p in productos if p['id']==x)} - {next(p['nombre'] for p in productos if p['id']==x)}"
                    )
                    cantidad = st.number_input("Cantidad a ingresar:", min_value=1, max_value=100, value=1)
                with col2:
                    fecha_ingreso = st.date_input("Fecha de ingreso:", value=datetime.now().date())
                
                if st.form_submit_button("Registrar Ingreso"):
                    try:
                        ids = agregar_producto_a_inventario(producto_seleccionado, cantidad, fecha_ingreso)
                        st.success(f"{cantidad} unidad(es) agregada(s) al inventario exitosamente")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# ========== FOOTER ==========
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 1rem;'>
        <p>Sistema Profesional de Gestion de Inventario v3.0</p>
        <p style='font-size: 0.8rem;'>Base de datos vacía al inicio - Creación de productos en recepción</p>
    </div>
    """,
    unsafe_allow_html=True
)