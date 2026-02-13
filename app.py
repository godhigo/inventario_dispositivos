import streamlit as st
import pandas as pd
from db import *
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Inventario",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar base de datos
init_db()

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">Sistema de Gestión de Inventario</h1>', unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    st.image("https://i2.wp.com/nubix.cloud/wp-content/uploads/2020/08/TRANSPARENTE_NUBIX-COLOR.png?fit=1506%2C1236&ssl=1", use_container_width=True)
    st.markdown("---")
    
    # Métricas rápidas
    metricas = get_metricas()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Disp. Enviados", metricas['total_dispositivos'])
        st.metric("SDs Enviadas", metricas['total_sds'])
    with col2:
        st.metric("Disp. Stock", metricas['total_stock'])
        st.metric("SDs Stock", metricas['total_sds_stock'])
    
    st.markdown("---")
    st.markdown("### Fecha")
    st.write(datetime.now().strftime("%d/%m/%Y"))
    
    # Botón de recarga manual
    if st.button("Recargar Datos"):
        st.cache_data.clear()
        st.rerun()

# ========== TABS PRINCIPALES ==========
tab1, tab2, tab3, tab4 = st.tabs([
    "Dispositivos Enviados", 
    "Stock Dispositivos",
    "SDs Enviadas",
    "Stock SDs"
])

