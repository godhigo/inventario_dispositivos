import streamlit as st
import pandas as pd
from db import *

st.set_page_config(page_title="Inventario", layout="wide")
init_db()
st.title("Inventario de Dispositivos")

def parse_fecha(fecha):
    if fecha and fecha != "None":
        try:
            return pd.to_datetime(fecha)
        except:
            return pd.Timestamp.today()
    return None

# ---------- DISP ENVIADOS ----------
st.subheader("Dispositivos Enviados")

tabla_container = st.empty()

def mostrar_tabla():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM dispositivos", conn)
    conn.close()
    tabla_container.dataframe(df, use_container_width=True)
    return df

df = mostrar_tabla()

ids = df["id"].tolist() if not df.empty else []
selected_id = st.selectbox("Selecciona un dispositivo", ids) if ids else None

# ---------- AGREGAR DISP ENVIADOS ----------
with st.expander("Agregar Dispositivo"):
    version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"])
    cables = st.selectbox("¿Tiene cables?", ["No", "Si"])

    tipo_cable = ethernet = None
    if cables == "Si":
        tipo_cable = st.selectbox("Tipo de Cable", ["Tipo C", "USB"])
        ethernet = st.selectbox("¿Ethernet?", ["No", "Si"])

    config_final = st.date_input("Configuración final") if st.checkbox("Agregar configuración final") else None

    fecha_salida = st.date_input("Fecha de salida") if st.checkbox("Agregar fecha de salida") else None
    folio = st.text_input("Folio") if fecha_salida else None

    if st.button("Guardar"):
        insertar((
            version, cables, tipo_cable, ethernet,
            str(config_final) if config_final else None,
            str(fecha_salida) if fecha_salida else None,
            folio
        ))
        st.success("Dispositivo agregado")
        df = mostrar_tabla()

# ---------- EDITAR DISP ENVIADOS ----------
if selected_id:
    with st.expander(f"Editar dispositivo con ID {selected_id}"):
        actual = df[df["id"] == selected_id].iloc[0]
        with st.form("editar"):
            version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"],
                                   index=["Normal", "Pro", "Max", "AMIcalidad"].index(actual["version"]))
            cables = st.selectbox("¿Cables?", ["No", "Si"], index=1 if actual["cables"] == "Si" else 0)

            tipo_cable = ethernet = None
            if cables == "Si":
                tipo_cable = st.selectbox("Tipo cable", ["Tipo C", "USB"])
                ethernet = st.selectbox("Ethernet", ["No", "Si"])


            config_final = st.date_input("Config final", parse_fecha(actual["config_final"])) if st.checkbox("Editar config final", value=bool(actual["config_final"])) else None
            fecha_salida = st.date_input("Fecha salida", parse_fecha(actual["fecha_salida"])) if st.checkbox("Editar fecha salida", value=bool(actual["fecha_salida"])) else None
            folio = st.text_input("Folio", actual["folio"] if fecha_salida else "")

            if st.form_submit_button("Actualizar"):
                actualizar(selected_id, (
                    version, cables, tipo_cable, ethernet,
                    str(config_final) if config_final else None,
                    str(fecha_salida) if fecha_salida else None,
                    folio
                ))
                st.success("Actualizado")
                df = mostrar_tabla()

# ---------- ELIMINAR DISP ENVIADOS ----------
if selected_id:
    with st.expander(f"Eliminar dispositivo con ID {selected_id}"):
        if st.button("Eliminar", type="primary"):
            eliminar(selected_id)
            st.warning("Eliminado")
            df = mostrar_tabla()

# ---------- STOCK ----------
st.divider()
st.subheader("Stock de Dispositivos")

stock_container = st.empty()

def mostrar_stock():
    conn = get_connection()
    df_stock = pd.read_sql_query("SELECT * FROM dispositivos_stock", conn)
    conn.close()
    stock_container.dataframe(df_stock, use_container_width=True)
    return df_stock

df_stock = mostrar_stock()

stock_ids = df_stock["id"].tolist() if not df_stock.empty else []
selected_stock_id = st.selectbox("Selecciona stock", stock_ids) if stock_ids else None

# ---------- AGREGAR STOCK ----------
with st.expander("Agregar a Stock"):
    version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"], key="s_v")
    cables = st.selectbox("Cables", ["No", "Si"], key="s_c")
    sd = st.selectbox("SD", ["No", "Si"], key="s_sd")
    reiniciado = st.selectbox("Reiniciado", ["No", "Si"], key="s_r")

    fecha_reinicio = st.date_input("Fecha reinicio") if reiniciado == "Si" else None
    fecha_llegada = st.date_input("Fecha llegada") if st.checkbox("Agregar fecha llegada") else None

    if st.button("Guardar stock"):
        insertar_stock((
            version, cables, sd, reiniciado,
            str(fecha_reinicio) if fecha_reinicio else None,
            str(fecha_llegada) if fecha_llegada else None
        ))
        st.success("Agregado a stock")
        df_stock = mostrar_stock()

