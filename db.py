import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

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
    """Inicializa todas las tablas de la base de datos (vacías)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # ===== TABLAS MAESTRAS (CATÁLOGOS) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ref_prod TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('DISPOSITIVO', 'SD', 'CABLE_USB', 'CABLE_ETHERNET', 'CABLE_C')),
                descripcion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ===== INVENTARIO FÍSICO =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                estado TEXT NOT NULL DEFAULT 'DISPONIBLE' 
                    CHECK(estado IN ('DISPONIBLE', 'CONFIGURADO', 'ENVIADO', 'DEFECTUOSO')),
                fecha_ingreso DATE NOT NULL,
                observaciones TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT
            )
        """)

        # Verificar si la columna observaciones ya existe (por si se ejecuta sobre una DB existente)
        cursor.execute("PRAGMA table_info(inventario)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'observaciones' not in columns:
            cursor.execute("ALTER TABLE inventario ADD COLUMN observaciones TEXT")

        # ===== CONFIGURACIONES DE SD =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sd_configuraciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventario_id INTEGER NOT NULL UNIQUE,
                config_final DATE,
                fecha_configuracion DATE NOT NULL,
                imagen_quemada TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventario_id) REFERENCES inventario(id) ON DELETE CASCADE
            )
        """)

        # ===== MOVIMIENTOS (ENVÍOS) =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS envios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folio TEXT UNIQUE NOT NULL,
                fecha_salida DATE NOT NULL,
                destino TEXT,
                descripcion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS envio_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                envio_id INTEGER NOT NULL,
                inventario_id INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (envio_id) REFERENCES envios(id) ON DELETE CASCADE,
                FOREIGN KEY (inventario_id) REFERENCES inventario(id) ON DELETE RESTRICT
            )
        """)

        # ===== ÍNDICES PARA MEJORAR RENDIMIENTO =====
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_estado ON inventario(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_producto ON inventario(producto_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_envios_folio ON envios(folio)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sd_config_inventario ON sd_configuraciones(inventario_id)")
        
        conn.commit()

# ========== FUNCIONES HELPER ==========
def format_fecha(fecha):
    """Convierte fecha a string para BD"""
    if fecha:
        return fecha.strftime("%Y-%m-%d")
    return None

def generar_ref(tipo: str) -> str:
    prefijos = {
        'DISPOSITIVO': 'DIS',
        'SD': 'SD',
        'CABLE_USB': 'USB',
        'CABLE_ETHERNET': 'ETH',
        'CABLE_C': 'C'
    }
    prefijo = prefijos.get(tipo, 'GEN')
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ref_prod FROM productos
            WHERE ref_prod LIKE ? || '-%'
        """, (prefijo,))
        existing = [row['ref_prod'] for row in cursor.fetchall()]
    
    max_num = 0
    for ref in existing:
        try:
            num = int(ref.split('-')[-1])
            if num > max_num:
                max_num = num
        except:
            continue
    
    nuevo_num = max_num + 1
    return f"{prefijo}-{nuevo_num:03d}"

# ========== GESTIÓN DE PRODUCTOS ==========
def crear_producto(tipo: str, nombre: Optional[str] = None, descripcion: str = "", ref: Optional[str] = None):
    if ref is None:
        ref = generar_ref(tipo)
    if nombre is None:
        nombre = f"{tipo}"
    
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO productos (ref_prod, tipo, nombre, descripcion)
                VALUES (?, ?, ?, ?)
            """, (ref, tipo, nombre, descripcion))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"Ya existe un producto con REF '{ref}'")