# ========== TAB 1: DISPOSITIVOS ENVIADOS ==========
with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Lista de Dispositivos Enviados")
    
    with col2:
        search_term = st.text_input("Buscar por folio o versión", key="search_disp")
    
    # Obtener datos
    dispositivos = get_dispositivos()
    
    if dispositivos:
        df_disp = pd.DataFrame(dispositivos)
        
        if search_term:
            mask = (
                df_disp['folio'].astype(str).str.contains(search_term, case=False, na=False) |
                df_disp['version'].astype(str).str.contains(search_term, case=False, na=False)
            )
            df_disp = df_disp[mask]
        
        st.dataframe(
            df_disp,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": "ID",
                "version": "Versión",
                "cables": "Cables",
                "tipo_cable": "Tipo Cable",
                "ethernet": "Ethernet",
                "config_final": "Config Final",
                "fecha_salida": "Fecha Salida",
                "folio": "Folio",
                "created_at": "Creado"
            }
        )
        
        if not df_disp.empty:
            selected_id = st.selectbox(
                "Seleccionar dispositivo para editar/eliminar",
                options=df_disp['id'].tolist(),
                format_func=lambda x: f"ID {x} - {df_disp[df_disp['id']==x]['version'].iloc[0]} - Folio: {df_disp[df_disp['id']==x]['folio'].iloc[0]}",
                key="select_disp"
            )
            
            if selected_id:
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("Editar", use_container_width=True, key="edit_disp_btn"):
                        st.session_state['edit_disp'] = selected_id
                
                with col2:
                    if st.button("Eliminar", use_container_width=True, key="delete_disp_btn"):
                        if st.session_state.get('confirm_delete_disp') == selected_id:
                            delete_dispositivo(selected_id)
                            st.success("Dispositivo eliminado")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.session_state['confirm_delete_disp'] = selected_id
                            st.warning("Presiona nuevamente para confirmar")
    else:
        st.info("No hay dispositivos registrados")
    
    # ----- FORMULARIO DE AGREGAR (CORREGIDO) -----
    with st.expander("Agregar Nuevo Dispositivo", expanded=False):
        # Checkboxes fuera del formulario para controlar visibilidad
        col1, col2 = st.columns(2)
        with col1:
            agregar_config = st.checkbox("Agregar fecha de configuración final", key="agregar_config")
        with col2:
            agregar_fecha = st.checkbox("Agregar fecha de salida", key="agregar_fecha")
        
        # Formulario
        with st.form("form_disp"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"])
                cables = st.selectbox("¿Tiene cables?", ["No", "Si"])
            
            with col2:
                if cables == "Si":
                    tipo_cable = st.selectbox("Tipo de Cable", ["Tipo C", "USB"])
                    ethernet = st.selectbox("¿Ethernet?", ["No", "Si"])
                else:
                    tipo_cable = None
                    ethernet = None
                    st.write("---")
            
            with col3:
                # Campos condicionales basados en los checkboxes
                config_final = st.date_input("Configuración final") if agregar_config else None
                
                if agregar_fecha:
                    fecha_salida = st.date_input("Fecha de salida")
                    folio = st.text_input("Folio")
                else:
                    fecha_salida = None
                    folio = None
            
            submitted = st.form_submit_button("Guardar Dispositivo", use_container_width=True)
            
            if submitted:
                insert_dispositivo((
                    version, cables, tipo_cable, ethernet,
                    format_fecha(config_final),
                    format_fecha(fecha_salida),
                    folio
                ))
                st.success("Dispositivo agregado exitosamente")
                st.cache_data.clear()
                st.rerun()
    
    # Formulario de edición (sin cambios, ya que la lógica es diferente)
    if st.session_state.get('edit_disp'):
        st.markdown("---")
        st.subheader(f"Editando Dispositivo ID: {st.session_state['edit_disp']}")
        actual = next((d for d in dispositivos if d['id'] == st.session_state['edit_disp']), None)
        if actual:
            with st.form("form_edit_disp"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"],
                                           index=["Normal", "Pro", "Max", "AMIcalidad"].index(actual['version']))
                    cables = st.selectbox("¿Cables?", ["No", "Si"],
                                          index=1 if actual['cables'] == "Si" else 0)
                with col2:
                    if cables == "Si":
                        tipo_cable = st.selectbox("Tipo cable", ["Tipo C", "USB"],
                                                  index=0 if actual.get('tipo_cable') == "Tipo C" else 1 if actual.get('tipo_cable') == "USB" else 0)
                        ethernet = st.selectbox("Ethernet", ["No", "Si"],
                                                index=1 if actual.get('ethernet') == "Si" else 0)
                    else:
                        tipo_cable = None
                        ethernet = None
                        st.write("---")
                with col3:
                    if st.checkbox("Editar config final", value=bool(actual.get('config_final'))):
                        config_final = st.date_input("Config final",
                                                     value=parse_fecha(actual.get('config_final')) if actual.get('config_final') else datetime.now().date())
                    else:
                        config_final = None
                    
                    if st.checkbox("Editar fecha salida", value=bool(actual.get('fecha_salida'))):
                        fecha_salida = st.date_input("Fecha salida",
                                                     value=parse_fecha(actual.get('fecha_salida')) if actual.get('fecha_salida') else datetime.now().date())
                        folio = st.text_input("Folio", actual.get('folio', ''))
                    else:
                        fecha_salida = None
                        folio = None
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Actualizar", use_container_width=True):
                        update_dispositivo(st.session_state['edit_disp'],
                                           (version, cables, tipo_cable, ethernet,
                                            format_fecha(config_final),
                                            format_fecha(fecha_salida),
                                            folio))
                        st.success("Dispositivo actualizado")
                        st.session_state['edit_disp'] = None
                        st.cache_data.clear()
                        st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state['edit_disp'] = None
                        st.rerun()

# ========== TAB 2: STOCK DISPOSITIVOS ==========
with tab2:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Stock de Dispositivos")
    with col2:
        search_term = st.text_input("Buscar", key="search_stock")
    
    stock = get_dispositivos_stock()
    if stock:
        df_stock = pd.DataFrame(stock)
        if search_term:
            mask = df_stock['version'].astype(str).str.contains(search_term, case=False, na=False)
            df_stock = df_stock[mask]
        st.dataframe(df_stock, use_container_width=True, hide_index=True,
                     column_config={"id": "ID", "version": "Versión", "cables": "Cables",
                                    "sd": "SD", "reiniciado": "Reiniciado",
                                    "fecha_reinicio": "Fecha Reinicio", "fecha_llegada": "Fecha Llegada"})
        if not df_stock.empty:
            selected_stock_id = st.selectbox("Seleccionar item para gestionar",
                                             options=df_stock['id'].tolist(),
                                             format_func=lambda x: f"ID {x} - {df_stock[df_stock['id']==x]['version'].iloc[0]}",
                                             key="select_stock")
            if selected_stock_id:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Editar", key="edit_stock_btn"):
                        st.session_state['edit_stock'] = selected_stock_id
                with col2:
                    if st.button("Eliminar", key="delete_stock_btn"):
                        if st.session_state.get('confirm_delete_stock') == selected_stock_id:
                            delete_dispositivo_stock(selected_stock_id)
                            st.success("Item eliminado del stock")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.session_state['confirm_delete_stock'] = selected_stock_id
                            st.warning("Presiona nuevamente para confirmar")
    else:
        st.info("No hay dispositivos en stock")
    
    # Formulario de agregar a stock (sin cambios, pero note que aquí no hay checkboxes problemáticos)
    with st.expander("Agregar a Stock", expanded=False):
        with st.form("form_stock"):
            col1, col2, col3 = st.columns(3)
            with col1:
                version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"], key="stock_v")
                cables = st.selectbox("Cables", ["No", "Si"], key="stock_c")
            with col2:
                sd = st.selectbox("SD", ["No", "Si"], key="stock_sd")
                reiniciado = st.selectbox("Reiniciado", ["No", "Si"], key="stock_r")
            with col3:
                if reiniciado == "Si":
                    fecha_reinicio = st.date_input("Fecha reinicio", key="stock_fr")
                else:
                    fecha_reinicio = None
                agregar_llegada = st.checkbox("Agregar fecha llegada", key="stock_chk")
                fecha_llegada = st.date_input("Fecha llegada", key="stock_fl") if agregar_llegada else None
            if st.form_submit_button("Guardar en Stock", use_container_width=True):
                insert_dispositivo_stock((version, cables, sd, reiniciado,
                                          format_fecha(fecha_reinicio),
                                          format_fecha(fecha_llegada)))
                st.success("Agregado al stock exitosamente")
                st.cache_data.clear()
                st.rerun()
    
    # Formulario de edición de stock (sin cambios)
    if st.session_state.get('edit_stock'):
        st.markdown("---")
        st.subheader(f"Editando Stock ID: {st.session_state['edit_stock']}")
        actual = next((s for s in stock if s['id'] == st.session_state['edit_stock']), None)
        if actual:
            with st.form("form_edit_stock"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"],
                                           index=["Normal", "Pro", "Max", "AMIcalidad"].index(actual['version']))
                    cables = st.selectbox("Cables", ["No", "Si"],
                                          index=1 if actual['cables'] == "Si" else 0)
                with col2:
                    sd = st.selectbox("SD", ["No", "Si"],
                                      index=1 if actual['sd'] == "Si" else 0)
                    reiniciado = st.selectbox("Reiniciado", ["No", "Si"],
                                              index=1 if actual['reiniciado'] == "Si" else 0)
                with col3:
                    if reiniciado == "Si":
                        fecha_reinicio = st.date_input("Fecha reinicio",
                                                       value=parse_fecha(actual.get('fecha_reinicio')) if actual.get('fecha_reinicio') else datetime.now().date())
                    else:
                        fecha_reinicio = None
                    if st.checkbox("Editar fecha llegada", value=bool(actual.get('fecha_llegada'))):
                        fecha_llegada = st.date_input("Fecha llegada",
                                                      value=parse_fecha(actual.get('fecha_llegada')) if actual.get('fecha_llegada') else datetime.now().date())
                    else:
                        fecha_llegada = None
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Actualizar Stock", use_container_width=True):
                        update_dispositivo_stock(st.session_state['edit_stock'],
                                                 (version, cables, sd, reiniciado,
                                                  format_fecha(fecha_reinicio),
                                                  format_fecha(fecha_llegada)))
                        st.success("Stock actualizado")
                        st.session_state['edit_stock'] = None
                        st.cache_data.clear()
                        st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state['edit_stock'] = None
                        st.rerun()

# ========== TAB 3: SDS ENVIADAS ==========
with tab3:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("SDs Enviadas")
    with col2:
        search_term = st.text_input("Buscar por folio", key="search_sds")
    
    sds = get_sds()
    if sds:
        df_sds = pd.DataFrame(sds)
        if search_term:
            mask = df_sds['folio'].astype(str).str.contains(search_term, case=False, na=False)
            df_sds = df_sds[mask]
        st.dataframe(df_sds, use_container_width=True, hide_index=True,
                     column_config={"id": "ID", "config_final": "Config Final",
                                    "fecha_salida": "Fecha Salida", "folio": "Folio"})
        if not df_sds.empty:
            selected_sds_id = st.selectbox("Seleccionar SD para gestionar",
                                           options=df_sds['id'].tolist(),
                                           format_func=lambda x: f"ID {x} - Folio: {df_sds[df_sds['id']==x]['folio'].iloc[0]}",
                                           key="select_sds")
            if selected_sds_id:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Editar", key="edit_sds_btn"):
                        st.session_state['edit_sds'] = selected_sds_id
                with col2:
                    if st.button("Eliminar", key="delete_sds_btn"):
                        if st.session_state.get('confirm_delete_sds') == selected_sds_id:
                            delete_sd(selected_sds_id)
                            st.success("SD eliminada")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.session_state['confirm_delete_sds'] = selected_sds_id
                            st.warning("Presiona nuevamente para confirmar")
    else:
        st.info("No hay SDs registradas")
    
    # ----- FORMULARIO DE AGREGAR SD (CORREGIDO) -----
    with st.expander("Agregar SD Enviada", expanded=False):
        # Checkboxes fuera del formulario
        col1, col2 = st.columns(2)
        with col1:
            agregar_config_sd = st.checkbox("Agregar fecha de configuración final", key="agregar_config_sd")
        with col2:
            agregar_salida_sd = st.checkbox("Agregar fecha de salida", key="agregar_salida_sd")
        
        with st.form("form_sds"):
            col1, col2 = st.columns(2)
            with col1:
                config_final = st.date_input("Config final", key="sds_fecha_config") if agregar_config_sd else None
            with col2:
                if agregar_salida_sd:
                    fecha_salida = st.date_input("Fecha salida", key="sds_fecha_salida")
                    folio = st.text_input("Folio", key="sds_folio")
                else:
                    fecha_salida = None
                    folio = None
            if st.form_submit_button("Guardar SD", use_container_width=True):
                insert_sd((format_fecha(config_final), format_fecha(fecha_salida), folio))
                st.success("SD agregada exitosamente")
                st.cache_data.clear()
                st.rerun()
    
    # Formulario de edición SD (sin cambios)
    if st.session_state.get('edit_sds'):
        st.markdown("---")
        st.subheader(f"Editando SD ID: {st.session_state['edit_sds']}")
        actual = next((s for s in sds if s['id'] == st.session_state['edit_sds']), None)
        if actual:
            with st.form("form_edit_sds"):
                col1, col2 = st.columns(2)
                with col1:
                    if st.checkbox("Editar config final", value=bool(actual.get('config_final'))):
                        config_final = st.date_input("Config final",
                                                     value=parse_fecha(actual.get('config_final')) if actual.get('config_final') else datetime.now().date())
                    else:
                        config_final = None
                with col2:
                    if st.checkbox("Editar fecha salida", value=bool(actual.get('fecha_salida'))):
                        fecha_salida = st.date_input("Fecha salida",
                                                     value=parse_fecha(actual.get('fecha_salida')) if actual.get('fecha_salida') else datetime.now().date())
                        folio = st.text_input("Folio", actual.get('folio', ''))
                    else:
                        fecha_salida = None
                        folio = None
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Actualizar SD", use_container_width=True):
                        update_sd(st.session_state['edit_sds'],
                                  (format_fecha(config_final), format_fecha(fecha_salida), folio))
                        st.success("SD actualizada")
                        st.session_state['edit_sds'] = None
                        st.cache_data.clear()
                        st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state['edit_sds'] = None
                        st.rerun()

# ========== TAB 4: STOCK SDS ==========
with tab4:
    st.subheader("Stock de SDs")
    
    sds_stock = get_sds_stock()
    if sds_stock:
        df_sds_stock = pd.DataFrame(sds_stock)
        st.dataframe(df_sds_stock, use_container_width=True, hide_index=True,
                     column_config={"id": "ID", "reiniciada": "Reiniciada",
                                    "fecha_reinicio": "Fecha Reinicio", "fecha_llegada": "Fecha Llegada"})
        if not df_sds_stock.empty:
            selected_sds_stock_id = st.selectbox("Seleccionar SD stock para gestionar",
                                                 options=df_sds_stock['id'].tolist(),
                                                 format_func=lambda x: f"ID {x} - Reiniciada: {df_sds_stock[df_sds_stock['id']==x]['reiniciada'].iloc[0]}",
                                                 key="select_sds_stock")
            if selected_sds_stock_id:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Editar", key="edit_sds_stock_btn"):
                        st.session_state['edit_sds_stock'] = selected_sds_stock_id
                with col2:
                    if st.button("Eliminar", key="delete_sds_stock_btn"):
                        if st.session_state.get('confirm_delete_sds_stock') == selected_sds_stock_id:
                            delete_sd_stock(selected_sds_stock_id)
                            st.success("SD eliminada del stock")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.session_state['confirm_delete_sds_stock'] = selected_sds_stock_id
                            st.warning("Presiona nuevamente para confirmar")
    else:
        st.info("No hay SDs en stock")
    
    # ----- FORMULARIO DE AGREGAR SD A STOCK (CORREGIDO) -----
    with st.expander("Agregar SD a Stock", expanded=False):
        # Checkbox fuera del formulario
        agregar_llegada_sd_stock = st.checkbox("Agregar fecha de llegada", key="agregar_llegada_sd_stock")
        
        with st.form("form_sds_stock"):
            col1, col2 = st.columns(2)
            with col1:
                reiniciada = st.selectbox("Reiniciada", ["No", "Si"], key="sds_stock_reiniciada")
            with col2:
                if reiniciada == "Si":
                    fecha_reinicio = st.date_input("Fecha reinicio", key="sds_stock_fecha_reinicio")
                else:
                    fecha_reinicio = None
                fecha_llegada = st.date_input("Fecha llegada", key="sds_stock_fecha_llegada") if agregar_llegada_sd_stock else None
            if st.form_submit_button("Guardar SD en Stock", use_container_width=True):
                insert_sd_stock((reiniciada, format_fecha(fecha_reinicio), format_fecha(fecha_llegada)))
                st.success("SD agregada al stock exitosamente")
                st.cache_data.clear()
                st.rerun()
    
    # Formulario de edición SD stock (sin cambios)
    if st.session_state.get('edit_sds_stock'):
        st.markdown("---")
        st.subheader(f"Editando SD Stock ID: {st.session_state['edit_sds_stock']}")
        actual = next((s for s in sds_stock if s['id'] == st.session_state['edit_sds_stock']), None)
        if actual:
            with st.form("form_edit_sds_stock"):
                col1, col2 = st.columns(2)
                with col1:
                    reiniciada = st.selectbox("Reiniciada", ["No", "Si"],
                                              index=1 if actual['reiniciada'] == "Si" else 0)
                with col2:
                    if reiniciada == "Si":
                        fecha_reinicio = st.date_input("Fecha reinicio",
                                                       value=parse_fecha(actual.get('fecha_reinicio')) if actual.get('fecha_reinicio') else datetime.now().date())
                    else:
                        fecha_reinicio = None
                    if st.checkbox("Editar fecha llegada", value=bool(actual.get('fecha_llegada'))):
                        fecha_llegada = st.date_input("Fecha llegada",
                                                      value=parse_fecha(actual.get('fecha_llegada')) if actual.get('fecha_llegada') else datetime.now().date())
                    else:
                        fecha_llegada = None
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Actualizar SD Stock", use_container_width=True):
                        update_sd_stock(st.session_state['edit_sds_stock'],
                                        (reiniciada, format_fecha(fecha_reinicio), format_fecha(fecha_llegada)))
                        st.success("SD Stock actualizada")
                        st.session_state['edit_sds_stock'] = None
                        st.cache_data.clear()
                        st.rerun()
                with col2:
                    if st.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state['edit_sds_stock'] = None
                        st.rerun()

# ========== FOOTER ==========
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; padding: 1rem;'>"
    "Sistema de Gestión de Inventario v2.0"
    "</div>",
    unsafe_allow_html=True
)