# ---------- EDITAR STOCK ----------
if selected_stock_id:
    with st.expander(f"Editar stock con ID {selected_stock_id}"):
        actual = df_stock[df_stock["id"] == selected_stock_id].iloc[0]
        with st.form("editar_stock"):
            version = st.selectbox("Versión", ["Normal", "Pro", "Max", "AMIcalidad"],
                                   index=["Normal", "Pro", "Max", "AMIcalidad"].index(actual["version"]))
            cables = st.selectbox("Cables", ["No", "Si"], index=1 if actual["cables"] == "Si" else 0)
            sd = st.selectbox("SD", ["No", "Si"], index=1 if actual["sd"] == "Si" else 0)
            reiniciado = st.selectbox("Reiniciado", ["No", "Si"], index=1 if actual["reiniciado"] == "Si" else 0)

            fecha_reinicio = st.date_input("Fecha reinicio", parse_fecha(actual["fecha_reinicio"])) if reiniciado == "Si" else None
            fecha_llegada = st.date_input("Fecha llegada", parse_fecha(actual["fecha_llegada"])) if st.checkbox("Editar fecha llegada", value=bool(actual["fecha_llegada"])) else None

            if st.form_submit_button("Actualizar stock"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE dispositivos_stock SET
                    version=?, cables=?, sd=?, reiniciado=?, fecha_reinicio=?, fecha_llegada=?
                    WHERE id=?
                """, (
                    version, cables, sd, reiniciado,
                    str(fecha_reinicio) if fecha_reinicio else None,
                    str(fecha_llegada) if fecha_llegada else None,
                    selected_stock_id
                ))
                conn.commit()
                conn.close()
                st.success("Stock actualizado")
                df_stock = mostrar_stock()

# ---------- ELIMINAR STOCK ----------
if selected_stock_id:
    with st.expander(f"Eliminar stock con ID {selected_stock_id}"):
        if st.button("Eliminar stock", type="primary"):
            eliminar_stock(selected_stock_id)
            st.warning("Stock eliminado")
            df_stock = mostrar_stock()
            
# ---------- SDs ENVIADAS ----------
st.divider()
st.subheader("SDs Enviadas")

sds_container = st.empty()

def mostrar_sds():
    conn = get_connection()
    df_sds = pd.read_sql_query("SELECT * FROM sds", conn)
    conn.close()
    sds_container.dataframe(df_sds, use_container_width=True)
    return df_sds

df_sds = mostrar_sds()

sds_ids = df_sds["id"].tolist() if not df_sds.empty else []
selected_sds_id = st.selectbox(
    "Selecciona una SD enviada",
    sds_ids,
    key="sds_env_select"
) if sds_ids else None

# ---------- AGREGAR SD ENVIADA ----------
with st.expander("Agregar SD enviada"):
    config_final = st.date_input(
        "Config final",
        key="sds_env_config_final"
    ) if st.checkbox(
        "Agregar config final",
        key="sds_env_chk_config"
    ) else None
    fecha_salida = st.date_input(
        "Fecha salida",
        key="sds_env_fecha_salida"
    ) if st.checkbox(
        "Agregar fecha salida",
        key="sds_env_chk_salida"
    ) else None

    folio = st.text_input(
        "Folio",
        key="sds_env_folio"
    ) if fecha_salida else None

    if st.button("Guardar SD", key="sds_env_guardar"):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sds
            (config_final, fecha_salida, folio)
            VALUES (?, ?, ?)
        """, (
            str(config_final) if config_final else None,
            str(fecha_salida) if fecha_salida else None,
            folio
        ))
        conn.commit()
        conn.close()
        st.success("SD enviada agregada")
        df_sds = mostrar_sds()