def get_productos():
    """Obtiene todos los productos del catálogo"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos ORDER BY tipo, nombre")
        return [dict(row) for row in cursor.fetchall()]

# ========== GESTIÓN DE INVENTARIO ==========
def agregar_producto_a_inventario(producto_id: int, cantidad: int, fecha_ingreso=None):
    """Agrega múltiples unidades de un producto al inventario"""
    if not fecha_ingreso:
        fecha_ingreso = datetime.now().date()
    
    ids_generados = []
    with get_connection() as conn:
        cursor = conn.cursor()
        for _ in range(cantidad):
            cursor.execute("""
                INSERT INTO inventario (producto_id, fecha_ingreso, estado)
                VALUES (?, ?, 'DISPONIBLE')
            """, (producto_id, format_fecha(fecha_ingreso)))
            ids_generados.append(cursor.lastrowid)
        conn.commit()
    return ids_generados

def obtener_stock_disponible(producto_id: Optional[int] = None, tipo: Optional[str] = None):
    """Obtiene inventario disponible, filtrado por producto o tipo"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT i.*, p.nombre as producto_nombre, p.ref_prod, p.tipo,
                   sc.config_final, sc.fecha_configuracion
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            WHERE i.estado = 'DISPONIBLE'
        """
        params = []
        
        if producto_id:
            query += " AND i.producto_id = ?"
            params.append(producto_id)
        elif tipo:
            query += " AND p.tipo = ?"
            params.append(tipo)
        
        query += " ORDER BY i.fecha_ingreso DESC"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def obtener_todo_el_inventario():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                i.id,
                i.estado,
                i.fecha_ingreso,

                p.nombre AS producto_nombre,
                p.ref_prod,
                p.tipo,

                sc.config_final,
                sc.fecha_configuracion
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            ORDER BY 
                CASE i.estado 
                    WHEN 'DISPONIBLE' THEN 1
                    WHEN 'CONFIGURADO' THEN 2
                    WHEN 'ENVIADO' THEN 3
                    ELSE 4
                END,
                i.fecha_ingreso DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def configurar_sd(inventario_id: int, config_final=None):
    """Marca una SD como configurada"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.*, p.tipo FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE i.id = ? AND i.estado = 'DISPONIBLE'
        """, (inventario_id,))
        
        item = cursor.fetchone()
        if not item:
            raise ValueError("El item no existe o no está disponible")
        
        if item['tipo'] != 'SD':
            raise ValueError("Solo se pueden configurar tarjetas SD")
        
        cursor.execute("""
            INSERT INTO sd_configuraciones (inventario_id, config_final, fecha_configuracion)
            VALUES (?, ?, date('now'))
        """, (inventario_id, format_fecha(config_final)))
        
        cursor.execute("""
            UPDATE inventario SET estado = 'CONFIGURADO' WHERE id = ?
        """, (inventario_id,))
        
        conn.commit()
        return True

# ========== FUNCIONES PARA EDITAR/ELIMinar EN INVENTARIO ==========
def actualizar_item_inventario(item_id, estado=None, observaciones=None):
    """Actualiza los campos editables de un item del inventario"""
    with get_connection() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        if estado is not None:
            updates.append("estado = ?")
            params.append(estado)
        if observaciones is not None:
            updates.append("observaciones = ?")
            params.append(observaciones)
        if not updates:
            return False
        params.append(item_id)
        cursor.execute(f"UPDATE inventario SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        return cursor.rowcount > 0

def eliminar_item_inventario(item_id):
    """Elimina un item del inventario siempre que no esté referenciado en envíos"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM inventario WHERE id = ?", (item_id,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            raise ValueError("No se puede eliminar el item porque está asociado a un envío o configuración.")

# ========== PROCESAMIENTO DE ENVÍOS ==========
def procesar_envio(items: list, folio: str, destino: str = "", descripcion: str = "", fecha_salida=None):
    """
    Procesa un envío a partir de una lista de items solicitados.
    items: lista de diccionarios con 'producto_id' y 'cantidad'
    """
    if not fecha_salida:
        fecha_salida = datetime.now().date()
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN TRANSACTION")
        
        inventario_ids = []
        
        for req in items:
            producto_id = req['producto_id']
            cantidad_necesaria = req['cantidad']
            
            cursor.execute("""
                SELECT id FROM inventario
                WHERE producto_id = ? AND estado IN ('DISPONIBLE', 'CONFIGURADO')
                ORDER BY fecha_ingreso ASC
                LIMIT ?
            """, (producto_id, cantidad_necesaria))
            
            disponibles = cursor.fetchall()
            
            if len(disponibles) < cantidad_necesaria:
                cursor.execute("SELECT nombre FROM productos WHERE id = ?", (producto_id,))
                producto_nombre = cursor.fetchone()['nombre']
                raise ValueError(
                    f"Stock insuficiente para {producto_nombre}. "
                    f"Requerido: {cantidad_necesaria}, Disponible: {len(disponibles)}"
                )
            
            for item in disponibles:
                inventario_ids.append(item['id'])
        
        cursor.execute("""
            INSERT INTO envios (folio, fecha_salida, destino, descripcion)
            VALUES (?, ?, ?, ?)
        """, (folio, format_fecha(fecha_salida), destino, descripcion))
        envio_id = cursor.lastrowid
        
        for inventario_id in inventario_ids:
            cursor.execute("""
                UPDATE inventario SET estado = 'ENVIADO' WHERE id = ?
            """, (inventario_id,))
            
            cursor.execute("""
                INSERT INTO envio_detalle (envio_id, inventario_id)
                VALUES (?, ?)
            """, (envio_id, inventario_id))
        
        conn.commit()
        return {
            'envio_id': envio_id,
            'folio': folio,
            'items_procesados': len(inventario_ids)
        }
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_envios():
    """Obtiene todos los envíos realizados"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.*, COUNT(ed.id) as total_items
            FROM envios e
            LEFT JOIN envio_detalle ed ON e.id = ed.envio_id
            GROUP BY e.id
            ORDER BY e.fecha_salida DESC, e.id DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_detalle_envio(envio_id: int):
    """Obtiene el detalle completo de un envío"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ed.*, i.estado,
                   p.nombre as producto_nombre, p.ref_prod, p.tipo,
                   sc.config_final
            FROM envio_detalle ed
            JOIN inventario i ON ed.inventario_id = i.id
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            WHERE ed.envio_id = ?
        """, (envio_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_metricas():
    """Obtiene métricas generales del inventario"""
    with get_connection() as conn:
        cursor = conn.cursor()
        metricas = {}
        
        cursor.execute("""
            SELECT p.tipo, COUNT(*) as cantidad
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE i.estado = 'DISPONIBLE'
            GROUP BY p.tipo
        """)
        stock_por_tipo = {row['tipo']: row['cantidad'] for row in cursor.fetchall()}
        
        metricas['dispositivos_disponibles'] = stock_por_tipo.get('DISPOSITIVO', 0)
        metricas['sds_disponibles'] = stock_por_tipo.get('SD', 0)
        metricas['cables_usb_disponibles'] = stock_por_tipo.get('CABLE_USB', 0)
        metricas['cables_eth_disponibles'] = stock_por_tipo.get('CABLE_ETHERNET', 0)
        
        cursor.execute("SELECT COUNT(*) FROM inventario WHERE estado IN ('DISPONIBLE', 'CONFIGURADO')")
        metricas['total_en_inventario'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM envios")
        metricas['total_envios'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM sd_configuraciones")
        metricas['sds_configuradas'] = cursor.fetchone()[0]
        
        return metricas