import streamlit as st
import pandas as pd
from db import *
from datetime import datetime

st.set_page_config(
    page_title="Sistema de Inventario - Nubix",
    page_icon="🎱",
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
    .info-box { padding: 1rem; background-color: #d1ecf1; border-color: #bee5eb; color: #0c5460; border-radius: 0.25rem; margin: 1rem 0; }
    .stButton>button { width: 100%; }
    .config-status { font-size: 0.9rem; padding: 0.2rem 0.5rem; border-radius: 0.25rem; }
    .status-disponible { background-color: #28a745; color: white; }
    .status-en-proceso { background-color: #ffc107; color: black; }
    .status-configurado { background-color: #17a2b8; color: white; }
    .status-enviado { background-color: #6c757d; color: white; }
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
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>Dispositivos configurados:</strong> <span>{metricas.get('dispositivos_configurados', 0)}</span></div>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>En configuración:</strong> <span>{metricas.get('dispositivos_en_configuracion', 0)}</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(f"<div style='text-align: center; padding: 10px 0;'><strong>Fecha de hoy:</strong> {datetime.now().strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.button("Recargar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Realizar Envio",
    "Inventario Fisico",
    "Historial de Envios",
    "Configurar SD",
    "Agregar al inventario",
    "Configurar Dispositivos"
])

# ========== TAB 1: REALIZAR ENVIO ==========
with tab1:
    st.subheader("Realizar Nuevo Envio")
    
    productos = get_productos()
    if not productos:
        st.warning("No hay productos en el items. Ve a 'Agregar al inventario' para crear items y agregar stock.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            producto_opciones = {f"{p['ref_prod']} - {p['nombre']}": p['id'] for p in productos}
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
            folio = st.text_input("Número de Folio:", placeholder="Ej: NBX XX0-X000")
        with col2:
            destino = st.text_input("Destino (opcional):", placeholder="Cliente o ubicación")
        
        descripcion = st.text_area("Descripción del envío (opcional):", placeholder="Notas adicionales...")
        
        if st.button("Procesar Envío", use_container_width=True, type="primary"):
            if not folio:
                st.error("El número de folio es obligatorio.")
            elif not st.session_state.carrito:
                st.error("El carrito está vacío")
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
        filtro_estado = st.selectbox("Filtrar por estado:", ["TODOS", "DISPONIBLE", "EN PROCESO", "CONFIGURADO", "ENVIADO", "DEFECTUOSO"])
    with col2:
        filtro_tipo = st.selectbox("Filtrar por tipo:", ["TODOS", "DISPOSITIVO", "SD", "CABLE_USB", "CABLE_C", "CABLE_ETHERNET"])
    with col3:
        search_term = st.text_input("Buscar:", placeholder="REF, nombre...")
    
    inventario = obtener_todo_el_inventario()
    
    if inventario:
        df_inv = pd.DataFrame(inventario)
        
        if filtro_estado != "TODOS":
            df_inv = df_inv[df_inv['estado'] == filtro_estado]
        if filtro_tipo != "TODOS":
            df_inv = df_inv[df_inv['tipo'] == filtro_tipo]
        if search_term:
            mask = (df_inv['ref_prod'].astype(str).str.contains(search_term, case=False, na=False) |
                    df_inv['producto_nombre'].astype(str).str.contains(search_term, case=False, na=False))
            df_inv = df_inv[mask]
        
        # Función para colorear el estado
        def color_estado(val):
            colors = {
                'DISPONIBLE': 'color: #17a2b8',
                'EN PROCESO': 'color: #ffc107',
                'CONFIGURADO': 'color: #28a745',
                'ENVIADO': 'color: white',
                'DEFECTUOSO': 'color: #dc3545'
            }
            return colors.get(val, '')
        
        styled_df = df_inv.style.applymap(color_estado, subset=['estado'])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True, column_config={
            "id": "ID", 
            "ref_prod": "REF", 
            "producto_nombre": "Producto", 
            "tipo": "Tipo",
            "estado": "Estado", 
            "fecha_ingreso": "Fecha Ingreso",
            "disp_fecha_config_inicio": "Inicio Config",
            "disp_fecha_config_final": "Fin Config",
            "sd_fecha_config": "Fecha Config SD",
            "sd_config_final": "Config SD Final",
        })
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"Mostrando {len(df_inv)} items")
        with col2:
            disponibles = len(df_inv[df_inv['estado'] == 'DISPONIBLE'])
            st.success(f"{disponibles} disponibles")
        with col3:
            en_proceso = len(df_inv[df_inv['estado'] == 'EN PROCESO'])
            st.warning(f"{en_proceso} en configuración")
        with col4:
            configurados = len(df_inv[df_inv['estado'] == 'CONFIGURADO'])
            st.info(f"{configurados} configurados")

        # ---------- Editar / Eliminar Items ----------
        with st.expander("Editar o Eliminar Item"):
            if not inventario:
                st.info("No hay items en el inventario")
            else:
                ids_disponibles = df_inv['id'].tolist()
                if ids_disponibles:
                    selected_id = st.selectbox("Seleccionar ID del item:", ids_disponibles)
                    item_data = df_inv[df_inv['id'] == selected_id].iloc[0].to_dict()

                    # Verificar si el item está enviado
                    if item_data['estado'] == 'ENVIADO':
                        st.warning("Este item ya fue enviado y no puede ser modificado")
                    else:
                        with st.form("editar_item"):
                            st.write(f"**Editando item ID:** {selected_id}")
                            nuevo_estado = st.selectbox(
                                "Estado",
                                ["DISPONIBLE", "EN PROCESO", "CONFIGURADO", "DEFECTUOSO"],
                                index=["DISPONIBLE", "EN PRCESO", "CONFIGURADO", "DEFECTUOSO"].index(item_data['estado']) 
                                if item_data['estado'] in ["DISPONIBLE", "EN PROCESO", "CONFIGURADO", "DEFECTUOSO"] else 0
                            )

                            col1, col2 = st.columns(2)
                            with col1:
                                actualizar = st.form_submit_button("Actualizar")
                            with col2:
                                eliminar = st.form_submit_button("Eliminar")

                        if actualizar:
                            try:
                                actualizar_item_inventario(
                                    selected_id,
                                    estado=nuevo_estado,
                                )
                                st.success("Item actualizado correctamente")
                                st.cache_data.clear()
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                            except Exception as e:
                                st.error(f"Error al actualizar: {e}")

                        if eliminar:
                            if 'confirm_delete' not in st.session_state:
                                st.session_state.confirm_delete = False
                            
                            if not st.session_state.confirm_delete:
                                if st.button("Confirmar eliminación", key="confirm_btn"):
                                    st.session_state.confirm_delete = True
                                    st.rerun()
                            else:
                                st.warning("¿Estás seguro? Esta acción no se puede deshacer.")
                                col_si, col_no = st.columns(2)
                                with col_si:
                                    if st.button("Sí, eliminar", key="delete_yes"):
                                        try:
                                            eliminar_item_inventario(selected_id)
                                            st.success("Item eliminado")
                                            st.session_state.confirm_delete = False
                                            st.cache_data.clear()
                                            st.rerun()
                                        except ValueError as e:
                                            st.error(str(e))
                                            st.session_state.confirm_delete = False
                                        except Exception as e:
                                            st.error(f"Error al eliminar: {e}")
                                            st.session_state.confirm_delete = False
                                with col_no:
                                    if st.button("No, cancelar", key="delete_no"):
                                        st.session_state.confirm_delete = False
                                        st.rerun()
                else:
                    st.warning("No hay items en la vista filtrada")
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
            "id": "ID", 
            "folio": "Folio", 
            "fecha_salida": "Fecha Salida", 
            "destino": "Destino",
            "descripcion": "Descripción", 
            "total_items": "Items", 
            "created_at": "Registrado"
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
                    "producto_nombre": "Producto", 
                    "ref_prod": "REF", 
                    "tipo": "Tipo",
                    "sd_config_final": "Config SD",
                    "disp_config_final": "Config Dispositivo",
                    "estado": "Estado"
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
        st.dataframe(df_sds[['id', 'ref_prod', 'producto_nombre', 'fecha_ingreso']], use_container_width=True, hide_index=True, column_config={
            "id": "ID", 
            "ref_prod": "REF", 
            "producto_nombre": "SD", 
            "fecha_ingreso": "Fecha Ingreso"
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
            config_final = st.date_input("Fecha de configuracion final (obligatoria):", value=datetime.now().date())
        
        if st.button("Configurar SD", use_container_width=True, type="primary"):
            if not config_final:
                st.error("La fecha de configuración final es obligatoria")
            else:
                try:
                    configurar_sd(sd_seleccionada, config_final)
                    st.success("SD configurada exitosamente y marcada como configurada")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        st.warning("No hay SDs disponibles para configurar")

# ========== TAB 5: RECEPCION DE MERCANCIA ==========
with tab5:
    st.subheader("Agregar al Inventario")
    
    with st.expander("Crear nuevo producto", expanded=False):
        tipo = st.selectbox(
            "Tipo de producto:",
            ["DISPOSITIVO", "SD", "CABLE_USB", "CABLE_C", "CABLE_ETHERNET"],
            key="tipo_item"
        )
        
        with st.form("nuevo_item"):
            nombre = None
            descripcion = None
            
            if tipo == "DISPOSITIVO":
                nombre = st.text_input("Nombre del dispositivo:", placeholder="Ej: Dispositivo PRO")
                descripcion = st.text_area("Descripción (opcional):")
                st.info("La referencia se generará automáticamente según el tipo de producto.")
            else:
                descripcion = st.text_area("Descripción (opcional):")
                st.info("La referencia y el nombre se generarán automáticamente según el tipo de producto.")
            
            submitted = st.form_submit_button("Crear producto")
            
            if submitted:
                if tipo == "DISPOSITIVO" and not nombre:
                    st.error("El nombre es obligatorio para dispositivos.")
                else:
                    try:
                        nuevo_id = crear_producto(tipo, nombre, descripcion)
                        st.success(f"Producto creado con referencia autogenerada. Ahora puedes agregar stock.")
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
        with st.expander("Agregar stock al inventario", expanded=True):
            with st.form("agregar_inventario"):
                col1, col2 = st.columns(2)
                with col1:
                    producto_seleccionado = st.selectbox(
                        "Seleccionar producto:",
                        options=[p['id'] for p in productos],
                        format_func=lambda x: f"{next(p['ref_prod'] for p in productos if p['id']==x)} - {next(p['nombre'] for p in productos if p['id']==x)}"
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

# ========== TAB 6: CONFIGURAR DISPOSITIVOS ==========
with tab6:
    st.subheader("Configuración de Dispositivos")
    
    # Obtener dispositivos en diferentes estados
    todo_inventario = obtener_todo_el_inventario()
    dispositivos = [d for d in todo_inventario if d['tipo'] == 'DISPOSITIVO']
    
    if not dispositivos:
        st.warning("No hay dispositivos en el inventario")
    else:
        # Separar por estados
        disponibles = [d for d in dispositivos if d['estado'] == 'DISPONIBLE']
        en_configuracion = [d for d in dispositivos if d['estado'] == 'EN PROCESO']
        configurados = [d for d in dispositivos if d['estado'] == 'CONFIGURADO']
        enviados = [d for d in dispositivos if d['estado'] == 'ENVIADO']
        
        # Mostrar resumen
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"Disponibles: {len(disponibles)}")
        with col2:
            st.warning(f"En configuración: {len(en_configuracion)}")
        with col3:
            st.success(f"Configurados: {len(configurados)}")
        with col4:
            st.error(f"Enviados: {len(enviados)}")
        
        st.markdown("---")
        
        # Sección para iniciar configuración
        if disponibles:
            with st.expander("Iniciar Configuración de Dispositivo", expanded=False):
                st.markdown("### Iniciar Configuración de Dispositivo")
                st.markdown('<div class="info-box">Selecciona un dispositivo disponible para comenzar su configuración</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    dispositivo_inicio = st.selectbox(
                        "Dispositivo disponible:",
                        options=[d['id'] for d in disponibles],
                        format_func=lambda x: f"ID {x} - {next(d['ref_prod'] for d in disponibles if d['id']==x)} - {next(d['producto_nombre'] for d in disponibles if d['id']==x)}",
                        key="inicio_config"
                    )
                with col2:
                    fecha_inicio = st.date_input("Fecha de inicio de configuración:", value=datetime.now().date(), key="fecha_inicio")
                
                if st.button("Iniciar Configuración", use_container_width=True, type="primary"):
                    try:
                        iniciar_configuracion_dispositivo(dispositivo_inicio, fecha_inicio)
                        st.success("Configuración iniciada correctamente")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                
        st.markdown("---")
        
        # Sección para finalizar configuración
        if en_configuracion:
            st.markdown("### Finalizar Configuración de Dispositivo")
            st.markdown('<div class="info-box">Completa la configuración del dispositivo. La fecha final es obligatoria para poder enviarlo después.</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                dispositivo_fin = st.selectbox(
                    "Dispositivo en configuración:",
                    options=[d['id'] for d in en_configuracion],
                    format_func=lambda x: f"ID {x} - {next(d['ref_prod'] for d in en_configuracion if d['id']==x)} - Inicio: {next(d['disp_fecha_config_inicio'] for d in en_configuracion if d['id']==x)}",
                    key="fin_config"
                )
            with col2:
                fecha_fin = st.date_input("Fecha de finalización (obligatoria):", value=datetime.now().date(), key="fecha_fin")
            
            config_realizada = st.text_area("Configuración realizada (opcional):", placeholder="Detalles de la configuración aplicada...")
            
            if st.button("Finalizar Configuración", use_container_width=True, type="primary"):
                if not fecha_fin:
                    st.error("La fecha de finalización es obligatoria")
                else:
                    try:
                        finalizar_configuracion_dispositivo(dispositivo_fin, fecha_fin, config_realizada)
                        st.success("Configuración finalizada correctamente. Dispositivo marcado como CONFIGURADO")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
            
            st.markdown("---")
        
        # Tabla de dispositivos en configuración
        if en_configuracion:
            st.markdown("### Dispositivos en Proceso de Configuración")
            df_en_config = pd.DataFrame(en_configuracion)
            st.dataframe(df_en_config[['id', 'ref_prod', 'producto_nombre', 'disp_fecha_config_inicio']], 
                        use_container_width=True, hide_index=True,
                        column_config={
                            "id": "ID",
                            "ref_prod": "REF",
                            "producto_nombre": "Dispositivo",
                            "disp_fecha_config_inicio": "Inicio Config"
                        })
        
        # Tabla de dispositivos configurados
        if configurados:
            st.markdown("### Dispositivos Configurados")
            df_config = pd.DataFrame(configurados)
            st.dataframe(df_config[['id', 'ref_prod', 'producto_nombre', 'disp_fecha_config_inicio', 'disp_fecha_config_final']], 
                        use_container_width=True, hide_index=True,
                        column_config={
                            "id": "ID",
                            "ref_prod": "REF",
                            "producto_nombre": "Dispositivo",
                            "disp_fecha_config_inicio": "Inicio Config",
                            "disp_fecha_config_final": "Fin Config",
                        })