# ---------- EDITAR SD ENVIADA ----------
if selected_sds_id:
    with st.expander(f"Editar SD enviada ID {selected_sds_id}"):
        actual = df_sds[df_sds["id"] == selected_sds_id].iloc[0]
        with st.form("editar_sds"):
            config_final = st.date_input(
                "Config final",
                parse_fecha(actual["config_final"]),
                key="sds_env_config_final_edit"
            ) if st.checkbox(
                "Editar config final",
                value=bool(actual["config_final"]),
                key="sds_env_chk_config_edit"
            ) else None
            fecha_salida = st.date_input(
                "Fecha salida",
                parse_fecha(actual["fecha_salida"]),
                key="sds_env_fecha_salida_edit"
            ) if st.checkbox(
                "Editar fecha salida",
                value=bool(actual["fecha_salida"]),
                key="sds_env_chk_salida_edit"
            ) else None
            folio = st.text_input(
                "Folio",
                actual["folio"] if fecha_salida else "",
                key="sds_env_folio_edit"
            )
            if st.form_submit_button("Actualizar SD"):
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sds SET
                    config_final=?, fecha_salida=?, folio=?
                    WHERE id=?
                """, (
                    str(config_final) if config_final else None,
                    str(fecha_salida) if fecha_salida else None,
                    folio,
                    selected_sds_id
                ))
                conn.commit()
                conn.close()
                st.success("SD actualizada")
                df_sds = mostrar_sds()

# ---------- ELIMINAR SD ----------
if selected_sds_id:
    with st.expander(f"Eliminar SD enviada ID {selected_sds_id}"):
        if st.button("Eliminar SD", type="primary", key="sds_env_eliminar"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sds WHERE id=?", (selected_sds_id,))
            conn.commit()
            conn.close()
            st.warning("SD eliminada")
            df_sds = mostrar_sds()

# ---------- SDS EN STOCK ----------
st.divider()
st.subheader("Stock de SDs")

sds_stock_container = st.empty()

def mostrar_sds_stock():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM sds_stock", conn)
    conn.close()
    sds_stock_container.dataframe(df, use_container_width=True)
    return df

df_sds_stock = mostrar_sds_stock()

sds_stock_ids = df_sds_stock["id"].tolist() if not df_sds_stock.empty else []
selected_sds_stock_id = st.selectbox(
    "Selecciona SD en stock",
    sds_stock_ids,
    key="sds_stock_select"
) if sds_stock_ids else None

# ---------- AGREGAR SDS STOCK ----------
with st.expander("Agregar SD a stock"):
    reiniciada = st.selectbox(
        "Reiniciada",
        ["No", "Si"],
        key="sds_stock_reiniciada"
    )

    fecha_reinicio = st.date_input(
        "Fecha reinicio",
        key="sds_stock_fecha_reinicio"
    ) if reiniciada == "Si" else None

    fecha_llegada = st.date_input(
        "Fecha llegada",
        key="sds_stock_fecha_llegada"
    ) if st.checkbox(
        "Agregar fecha llegada",
        key="sds_stock_chk_llegada"
    ) else None

    if st.button("Guardar SD en stock", key="sds_stock_guardar"):
        insertar_sds_stock((
            reiniciada,
            str(fecha_reinicio) if fecha_reinicio else None,
            str(fecha_llegada) if fecha_llegada else None
        ))
        st.success("SD agregada a stock")
        df_sds_stock = mostrar_sds_stock()

# ---------- EDITAR SDS STOCK ----------
if selected_sds_stock_id:
    with st.expander(f"Editar SD stock ID {selected_sds_stock_id}"):
        actual = df_sds_stock[df_sds_stock["id"] == selected_sds_stock_id].iloc[0]
        with st.form("editar_sds_stock"):
            reiniciada = st.selectbox(
                "Reiniciada",
                ["No", "Si"],
                index=1 if actual["reiniciada"] == "Si" else 0,
                key="sds_stock_reiniciada_edit"
            )

            fecha_reinicio = st.date_input(
                "Fecha reinicio",
                parse_fecha(actual["fecha_reinicio"]),
                key="sds_stock_fecha_reinicio_edit"
            ) if reiniciada == "Si" else None

            fecha_llegada = st.date_input(
                "Fecha llegada",
                parse_fecha(actual["fecha_llegada"]),
                key="sds_stock_fecha_llegada_edit"
            ) if st.checkbox(
                "Editar fecha llegada",
                value=bool(actual["fecha_llegada"]),
                key="sds_stock_chk_llegada_edit"
            ) else None

            if st.form_submit_button("Actualizar SD stock"):
                actualizar_sds_stock(
                    selected_sds_stock_id,
                    (
                        reiniciada,
                        str(fecha_reinicio) if fecha_reinicio else None,
                        str(fecha_llegada) if fecha_llegada else None
                    )
                )
                st.success("Stock de SD actualizado")
                df_sds_stock = mostrar_sds_stock()

# ---------- ELIMINAR SDS STOCK ----------
if selected_sds_stock_id:
    with st.expander(f"Eliminar SD stock ID {selected_sds_stock_id}"):
        if st.button("Eliminar SD stock", type="primary", key="sds_stock_eliminar"):
            eliminar_sds_stock(selected_sds_stock_id)
            st.warning("SD en stock eliminada")
            df_sds_stock = mostrar_sds_stock()
