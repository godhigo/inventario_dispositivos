import sqlite3

DB_NAME = "inventario.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispositivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT,
            cables TEXT,
            tipo_cable TEXT,
            ethernet TEXT,
            config_final TEXT,
            fecha_salida TEXT,
            folio TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dispositivos_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT,
            cables TEXT,
            sd TEXT,
            reiniciado TEXT,
            fecha_reinicio TEXT,
            fecha_llegada TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_final TEXT,
            fecha_salida TEXT,
            folio TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sds_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reiniciada TEXT,
            fecha_reinicio TEXT,
            fecha_llegada TEXT
        )
    """)

    conn.commit()
    conn.close()

# ---------- INVENTARIO ----------
def obtener_dispositivos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dispositivos")
    rows = cursor.fetchall()
    conn.close()
    return rows

def insertar(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dispositivos
        (version, cables, tipo_cable, ethernet,
        config_final, fecha_salida, folio)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

def actualizar(id, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE dispositivos SET
        version=?, cables=?, tipo_cable=?, ethernet=?,
        config_final=?, fecha_salida=?, folio=?
        WHERE id=?
    """, (*data, id))
    conn.commit()
    conn.close()

def eliminar(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dispositivos WHERE id=?", (id,))
    conn.commit()
    conn.close()

# ---------- STOCK ----------
def obtener_stock():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dispositivos_stock")
    rows = cursor.fetchall()
    conn.close()
    return rows

def insertar_stock(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO dispositivos_stock
        (version, cables, sd, reiniciado, fecha_reinicio, fecha_llegada)
        VALUES (?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

def eliminar_stock(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dispositivos_stock WHERE id=?", (id,))
    conn.commit()
    conn.close()

def actualizar_stock(id, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE dispositivos_stock SET
        version=?, cables=?, sd=?, reiniciado=?, fecha_reinicio=?, fecha_llegada=?
        WHERE id=?
    """, (*data, id))
    conn.commit()
    conn.close()

# ---------- SDS STOCK ----------
def insertar_sds_stock(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sds_stock
        (reiniciada, fecha_reinicio, fecha_llegada)
        VALUES (?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

def eliminar_sds_stock(id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sds_stock WHERE id=?", (id,))
    conn.commit()
    conn.close()

def actualizar_sds_stock(id, data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE sds_stock SET
        reiniciada=?, fecha_reinicio=?, fecha_llegada=?
        WHERE id=?
    """, (*data, id))
    conn.commit()
    conn.close()

