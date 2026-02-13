import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_NAME = "inventario.db"

@contextmanager
def get_connection():
    """Context manager para manejo seguro de conexiones"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Inicializa todas las tablas de la base de datos"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabla de dispositivos enviados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispositivos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                cables TEXT NOT NULL,
                tipo_cable TEXT,
                ethernet TEXT,
                config_final TEXT,
                fecha_salida TEXT,
                folio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabla de stock de dispositivos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispositivos_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                cables TEXT NOT NULL,
                sd TEXT NOT NULL,
                reiniciado TEXT NOT NULL,
                fecha_reinicio TEXT,
                fecha_llegada TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de SDs enviadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_final TEXT,
                fecha_salida TEXT,
                folio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de stock de SDs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sds_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reiniciada TEXT NOT NULL,
                fecha_reinicio TEXT,
                fecha_llegada TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

# ========== FUNCIONES HELPER ==========
def parse_fecha(fecha):
    """Convierte string a datetime object de forma segura"""
    if fecha and fecha != "None" and fecha is not None:
        try:
            return datetime.strptime(fecha, "%Y-%m-%d").date()
        except:
            return datetime.now().date()
    return None

def format_fecha(fecha):
    """Convierte fecha a string para BD"""
    if fecha:
        return fecha.strftime("%Y-%m-%d")
    return None

# ========== DISPOSITIVOS ENVIADOS ==========
def get_dispositivos():
    """Obtiene todos los dispositivos enviados"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dispositivos ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def insert_dispositivo(data):
    """Inserta un nuevo dispositivo enviado"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dispositivos
            (version, cables, tipo_cable, ethernet, config_final, fecha_salida, folio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
        return cursor.lastrowid

def update_dispositivo(id, data):
    """Actualiza un dispositivo enviado"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dispositivos SET
                version=?, cables=?, tipo_cable=?, ethernet=?,
                config_final=?, fecha_salida=?, folio=?
            WHERE id=?
        """, (*data, id))
        conn.commit()

def delete_dispositivo(id):
    """Elimina un dispositivo enviado"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dispositivos WHERE id=?", (id,))
        conn.commit()

# ========== STOCK DISPOSITIVOS ==========
def get_dispositivos_stock():
    """Obtiene todos los dispositivos en stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dispositivos_stock ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def insert_dispositivo_stock(data):
    """Inserta un nuevo dispositivo en stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dispositivos_stock
            (version, cables, sd, reiniciado, fecha_reinicio, fecha_llegada)
            VALUES (?, ?, ?, ?, ?, ?)
        """, data)
        conn.commit()
        return cursor.lastrowid

def update_dispositivo_stock(id, data):
    """Actualiza un dispositivo en stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dispositivos_stock SET
                version=?, cables=?, sd=?, reiniciado=?, 
                fecha_reinicio=?, fecha_llegada=?
            WHERE id=?
        """, (*data, id))
        conn.commit()

def delete_dispositivo_stock(id):
    """Elimina un dispositivo del stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dispositivos_stock WHERE id=?", (id,))
        conn.commit()

# ========== SDS ENVIADAS ==========
def get_sds():
    """Obtiene todas las SDs enviadas"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sds ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def insert_sd(data):
    """Inserta una nueva SD enviada"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sds (config_final, fecha_salida, folio)
            VALUES (?, ?, ?)
        """, data)
        conn.commit()
        return cursor.lastrowid

def update_sd(id, data):
    """Actualiza una SD enviada"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sds SET
                config_final=?, fecha_salida=?, folio=?
            WHERE id=?
        """, (*data, id))
        conn.commit()

def delete_sd(id):
    """Elimina una SD enviada"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sds WHERE id=?", (id,))
        conn.commit()

# ========== SDS EN STOCK ==========
def get_sds_stock():
    """Obtiene todas las SDs en stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sds_stock ORDER BY id DESC")
        return [dict(row) for row in cursor.fetchall()]

def insert_sd_stock(data):
    """Inserta una nueva SD en stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sds_stock (reiniciada, fecha_reinicio, fecha_llegada)
            VALUES (?, ?, ?)
        """, data)
        conn.commit()
        return cursor.lastrowid

def update_sd_stock(id, data):
    """Actualiza una SD en stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sds_stock SET
                reiniciada=?, fecha_reinicio=?, fecha_llegada=?
            WHERE id=?
        """, (*data, id))
        conn.commit()

def delete_sd_stock(id):
    """Elimina una SD del stock"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sds_stock WHERE id=?", (id,))
        conn.commit()

# ========== MÉTRICAS ==========
def get_metricas():
    """Obtiene métricas generales del inventario"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        metricas = {}
        
        # Total dispositivos enviados
        cursor.execute("SELECT COUNT(*) FROM dispositivos")
        metricas['total_dispositivos'] = cursor.fetchone()[0]
        
        # Total dispositivos en stock
        cursor.execute("SELECT COUNT(*) FROM dispositivos_stock")
        metricas['total_stock'] = cursor.fetchone()[0]
        
        # Total SDs enviadas
        cursor.execute("SELECT COUNT(*) FROM sds")
        metricas['total_sds'] = cursor.fetchone()[0]
        
        # Total SDs en stock
        cursor.execute("SELECT COUNT(*) FROM sds_stock")
        metricas['total_sds_stock'] = cursor.fetchone()[0]
        
        return metricas