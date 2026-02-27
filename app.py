import streamlit as st
import pandas as pd
from db import *
from datetime import datetime
import time

# Constantes
TIPOS_CABLE = ["CABLE_USB", "CABLE_ETHERNET", "CABLE_C"]
TIPOS_ITEM = ["DISPOSITIVO", "SD"] + TIPOS_CABLE
MAX_FOLIO_LENGTH = 20
MAX_DESTINO_LENGTH = 80
MAX_DESCRIPCION_LENGTH = 250

st.set_page_config(
    page_title="Sistema de Inventario - Nubix",
    page_icon="🎱",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

# Inicializar session state
if 'carrito' not in st.session_state:
    st.session_state.carrito = []
if 'error_envio' not in st.session_state:
    st.session_state.error_envio = None
if 'modo_edicion' not in st.session_state:
    st.session_state.modo_edicion = False
if 'item_editando' not in st.session_state:
    st.session_state.item_editando = None

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
    .cart-item { padding: 0.5rem; border-bottom: 1px solid #444; }
    .stock-ajustado { font-size: 0.8rem; color: #888; }
    .disabled-input { opacity: 0.5; pointer-events: none; }
    .edit-mode-active { border-left: 4px solid #ff4b4b; padding-left: 1rem; }
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
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>Envíos realizados:</strong> <span>{metricas['total_envios']}</span></div>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>SDs configuradas:</strong> <span>{metricas.get('sds_configuradas', 0)}</span></div>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>Dispositivos configurados:</strong> <span>{metricas.get('dispositivos_configurados', 0)}</span></div>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>Dispositivos reiniciados:</strong> <span>{metricas.get('dispositivos_reiniciados', 0)}</span></div>
        <div style='display: flex; justify-content: space-between; margin: 8px 0;'><strong>Dispositivos defectuosos:</strong> <span>{metricas.get('dispositivos_defectuosos', 0)}</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown(f"<div style='text-align: center; padding: 10px 0;'><strong>Fecha de hoy:</strong> {datetime.now().strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)
    st.markdown("---")
    
    if st.button("Recargar Datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Inventario",
    "Agregar al inventario",
    "Historial de Envíos",
    "Configurar SD",
    "Dispositivos",
    "Realizar Envío"
])

# ========== FUNCIÓN HELPER PARA STOCK AJUSTADO ==========
def get_stock_ajustado(producto_id: int) -> int:
    """
    Calcula stock disponible restando lo que ya está en el carrito.
    Garantiza que nunca retorne negativo.
    """
    stock_total = len(obtener_items_para_envio(producto_id=producto_id))
    en_carrito = sum(item['cantidad'] for item in st.session_state.carrito if item['producto_id'] == producto_id)
    return max(0, stock_total - en_carrito)

# ========== FUNCIÓN PARA SALIR DEL MODO EDICIÓN ==========
def salir_modo_edicion():
    """Limpia el estado de edición"""
    st.session_state.modo_edicion = False
    st.session_state.item_editando = None

# ========== TAB 1: INVENTARIO ==========
with tab1:
    st.subheader("Inventario Físico")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        filtro_estado = st.selectbox("Filtrar por estado:", ["TODOS", "DISPONIBLE", "REINICIADO", "CONFIGURADO", "ENVIADO", "DEFECTUOSO"])
    with col2:
        filtro_tipo = st.selectbox("Filtrar por tipo:", ["TODOS"] + TIPOS_ITEM)
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
                'REINICIADO': 'color: #ffc107',
                'CONFIGURADO': 'color: #28a745',
                'ENVIADO': 'color: white',
                'DEFECTUOSO': 'color: #dc3545'
            }
            return colors.get(val, '')
        
        if not df_inv.empty:
            styled_df = df_inv.style.applymap(color_estado, subset=['estado'])
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True, column_config={
                "id": "ID",
                "estado": "ESTADO",
                "fecha_ingreso": "Fecha Ingreso",
                "fecha_defectuoso": "Fecha Defectuoso",
                "producto_nombre": "ITEM",   
                "ref_prod": "REF", 
                "tipo": "TIPO",
                "sd_config_final": "SD Fecha Config",
                "disp_fecha_config_inicio": "DISP Fecha Reinicio",
                "disp_fecha_config_final": "DISP Fecha Config",
                "disp_fecha_accion": "DISP Fecha Acción",
            })
            
            # ---------- Editar / Eliminar Items ----------
            with st.expander("Editar o Eliminar Item", expanded=False):
                if not inventario:
                    st.info("No hay items en el inventario")
                else:
                    items_filtrados = df_inv['id'].tolist() if not df_inv.empty else []
                    
                    if items_filtrados:
                        # Si estamos en modo edición, mostrar formulario
                        if st.session_state.modo_edicion and st.session_state.item_editando in items_filtrados:
                            selected_id = st.session_state.item_editando
                            item_data = df_inv[df_inv['id'] == selected_id].iloc[0].to_dict()
                            item_completo = obtener_item_completo(selected_id)
                            
                            st.markdown(f"### Editando: {item_data['ref_prod']} - {item_data['producto_nombre']}")
                            st.caption(f"Tipo: {item_data['tipo']} | Estado actual: **{item_data['estado']}**")
                            
                            if item_data['estado'] == 'ENVIADO':
                                st.warning("⚠️ Este item ya fue enviado y no puede ser modificado")
                                if st.button("Volver", key="volver_enviado"):
                                    salir_modo_edicion()
                                    st.rerun()
                            else:
                                with st.form("form_editar_item"):
                                    st.markdown("#### Datos del Inventario")
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        nuevo_estado = st.selectbox(
                                            "Estado",
                                            ["DISPONIBLE", "REINICIADO", "CONFIGURADO", "DEFECTUOSO"],
                                            index=["DISPONIBLE", "REINICIADO", "CONFIGURADO", "DEFECTUOSO"].index(item_data['estado']) 
                                            if item_data['estado'] in ["DISPONIBLE", "REINICIADO", "CONFIGURADO", "DEFECTUOSO"] else 0,
                                            help="Cambiar el estado del item"
                                        )
                                    
                                    with col2:
                                        fecha_ingreso_val = item_data['fecha_ingreso']
                                        if isinstance(fecha_ingreso_val, str):
                                            fecha_ingreso_val = datetime.strptime(fecha_ingreso_val, "%Y-%m-%d").date()
                                        
                                        nueva_fecha_ingreso = st.date_input(
                                            "Fecha de ingreso",
                                            value=fecha_ingreso_val,
                                            max_value=datetime.now().date(),
                                            help="No puede ser una fecha futura"
                                        )
                                    
                                    st.markdown("---")
                                    
                                    # Campos específicos según tipo
                                    if item_data['tipo'] == 'SD' and item_completo:
                                        st.markdown("#### Configuración de SD")
                                        
                                        sd_fecha_val = item_completo.get('sd_config_final')
                                        if sd_fecha_val and isinstance(sd_fecha_val, str):
                                            sd_fecha_val = datetime.strptime(sd_fecha_val, "%Y-%m-%d").date()
                                        
                                        sd_config_final = st.date_input(
                                            "Fecha de configuración final",
                                            value=sd_fecha_val if sd_fecha_val else None,
                                            max_value=datetime.now().date(),
                                            help="Fecha en que se quemó la imagen en la SD"
                                        )
                                    else:
                                        sd_config_final = None
                                    
                                    if item_data['tipo'] == 'DISPOSITIVO' and item_completo:
                                        st.markdown("#### Configuración de Dispositivo")
                                        
                                        col_d1, col_d2 = st.columns(2)
                                        
                                        with col_d1:
                                            fecha_inicio_val = item_completo.get('disp_fecha_config_inicio')
                                            if fecha_inicio_val and isinstance(fecha_inicio_val, str):
                                                fecha_inicio_val = datetime.strptime(fecha_inicio_val, "%Y-%m-%d").date()
                                            
                                            disp_fecha_inicio = st.date_input(
                                                "Fecha de inicio (reinicio)",
                                                value=fecha_inicio_val if fecha_inicio_val else None,
                                                max_value=datetime.now().date(),
                                                help="Fecha en que se reinició el dispositivo"
                                            )
                                        
                                        with col_d2:
                                            fecha_fin_val = item_completo.get('disp_fecha_config_final')
                                            if fecha_fin_val and isinstance(fecha_fin_val, str):
                                                fecha_fin_val = datetime.strptime(fecha_fin_val, "%Y-%m-%d").date()
                                            
                                            disp_fecha_fin = st.date_input(
                                                "Fecha de finalización",
                                                value=fecha_fin_val if fecha_fin_val else None,
                                                max_value=datetime.now().date(),
                                                help="Fecha en que se completó la configuración"
                                            )
                                        
                                        # Validación visual
                                        if disp_fecha_inicio and disp_fecha_fin:
                                            if disp_fecha_inicio > disp_fecha_fin:
                                                st.error("❌ La fecha de inicio no puede ser posterior a la fecha final")
                                    else:
                                        disp_fecha_inicio = None
                                        disp_fecha_fin = None
                                    
                                    st.markdown("---")
                                    
                                    # Botones de acción
                                    col_b1, col_b2, col_b3 = st.columns([2, 2, 2])
                                    
                                    with col_b1:
                                        guardar = st.form_submit_button("Guardar cambios", use_container_width=True, type="primary")
                                    
                                    with col_b2:
                                        marcar_defectuoso = st.form_submit_button("Marcar como Defectuoso", use_container_width=True)
                                    
                                    with col_b3:
                                        cancelar = st.form_submit_button("Cancelar", use_container_width=True)
                                
                                # Procesar acciones del formulario
                                if guardar:
                                    try:
                                        if item_data['tipo'] == 'DISPOSITIVO' and disp_fecha_inicio and disp_fecha_fin:
                                            if disp_fecha_inicio > disp_fecha_fin:
                                                st.error("❌ La fecha de inicio no puede ser posterior a la fecha final")
                                                st.stop()
                                        
                                        actualizar_item(
                                            item_id=selected_id,
                                            estado=nuevo_estado,
                                            fecha_ingreso=nueva_fecha_ingreso,
                                            sd_config_final=sd_config_final,
                                            disp_fecha_config_inicio=disp_fecha_inicio,
                                            disp_fecha_config_final=disp_fecha_fin
                                        )
                                        
                                        st.success("✅ Item actualizado correctamente")
                                        salir_modo_edicion()
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                        
                                    except ValueError as e:
                                        st.error(f"❌ {str(e)}")
                                    except Exception as e:
                                        st.error(f"❌ Error inesperado: {str(e)}")
                                
                                if marcar_defectuoso:
                                    try:
                                        marcar_como_defectuoso(selected_id)
                                        st.success("✅ Item marcado como defectuoso")
                                        salir_modo_edicion()
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                    except ValueError as e:
                                        st.error(f"❌ {str(e)}")
                                    except Exception as e:
                                        st.error(f"❌ Error inesperado: {str(e)}")
                                
                                if cancelar:
                                    salir_modo_edicion()
                                    st.rerun()
                        
                        else:
                            # Modo selección (no estamos editando)
                            col_select, col_action = st.columns([3, 1])
                            
                            with col_select:
                                selected_id = st.selectbox(
                                    "Seleccionar item a editar:", 
                                    options=items_filtrados,
                                    format_func=lambda x: f"ID {x} - {df_inv[df_inv['id']==x]['ref_prod'].iloc[0]} - {df_inv[df_inv['id']==x]['producto_nombre'].iloc[0]}"
                                )
                            
                            with col_action:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("Editar", use_container_width=True, key="btn_editar"):
                                    st.session_state.modo_edicion = True
                                    st.session_state.item_editando = selected_id
                                    st.rerun()
                            
                            # Sección de eliminación (separada)
                            st.markdown("---")
                            st.markdown("#### Eliminar Item")
                            st.warning("⚠️ Esta acción no se puede deshacer")
                            
                            col_del1, col_del2, col_del3 = st.columns([2, 1, 2])
                            
                            with col_del1:
                                item_a_eliminar = st.selectbox(
                                    "Seleccionar item a eliminar:",
                                    options=items_filtrados,
                                    format_func=lambda x: f"ID {x} - {df_inv[df_inv['id']==x]['ref_prod'].iloc[0]}",
                                    key="select_eliminar"
                                )
                            
                            with col_del2:
                                st.markdown("<br>", unsafe_allow_html=True)
                                if st.button("Eliminar", key="btn_eliminar", type="secondary"):
                                    st.session_state['confirmar_eliminacion'] = item_a_eliminar
                                    st.rerun()
                            
                            # Confirmación de eliminación
                            if 'confirmar_eliminacion' in st.session_state:
                                item_id_confirm = st.session_state['confirmar_eliminacion']
                                item_info = df_inv[df_inv['id'] == item_id_confirm].iloc[0]
                                
                                st.error(f"### ¿Eliminar permanentemente?")
                                st.warning(f"**Item:** {item_info['ref_prod']} - {item_info['producto_nombre']}")
                                st.warning(f"**Estado:** {item_info['estado']}")
                                
                                col_conf1, col_conf2, col_conf3 = st.columns([1, 1, 2])
                                
                                with col_conf1:
                                    if st.button("✅ Sí, eliminar", key="confirm_si", type="primary"):
                                        try:
                                            eliminar_item_inventario(item_id_confirm)
                                            st.success("✅ Item eliminado permanentemente")
                                            del st.session_state['confirmar_eliminacion']
                                            st.cache_data.clear()
                                            time.sleep(1)
                                            st.rerun()
                                        except ValueError as e:
                                            st.error(f"❌ {str(e)}")
                                            del st.session_state['confirmar_eliminacion']
                                            time.sleep(2)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ Error inesperado: {str(e)}")
                                            del st.session_state['confirmar_eliminacion']
                                
                                with col_conf2:
                                    if st.button("❌ No, cancelar", key="confirm_no"):
                                        del st.session_state['confirmar_eliminacion']
                                        st.rerun()
                    else:
                        st.warning("No hay items en la vista filtrada para editar")

# ========== TAB 2: AGREGAR AL INVENTARIO ==========
with tab2:
    st.subheader("Agregar al Inventario")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("Crear nuevo item", expanded=True):
            tipo = st.selectbox("Tipo de item:", TIPOS_ITEM, key="tipo_item")
            
            with st.form("nuevo_item"):
                nombre = None
                if tipo == "DISPOSITIVO":
                    nombre = st.text_input("Nombre del dispositivo:", placeholder="Ej: Dispositivo PRO", max_chars=100)
                    st.info("La referencia se generará automáticamente.")
                else:
                    st.info("La referencia y el nombre se generarán automáticamente.")
                
                submitted = st.form_submit_button("Crear item", use_container_width=True, type="primary")
                
                if submitted:
                    if tipo == "DISPOSITIVO" and not nombre:
                        st.error("El nombre es obligatorio para dispositivos.")
                    else:
                        try:
                            nuevo_id = crear_producto(tipo, nombre)
                            st.success(f"✅ Producto creado con referencia autogenerada.")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except ValueError as e:
                            st.error(f"❌ {str(e)}")
        
    with col2:
        items = get_productos()
        if not items:
            st.info("No hay items en el inventario")
        else:
            with st.expander("Agregar stock al inventario", expanded=True):
                with st.form("agregar_inventario"):
                    item_seleccionado = st.selectbox(
                            "Seleccionar item:",
                            options=[p['id'] for p in items],
                            format_func=lambda x: f"{next(p['ref_prod'] for p in items if p['id']==x)} - {next(p['nombre'] for p in items if p['id']==x)}"
                        )
                    cantidad = st.number_input("Cantidad a ingresar:", min_value=1, max_value=100, value=1)
                    fecha_ingreso = st.date_input("Fecha de ingreso:", value=datetime.now().date(), max_value=datetime.now().date())
                    
                    if st.form_submit_button("Registrar en Inventario", use_container_width=True, type="primary"):
                        try:
                            ids = agregar_item_a_inventario(item_seleccionado, cantidad, fecha_ingreso)
                            st.success(f"✅ {cantidad} unidad(es) agregada(s) al inventario")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except ValueError as e:
                            st.error(f"❌ {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

# ========== TAB 6: REALIZAR ENVÍO ==========
with tab6:
    st.subheader("Realizar Nuevo Envío")
    
    # Mostrar error pendiente si existe
    if st.session_state.error_envio:
        with st.container():
            st.error(f"❌ Error en el envío anterior: {st.session_state.error_envio}")
            if st.button("Limpiar error y reintentar", use_container_width=True):
                st.session_state.error_envio = None
                st.rerun()
    
    productos = get_productos()
    if not productos:
        st.warning("No hay productos en el catálogo. Ve a 'Agregar al inventario' para crear items.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            producto_opciones = {f"{p['ref_prod']} - {p['nombre']}": p['id'] for p in productos}
            producto_seleccionado = st.selectbox("Seleccionar producto:", options=list(producto_opciones.keys()), key="prod_select")
            producto_id = producto_opciones[producto_seleccionado]
            
            stock_ajustado = get_stock_ajustado(producto_id)
            stock_total = len(obtener_items_para_envio(producto_id=producto_id))
            
            st.caption(f"Stock disponible: {stock_total} | En carrito: {stock_total - stock_ajustado} | Puede agregar: {stock_ajustado}")
            
            # Solo mostrar input de cantidad si hay stock disponible
            if stock_ajustado > 0:
                cantidad = st.number_input(
                    "Cantidad:", 
                    min_value=1, 
                    max_value=stock_ajustado,
                    value=1,
                    step=1
                )
                
                if st.button("Agregar al envío", use_container_width=True):
                    existing = next((item for item in st.session_state.carrito if item['producto_id'] == producto_id), None)
                    nombre = next(p['nombre'] for p in productos if p['id'] == producto_id)
                    
                    if existing:
                        existing['cantidad'] += cantidad
                    else:
                        st.session_state.carrito.append({
                            'producto_id': producto_id,
                            'nombre': nombre,
                            'cantidad': cantidad,
                            'ref': next(p['ref_prod'] for p in productos if p['id'] == producto_id)
                        })
                    st.success(f"✅ Agregado {cantidad} x {nombre}")
                    st.rerun()
            else:
                st.info("No hay stock disponible de este producto")
                st.number_input("Cantidad:", value=0, disabled=True, key="cantidad_disabled")
        
        with col2:
            st.markdown("##### Carrito actual")
            if st.session_state.carrito:
                total_items = sum(item['cantidad'] for item in st.session_state.carrito)
                st.markdown(f"**Total productos: {total_items}**")
                
                for i, item in enumerate(st.session_state.carrito):
                    with st.container():
                        col_a, col_b, col_c = st.columns([2, 1, 1])
                        with col_a:
                            st.write(f"**{item['ref']}**")
                            st.caption(f"{item['nombre']}")
                        with col_b:
                            st.write(f"x{item['cantidad']}")
                        with col_c:
                            if st.button("🗑️", key=f"del_{i}"):
                                st.session_state.carrito.pop(i)
                                st.rerun()
                        st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
                
                if st.button("Vaciar carrito", use_container_width=True):
                    st.session_state.carrito = []
                    st.rerun()
            else:
                st.info("Carrito vacío")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            folio = st.text_input("Número de Folio:", placeholder="Ej: NBX-2024-001", max_chars=MAX_FOLIO_LENGTH)
        with col2:
            destino = st.text_input("Destino (opcional):", placeholder="Cliente o ubicación", max_chars=MAX_DESTINO_LENGTH)
        
        descripcion = st.text_area("Descripción del envío (opcional):", placeholder="Notas adicionales...", max_chars=MAX_DESCRIPCION_LENGTH)
        
        if st.button("Procesar Envío", use_container_width=True, type="primary"):
            if not folio or not folio.strip():
                st.error("❌ El número de folio es obligatorio.")
            elif not st.session_state.carrito:
                st.error("❌ El carrito está vacío")
            else:
                try:
                    with st.spinner("Procesando envío..."):
                        items_envio = [
                            {'producto_id': item['producto_id'], 'cantidad': item['cantidad']} 
                            for item in st.session_state.carrito
                        ]
                        resultado = procesar_envio(items_envio, folio.strip(), destino, descripcion)
                    
                    st.success(f"""
                    **✅ Envío procesado exitosamente**
                    - Folio: {resultado['folio']}
                    - ID de envío: {resultado['envio_id']}
                    - Items enviados: {resultado['items_procesados']}
                    """)
                    st.balloons()
                    st.session_state.carrito = []
                    st.session_state.error_envio = None
                    st.cache_data.clear()
                    time.sleep(2)
                    st.rerun()
                    
                except ValueError as e:
                    st.session_state.error_envio = str(e)
                    st.error(f"❌ Error: {str(e)}")
                except Exception as e:
                    st.session_state.error_envio = f"Error inesperado: {str(e)}"
                    st.error(f"❌ Error inesperado: {str(e)}")

# ========== TAB 3: HISTORIAL DE ENVÍOS ==========
with tab3:
    st.subheader("Historial de Envíos")
    
    envios = get_envios()
    
    if envios:
        df_envios = pd.DataFrame(envios)
        
        search_folio = st.text_input("Buscar por folio:", key="search_envios")
        if search_folio:
            mask = df_envios['folio'].astype(str).str.contains(search_folio, case=False, na=False)
            df_envios = df_envios[mask]
        
        if not df_envios.empty:
            st.dataframe(df_envios, use_container_width=True, hide_index=True, column_config={
                "id": "ID", 
                "folio": "FOLIO", 
                "fecha_salida": "FECHA SALIDA", 
                "destino": "DESTINO", 
                "total_items": "TOTAL ITEMS", 
                "created_at": "FECHA REGISTRO"
            })
            
            st.markdown("---")
            st.subheader("Ver Detalle de Envío")
            
            selected_envio = st.selectbox(
                "Seleccionar envío:",
                options=df_envios['id'].tolist(),
                format_func=lambda x: f"Folio: {df_envios[df_envios['id']==x]['folio'].iloc[0]}"
            )
            
            if selected_envio:
                detalle = get_detalle_envio(selected_envio)
                if detalle:
                    st.markdown("##### Items enviados:")
                    df_detalle = pd.DataFrame(detalle)
                    st.dataframe(df_detalle, use_container_width=True, hide_index=True)
        else:
            st.info("No hay envíos que coincidan con la búsqueda")
    else:
        st.info("No hay envíos registrados")

# ========== TAB 4: CONFIGURAR SD ==========
with tab4:
    st.subheader("Configurar Tarjetas SD")
    
    sds_disponibles = obtener_sds_para_configurar()
    
    if sds_disponibles:
        st.markdown("##### SDs disponibles para configurar:")
        df_sds = pd.DataFrame(sds_disponibles)
        st.dataframe(df_sds[['id', 'ref_prod', 'producto_nombre', 'fecha_ingreso']], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        with st.expander("Configurar SD", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                sd_seleccionada = st.selectbox(
                    "Seleccionar SD a configurar:",
                    options=[s['id'] for s in sds_disponibles],
                    format_func=lambda x: f"ID {x} - {next(s['producto_nombre'] for s in sds_disponibles if s['id']==x)}"
                )
            with col2:
                config_final = st.date_input("Fecha de configuración final:", value=datetime.now().date(), max_value=datetime.now().date())
            
            if st.button("Configurar SD", use_container_width=True, type="primary"):
                if not config_final:
                    st.error("❌ La fecha de configuración es obligatoria")
                else:
                    try:
                        configurar_sd(sd_seleccionada, config_final)
                        st.success("✅ SD configurada exitosamente")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    except ValueError as e:
                        st.error(f"❌ {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    else:
        st.warning("No hay SDs disponibles para configurar")

# ========== TAB 5: DISPOSITIVOS ==========
with tab5:
    st.subheader("Dispositivos")
    
    todo_inventario = obtener_todo_el_inventario()
    dispositivos = [d for d in todo_inventario if d['tipo'] == 'DISPOSITIVO']
    
    if not dispositivos:
        st.warning("No hay dispositivos en el inventario")
    else:
        # Separar por estados
        disponibles = [d for d in dispositivos if d['estado'] == 'DISPONIBLE']
        reiniciado = [d for d in dispositivos if d['estado'] == 'REINICIADO']
        configurados = [d for d in dispositivos if d['estado'] == 'CONFIGURADO']
        defectuosos = [d for d in dispositivos if d['estado'] == 'DEFECTUOSO']
        
        # Mostrar resumen
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.info(f"Disponibles: {len(disponibles)}")
        with col2:
            st.warning(f"Reiniciados: {len(reiniciado)}")
        with col3:
            st.success(f"Configurados: {len(configurados)}")
        with col4:
            st.error(f"Defectuosos: {len(defectuosos)}")
        
        st.markdown("---")
        
        # Sección de reinicio
        col1, col2 = st.columns(2)
        with col1:
            dispositivos_para_reiniciar = obtener_dispositivos_para_reiniciar()
            
            if dispositivos_para_reiniciar:
                with st.expander("Reinicio de Dispositivo", expanded=True):
                    st.markdown("### Iniciar Reinicio de Dispositivo")
                    
                    col_left, col_right = st.columns(2)
                    with col_left:
                        dispositivo_inicio = st.selectbox(
                            "Dispositivo disponible:",
                            options=[d['id'] for d in dispositivos_para_reiniciar],
                            format_func=lambda x: f"ID {x} - {next(d['producto_nombre'] for d in dispositivos_para_reiniciar if d['id']==x)}",
                            key="inicio_config"
                        )
                    with col_right:
                        fecha_reinicio = st.date_input("Fecha de reinicio:", value=datetime.now().date(), max_value=datetime.now().date(), key="fecha_reinicio")
                    
                    if st.button("Reiniciar Dispositivo", use_container_width=True, type="primary"):
                        try:
                            iniciar_configuracion_dispositivo(dispositivo_inicio, fecha_reinicio)
                            st.success("✅ Dispositivo reiniciado correctamente")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except ValueError as e:
                            st.error(f"❌ {str(e)}")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
            else:
                st.info("No hay dispositivos disponibles para reiniciar")
        
        # Sección para configuración
        with col2:
            dispositivos_reiniciados = obtener_dispositivos_reiniciados()
            
            if dispositivos_reiniciados:
                with st.expander("Configurar Dispositivo Reiniciado", expanded=True):
                    st.markdown("### Finalizar Configuración")
                    
                    # Crear opciones con texto seguro
                    opciones_config = {
                        d['id']: f"ID {d['id']} - {d['producto_nombre']} (Reiniciado: {d['fecha_config_inicio']})"
                        for d in dispositivos_reiniciados
                    }
                    
                    col_left, col_right = st.columns(2)
                    with col_left:
                        dispositivo_fin = st.selectbox(
                            "Dispositivo reiniciado:",
                            options=list(opciones_config.keys()),
                            format_func=lambda x: opciones_config[x],
                            key="fin_config"
                        )
                    with col_right:
                        fecha_fin = st.date_input("Fecha de configuración:", value=datetime.now().date(), max_value=datetime.now().date(), key="fecha_fin")
                    
                    if st.button("Finalizar Configuración", use_container_width=True, type="primary"):
                        if not fecha_fin:
                            st.error("❌ La fecha de finalización es obligatoria")
                        else:
                            try:
                                finalizar_configuracion_dispositivo(dispositivo_fin, fecha_fin)
                                st.success("✅ Configuración finalizada. Dispositivo marcado como CONFIGURADO")
                                st.cache_data.clear()
                                time.sleep(1)
                                st.rerun()
                            except ValueError as e:
                                st.error(f"❌ {str(e)}")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
            else:
                st.info("No hay dispositivos reiniciados para configurar")
        
        st.markdown("---")
        
        # Tabla de dispositivos reiniciados
        if reiniciado:
            st.markdown("### Dispositivos Reiniciados")
            dv_reiniciado = pd.DataFrame(reiniciado)
            if not dv_reiniciado.empty:
                st.dataframe(dv_reiniciado[['id', 'ref_prod', 'producto_nombre', 'disp_fecha_config_inicio']], 
                            use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Tabla de dispositivos configurados
        if configurados:
            st.markdown("### Dispositivos Configurados")
            df_config = pd.DataFrame(configurados)
            if not df_config.empty:
                st.dataframe(df_config[['id', 'ref_prod', 'producto_nombre', 'disp_fecha_config_inicio', 'disp_fecha_config_final', 'disp_fecha_accion']], 
                            use_container_width=True, hide_index=True)

st.markdown("---")