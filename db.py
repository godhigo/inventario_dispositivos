import sqlite3
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, List, Dict, Any

DB_NAME = "inventario.db"

@contextmanager
def get_connection(read_only: bool = False):
    """
    Context manager para manejo seguro de conexiones.
    read_only=True: No inicia transacción, solo lectura.
    read_only=False: Inicia transacción para escritura.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # Para manejo manual de transacciones
    
    try:
        if not read_only:
            conn.execute("BEGIN IMMEDIATE")  # Solo bloqueamos si vamos a escribir
        yield conn
        if not read_only:
            conn.commit()
    except Exception as e:
        if not read_only:
            conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Inicializa todas las tablas de la base de datos"""
    with get_connection(read_only=False) as conn:
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
                    CHECK(estado IN ('DISPONIBLE', 'REINICIADO', 'CONFIGURADO', 'ENVIADO', 'DEFECTUOSO')),
                fecha_ingreso DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE RESTRICT
            )
        """)

        # ===== CONFIGURACIONES DE SD =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sd_configuraciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventario_id INTEGER NOT NULL UNIQUE,
                config_final DATE NOT NULL,
                fecha_configuracion DATE NOT NULL,
                imagen_quemada TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (inventario_id) REFERENCES inventario(id) ON DELETE CASCADE
            )
        """)

        # ===== CONFIGURACIONES DE DISPOSITIVOS =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispositivo_configuraciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                inventario_id INTEGER NOT NULL UNIQUE,
                fecha_config_inicio DATE NOT NULL,
                fecha_config_final DATE,
                fecha_finalizacion_accion TIMESTAMP,
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

        # ===== TABLA DE SECUENCIAS PARA REFERENCIAS =====
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS secuencias (
                tipo TEXT PRIMARY KEY,
                ultimo_numero INTEGER DEFAULT 0
            )
        """)

        # ===== ÍNDICES PARA MEJORAR RENDIMIENTO =====
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_estado ON inventario(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_producto ON inventario(producto_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_envios_folio ON envios(folio)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sd_config_inventario ON sd_configuraciones(inventario_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_disp_config_inventario ON dispositivo_configuraciones(inventario_id)")
        
        # No hacer commit explícito, el context manager lo hace

# ========== FUNCIONES HELPER ==========
def format_fecha(fecha) -> Optional[str]:
    """Convierte fecha a string para BD"""
    if fecha:
        return fecha.strftime("%Y-%m-%d")
    return None

def generar_ref(tipo: str) -> str:
    """
    Genera referencias únicas usando tabla de secuencias.
    Compatible con SQLite (sin RETURNING en UPDATE).
    """
    prefijos = {
        'DISPOSITIVO': 'DIS',
        'SD': 'SD',
        'CABLE_USB': 'USB',
        'CABLE_ETHERNET': 'ETH',
        'CABLE_C': 'C'
    }
    prefijo = prefijos.get(tipo, 'GEN')
    
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        # Asegurar que existe el contador para este tipo
        cursor.execute("""
            INSERT OR IGNORE INTO secuencias (tipo, ultimo_numero) 
            VALUES (?, 0)
        """, (tipo,))
        
        # Incrementar el contador y obtener el nuevo valor
        # SQLite no soporta RETURNING en UPDATE, así que lo hacemos en dos pasos
        cursor.execute("""
            UPDATE secuencias 
            SET ultimo_numero = ultimo_numero + 1 
            WHERE tipo = ?
        """, (tipo,))
        
        # Obtener el nuevo valor
        cursor.execute("SELECT ultimo_numero FROM secuencias WHERE tipo = ?", (tipo,))
        resultado = cursor.fetchone()
        nuevo_num = resultado['ultimo_numero'] if resultado else 1
        
    return f"{prefijo}-{nuevo_num:03d}"

# ========== FUNCIONES ESPECIALIZADAS DE STOCK ==========
def obtener_items_para_envio(producto_id: Optional[int] = None, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Obtiene items que están listos para ser enviados.
    Solo lectura, no usa transacción de escritura.
    """
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT i.*, p.nombre as producto_nombre, p.ref_prod, p.tipo,
                dc.fecha_config_inicio, dc.fecha_config_final as disp_fecha_config_final,
                sc.config_final as sd_config_final
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            LEFT JOIN dispositivo_configuraciones dc ON i.id = dc.inventario_id
            WHERE (
                -- Dispositivos: solo CONFIGURADOS pueden enviarse
                (p.tipo = 'DISPOSITIVO' AND i.estado = 'CONFIGURADO')
                OR
                -- SDs: solo CONFIGURADAS pueden enviarse
                (p.tipo = 'SD' AND i.estado = 'CONFIGURADO')
                OR
                -- Cables: cualquier DISPONIBLE puede enviarse
                (p.tipo IN ('CABLE_USB', 'CABLE_ETHERNET', 'CABLE_C') AND i.estado = 'DISPONIBLE')
            )
        """
        
        params = []
        
        if producto_id:
            query += " AND i.producto_id = ?"
            params.append(producto_id)
        elif tipo:
            query += " AND p.tipo = ?"
            params.append(tipo)
        
        query += " ORDER BY i.fecha_ingreso ASC"  # FIFO
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def obtener_sds_para_configurar() -> List[Dict[str, Any]]:
    """
    Obtiene SDs disponibles para configurar.
    Verifica que no tengan ya una configuración asociada.
    """
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        
        # SDs disponibles que NO tienen entrada en sd_configuraciones
        cursor.execute("""
            SELECT i.*, p.nombre as producto_nombre, p.ref_prod
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            WHERE p.tipo = 'SD' 
              AND i.estado = 'DISPONIBLE'
              AND sc.id IS NULL  -- No tiene configuración previa
            ORDER BY i.fecha_ingreso ASC
        """)
        
        return [dict(row) for row in cursor.fetchall()]

def obtener_dispositivos_para_reiniciar() -> List[Dict[str, Any]]:
    """
    Obtiene dispositivos disponibles para iniciar reinicio.
    """
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT i.*, p.nombre as producto_nombre, p.ref_prod
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN dispositivo_configuraciones dc ON i.id = dc.inventario_id
            WHERE p.tipo = 'DISPOSITIVO' 
              AND i.estado = 'DISPONIBLE'
              AND dc.id IS NULL  -- No tiene configuración iniciada
            ORDER BY i.fecha_ingreso ASC
        """)
        
        return [dict(row) for row in cursor.fetchall()]

def obtener_dispositivos_reiniciados() -> List[Dict[str, Any]]:
    """
    Obtiene dispositivos en estado REINICIADO para finalizar configuración.
    """
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, p.nombre as producto_nombre, p.ref_prod,
                   dc.fecha_config_inicio
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            JOIN dispositivo_configuraciones dc ON i.id = dc.inventario_id
            WHERE p.tipo = 'DISPOSITIVO' 
              AND i.estado = 'REINICIADO'
              AND dc.fecha_config_final IS NULL  -- Aún no finalizado
            ORDER BY dc.fecha_config_inicio DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def obtener_cables_disponibles() -> List[Dict[str, Any]]:
    """
    Obtiene cables disponibles para envío.
    """
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, p.nombre as producto_nombre, p.ref_prod, p.tipo
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE p.tipo IN ('CABLE_USB', 'CABLE_ETHERNET', 'CABLE_C')
              AND i.estado = 'DISPONIBLE'
            ORDER BY i.fecha_ingreso ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

# ========== GESTIÓN DE PRODUCTOS ==========
def crear_producto(tipo: str, nombre: Optional[str] = None, ref: Optional[str] = None) -> int:
    """Crea un nuevo producto en el catálogo"""
    if ref is None:
        ref = generar_ref(tipo)
    if nombre is None:
        nombre = f"{tipo}"
    
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO productos (ref_prod, tipo, nombre)
                VALUES (?, ?, ?)
            """, (ref, tipo, nombre))
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"Ya existe un producto con REF '{ref}'")

def get_productos() -> List[Dict[str, Any]]:
    """Obtiene todos los productos del catálogo"""
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM productos ORDER BY tipo, nombre")
        return [dict(row) for row in cursor.fetchall()]

# ========== GESTIÓN DE INVENTARIO ==========
def agregar_item_a_inventario(producto_id: int, cantidad: int, fecha_ingreso=None) -> List[int]:
    """Agrega múltiples unidades de un producto al inventario"""
    if not fecha_ingreso:
        fecha_ingreso = datetime.now().date()
    
    ids_generados = []
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        for _ in range(cantidad):
            cursor.execute("""
                INSERT INTO inventario (producto_id, fecha_ingreso, estado)
                VALUES (?, ?, 'DISPONIBLE')
            """, (producto_id, format_fecha(fecha_ingreso)))
            ids_generados.append(cursor.lastrowid)
        
    return ids_generados

def obtener_todo_el_inventario() -> List[Dict[str, Any]]:
    """Obtiene todo el inventario con información relacionada"""
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                i.id,
                i.estado,
                i.fecha_ingreso,

                p.nombre AS producto_nombre,
                p.ref_prod,
                p.tipo,

                sc.config_final as sd_config_final,

                dc.fecha_config_inicio as disp_fecha_config_inicio,
                dc.fecha_config_final as disp_fecha_config_final,
                dc.fecha_finalizacion_accion as disp_fecha_accion
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            LEFT JOIN dispositivo_configuraciones dc ON i.id = dc.inventario_id
            ORDER BY 
                CASE i.estado 
                    WHEN 'DISPONIBLE' THEN 1
                    WHEN 'REINICIADO' THEN 2
                    WHEN 'CONFIGURADO' THEN 3
                    WHEN 'ENVIADO' THEN 4
                    ELSE 5
                END,
                i.fecha_ingreso DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def obtener_item_completo(item_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un item del inventario con todas sus configuraciones"""
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                i.id,
                i.producto_id,
                i.estado,
                i.fecha_ingreso,
                i.created_at,

                p.nombre AS producto_nombre,
                p.ref_prod,
                p.tipo,

                sc.id as sd_config_id,
                sc.config_final as sd_config_final,
                sc.fecha_configuracion as sd_fecha_configuracion,

                dc.id as disp_config_id,
                dc.fecha_config_inicio as disp_fecha_config_inicio,
                dc.fecha_config_final as disp_fecha_config_final,
                dc.fecha_finalizacion_accion as disp_fecha_accion
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            LEFT JOIN dispositivo_configuraciones dc ON i.id = dc.inventario_id
            WHERE i.id = ?
        """, (item_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None

def actualizar_item_completo(
    item_id: int,
    estado: Optional[str] = None,
    fecha_ingreso: Optional[date] = None,
    sd_config_final: Optional[date] = None,
    disp_fecha_config_inicio: Optional[date] = None,
    disp_fecha_config_final: Optional[date] = None
) -> bool:
    """
    Actualiza un item del inventario y sus configuraciones asociadas.
    Solo items no enviados pueden ser editados.
    """
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        # Verificar que el item existe y no está enviado
        cursor.execute("SELECT estado, producto_id FROM inventario WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            raise ValueError("El item no existe")
        
        if item['estado'] == 'ENVIADO':
            raise ValueError("No se puede modificar un item que ya ha sido enviado")
        
        # Obtener tipo de producto
        cursor.execute("SELECT tipo FROM productos WHERE id = ?", (item['producto_id'],))
        producto = cursor.fetchone()
        tipo = producto['tipo'] if producto else None
        
        # Actualizar inventario
        updates = []
        params = []
        
        if estado is not None:
            updates.append("estado = ?")
            params.append(estado)
        
        if fecha_ingreso is not None:
            # Validar que la fecha no sea futura
            if fecha_ingreso > datetime.now().date():
                raise ValueError("La fecha de ingreso no puede ser futura")
            updates.append("fecha_ingreso = ?")
            params.append(format_fecha(fecha_ingreso))
        
        if updates:
            params.append(item_id)
            cursor.execute(f"UPDATE inventario SET {', '.join(updates)} WHERE id = ?", params)
        
        # Actualizar configuración de SD si aplica
        if tipo == 'SD' and sd_config_final is not None:
            # Verificar si existe configuración
            cursor.execute("SELECT id FROM sd_configuraciones WHERE inventario_id = ?", (item_id,))
            config = cursor.fetchone()
            
            if config:
                cursor.execute("""
                    UPDATE sd_configuraciones 
                    SET config_final = ? 
                    WHERE inventario_id = ?
                """, (format_fecha(sd_config_final), item_id))
            else:
                # Si no existe pero se quiere poner fecha, crear registro
                cursor.execute("""
                    INSERT INTO sd_configuraciones (inventario_id, config_final, fecha_configuracion)
                    VALUES (?, ?, date('now'))
                """, (item_id, format_fecha(sd_config_final)))
        
        # Actualizar configuración de dispositivo si aplica
        if tipo == 'DISPOSITIVO':
            # Verificar si existe configuración
            cursor.execute("SELECT id FROM dispositivo_configuraciones WHERE inventario_id = ?", (item_id,))
            config = cursor.fetchone()
            
            if disp_fecha_config_inicio is not None or disp_fecha_config_final is not None:
                # Validar coherencia de fechas
                fecha_inicio = disp_fecha_config_inicio
                fecha_final = disp_fecha_config_final
                
                # Obtener fechas actuales si no se proporcionan
                if config:
                    if fecha_inicio is None:
                        cursor.execute("SELECT fecha_config_inicio FROM dispositivo_configuraciones WHERE inventario_id = ?", (item_id,))
                        fecha_inicio_row = cursor.fetchone()
                        fecha_inicio = fecha_inicio_row['fecha_config_inicio'] if fecha_inicio_row else None
                    
                    if fecha_final is None:
                        cursor.execute("SELECT fecha_config_final FROM dispositivo_configuraciones WHERE inventario_id = ?", (item_id,))
                        fecha_final_row = cursor.fetchone()
                        fecha_final = fecha_final_row['fecha_config_final'] if fecha_final_row else None
                
                # Validar que inicio no sea posterior a final
                if fecha_inicio and fecha_final:
                    # Convertir a date si son strings
                    if isinstance(fecha_inicio, str):
                        fecha_inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                    if isinstance(fecha_final, str):
                        fecha_final = datetime.strptime(fecha_final, "%Y-%m-%d").date()
                    
                    if fecha_inicio > fecha_final:
                        raise ValueError("La fecha de inicio no puede ser posterior a la fecha final")
                
                if config:
                    # Actualizar existente
                    updates_disp = []
                    params_disp = []
                    
                    if disp_fecha_config_inicio is not None:
                        updates_disp.append("fecha_config_inicio = ?")
                        params_disp.append(format_fecha(disp_fecha_config_inicio))
                    
                    if disp_fecha_config_final is not None:
                        updates_disp.append("fecha_config_final = ?")
                        params_disp.append(format_fecha(disp_fecha_config_final))
                        updates_disp.append("fecha_finalizacion_accion = CURRENT_TIMESTAMP")
                    
                    if updates_disp:
                        params_disp.append(item_id)
                        cursor.execute(f"""
                            UPDATE dispositivo_configuraciones 
                            SET {', '.join(updates_disp)} 
                            WHERE inventario_id = ?
                        """, params_disp)
                else:
                    # Crear nueva configuración solo si hay fechas
                    if disp_fecha_config_inicio:
                        cursor.execute("""
                            INSERT INTO dispositivo_configuraciones 
                            (inventario_id, fecha_config_inicio, fecha_config_final, fecha_finalizacion_accion)
                            VALUES (?, ?, ?, 
                                CASE WHEN ? IS NOT NULL THEN CURRENT_TIMESTAMP ELSE NULL END)
                        """, (
                            item_id, 
                            format_fecha(disp_fecha_config_inicio),
                            format_fecha(disp_fecha_config_final) if disp_fecha_config_final else None,
                            disp_fecha_config_final
                        ))
        
        conn.commit()
        return True

def marcar_como_defectuoso(item_id: int) -> bool:
    """
    Marca un item como defectuoso.
    Si tiene configuraciones, las elimina.
    """
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        # Verificar que el item existe y no está enviado
        cursor.execute("SELECT estado FROM inventario WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            raise ValueError("El item no existe")
        
        if item['estado'] == 'ENVIADO':
            raise ValueError("No se puede marcar como defectuoso un item ya enviado")
        
        # Eliminar configuraciones asociadas
        cursor.execute("DELETE FROM dispositivo_configuraciones WHERE inventario_id = ?", (item_id,))
        cursor.execute("DELETE FROM sd_configuraciones WHERE inventario_id = ?", (item_id,))
        
        # Cambiar estado
        cursor.execute("UPDATE inventario SET estado = 'DEFECTUOSO' WHERE id = ?", (item_id,))
        
        conn.commit()
        return True



def iniciar_configuracion_dispositivo(inventario_id: int, fecha_config_inicio) -> bool:
    """Inicia el proceso de configuración de un dispositivo"""
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        # Verificar que el item existe y es un dispositivo disponible
        cursor.execute("""
            SELECT i.*, p.tipo FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE i.id = ? AND i.estado = 'DISPONIBLE'
        """, (inventario_id,))
        
        item = cursor.fetchone()
        if not item:
            raise ValueError("El item no existe o no está disponible")
        
        if item['tipo'] != 'DISPOSITIVO':
            raise ValueError("Solo se pueden configurar dispositivos")
        
        # Verificar que no tenga ya una configuración iniciada
        cursor.execute("""
            SELECT id FROM dispositivo_configuraciones 
            WHERE inventario_id = ?
        """, (inventario_id,))
        
        if cursor.fetchone():
            raise ValueError("Este dispositivo ya tiene un proceso de configuración iniciado")
        
        # Registrar inicio de configuración y cambiar estado
        cursor.execute("""
            INSERT INTO dispositivo_configuraciones (inventario_id, fecha_config_inicio)
            VALUES (?, ?)
        """, (inventario_id, format_fecha(fecha_config_inicio)))
        
        cursor.execute("""
            UPDATE inventario SET estado = 'REINICIADO' WHERE id = ?
        """, (inventario_id,))
        
        return True

def finalizar_configuracion_dispositivo(inventario_id: int, fecha_config_final) -> bool:
    """Finaliza la configuración de un dispositivo"""
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        # Verificar que el dispositivo está en proceso de reinicio
        cursor.execute("""
            SELECT i.* FROM inventario i
            WHERE i.id = ? AND i.estado = 'REINICIADO'
        """, (inventario_id,))
        
        item = cursor.fetchone()
        if not item:
            raise ValueError("El dispositivo no está en proceso de reinicio")
        
        # Verificar que existe la configuración
        cursor.execute("""
            SELECT id FROM dispositivo_configuraciones 
            WHERE inventario_id = ? AND fecha_config_final IS NULL
        """, (inventario_id,))
        
        if not cursor.fetchone():
            raise ValueError("No hay una configuración activa para este dispositivo")
        
        # Actualizar configuración con fecha final y timestamp de acción
        cursor.execute("""
            UPDATE dispositivo_configuraciones 
            SET 
                fecha_config_final = ?,
                fecha_finalizacion_accion = CURRENT_TIMESTAMP
            WHERE inventario_id = ? AND fecha_config_final IS NULL
        """, (format_fecha(fecha_config_final), inventario_id))
        
        # Cambiar estado a configurado
        cursor.execute("""
            UPDATE inventario SET estado = 'CONFIGURADO' WHERE id = ?
        """, (inventario_id,))
        
        return True

def configurar_sd(inventario_id: int, config_final) -> bool:
    """Marca una SD como configurada"""
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        # Verificar que el item existe, es SD y está disponible
        cursor.execute("""
            SELECT i.*, p.tipo FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE i.id = ? AND i.estado = 'DISPONIBLE'
        """, (inventario_id,))
        
        item = cursor.fetchone()
        if not item:
            raise ValueError("La SD no existe o no está disponible")
        
        if item['tipo'] != 'SD':
            raise ValueError("Solo se pueden configurar tarjetas SD")
        
        # Verificar que no tenga ya una configuración
        cursor.execute("""
            SELECT id FROM sd_configuraciones 
            WHERE inventario_id = ?
        """, (inventario_id,))
        
        if cursor.fetchone():
            raise ValueError("Esta SD ya está configurada")
        
        # Registrar configuración
        cursor.execute("""
            INSERT INTO sd_configuraciones (inventario_id, config_final, fecha_configuracion)
            VALUES (?, ?, date('now'))
        """, (inventario_id, format_fecha(config_final)))
        
        # Cambiar estado
        cursor.execute("""
            UPDATE inventario SET estado = 'CONFIGURADO' WHERE id = ?
        """, (inventario_id,))
        
        return True

# ========== FUNCIONES PARA EDITAR/ELIMINAR EN INVENTARIO ==========
def eliminar_item_inventario(item_id: int) -> bool:
    """
    Elimina un item del inventario y sus configuraciones asociadas.
    Verifica todas las dependencias antes de eliminar.
    """
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        # Verificar que el item existe
        cursor.execute("SELECT estado FROM inventario WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        
        if not item:
            raise ValueError("El item no existe")
        
        # No permitir eliminar items enviados
        if item['estado'] == 'ENVIADO':
            raise ValueError("No se puede eliminar un item que ya ha sido enviado")
        
        # Verificar si está en envíos (dependencia crítica)
        cursor.execute("SELECT id FROM envio_detalle WHERE inventario_id = ?", (item_id,))
        if cursor.fetchone():
            raise ValueError("No se puede eliminar: el item está asociado a un envío")
        
        # Eliminar (las configuraciones se irán por CASCADE)
        cursor.execute("DELETE FROM inventario WHERE id = ?", (item_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        
        return deleted

# ========== PROCESAMIENTO DE ENVÍOS ==========
def procesar_envio(items: List[Dict[str, int]], folio: str, destino: str = "", 
                   descripcion: str = "", fecha_salida=None) -> Dict[str, Any]:
    """
    Procesa un envío a partir de una lista de items solicitados.
    items: lista de diccionarios con 'producto_id' y 'cantidad'
    """
    if not fecha_salida:
        fecha_salida = datetime.now().date()
    
    with get_connection(read_only=False) as conn:
        cursor = conn.cursor()
        
        inventario_ids = []
        items_procesados = []
        
        for req in items:
            producto_id = req['producto_id']
            cantidad_necesaria = req['cantidad']
            
            # Obtener items disponibles para envío (bloqueados por la transacción)
            cursor.execute("""
                SELECT i.id, p.tipo, p.nombre as producto_nombre,
                       dc.fecha_config_final as disp_fecha_final,
                       sc.config_final as sd_fecha_final
                FROM inventario i
                JOIN productos p ON i.producto_id = p.id
                LEFT JOIN dispositivo_configuraciones dc ON i.id = dc.inventario_id
                LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
                WHERE i.producto_id = ? 
                AND (
                    (p.tipo = 'DISPOSITIVO' AND i.estado = 'CONFIGURADO')
                    OR
                    (p.tipo = 'SD' AND i.estado = 'CONFIGURADO')
                    OR
                    (p.tipo IN ('CABLE_USB', 'CABLE_ETHERNET', 'CABLE_C') AND i.estado = 'DISPONIBLE')
                )
                ORDER BY i.fecha_ingreso ASC
                LIMIT ?
            """, (producto_id, cantidad_necesaria))
            
            disponibles = cursor.fetchall()
            
            if len(disponibles) < cantidad_necesaria:
                raise ValueError(
                    f"Stock insuficiente para {disponibles[0]['producto_nombre'] if disponibles else 'el producto'}. "
                    f"Requerido: {cantidad_necesaria}, Disponible: {len(disponibles)}"
                )
            
            # Validar fechas de configuración
            for item in disponibles:
                if item['tipo'] == 'DISPOSITIVO' and not item['disp_fecha_final']:
                    raise ValueError(
                        f"El dispositivo ID {item['id']} no tiene fecha de configuración final"
                    )
                
                if item['tipo'] == 'SD' and not item['sd_fecha_final']:
                    raise ValueError(
                        f"La SD ID {item['id']} no tiene fecha de configuración final"
                    )
                
                inventario_ids.append(item['id'])
                items_procesados.append({
                    'id': item['id'],
                    'tipo': item['tipo'],
                    'producto': item['producto_nombre']
                })
        
        # Crear el envío
        cursor.execute("""
            INSERT INTO envios (folio, fecha_salida, destino, descripcion)
            VALUES (?, ?, ?, ?)
        """, (folio, format_fecha(fecha_salida), destino, descripcion))
        envio_id = cursor.lastrowid
        
        # Marcar items como enviados y crear detalle
        for inventario_id in inventario_ids:
            cursor.execute("""
                UPDATE inventario SET estado = 'ENVIADO' WHERE id = ?
            """, (inventario_id,))
            
            cursor.execute("""
                INSERT INTO envio_detalle (envio_id, inventario_id)
                VALUES (?, ?)
            """, (envio_id, inventario_id))
        
        return {
            'envio_id': envio_id,
            'folio': folio,
            'items_procesados': len(inventario_ids),
            'detalle': items_procesados
        }

def get_envios() -> List[Dict[str, Any]]:
    """Obtiene todos los envíos realizados"""
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.*, COUNT(ed.id) as total_items
            FROM envios e
            LEFT JOIN envio_detalle ed ON e.id = ed.envio_id
            GROUP BY e.id
            ORDER BY e.fecha_salida DESC, e.id DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_detalle_envio(envio_id: int) -> List[Dict[str, Any]]:
    """Obtiene el detalle completo de un envío"""
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ed.*, i.estado,
                   p.nombre as producto_nombre, p.ref_prod, p.tipo,
                   sc.config_final as sd_config_final,
                   dc.fecha_config_final as disp_config_final
            FROM envio_detalle ed
            JOIN inventario i ON ed.inventario_id = i.id
            JOIN productos p ON i.producto_id = p.id
            LEFT JOIN sd_configuraciones sc ON i.id = sc.inventario_id
            LEFT JOIN dispositivo_configuraciones dc ON i.id = dc.inventario_id
            WHERE ed.envio_id = ?
        """, (envio_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_metricas() -> Dict[str, int]:
    """Obtiene métricas generales del inventario"""
    with get_connection(read_only=True) as conn:
        cursor = conn.cursor()
        metricas = {}
        
        # Total en inventario (no enviados)
        cursor.execute("SELECT COUNT(*) FROM inventario WHERE estado IN ('DISPONIBLE', 'REINICIADO', 'CONFIGURADO')")
        metricas['total_en_inventario'] = cursor.fetchone()[0]
        
        # Total de envíos
        cursor.execute("SELECT COUNT(*) FROM envios")
        metricas['total_envios'] = cursor.fetchone()[0]
        
        # SDs configuradas
        cursor.execute("""
            SELECT COUNT(*)
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE p.tipo = 'SD' AND i.estado = 'CONFIGURADO'
        """)
        metricas['sds_configuradas'] = cursor.fetchone()[0]
        
        # Dispositivos configurados
        cursor.execute("""
            SELECT COUNT(*)
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE p.tipo = 'DISPOSITIVO' AND i.estado = 'CONFIGURADO'
        """)
        metricas['dispositivos_configurados'] = cursor.fetchone()[0]
        
        # Dispositivos reiniciados
        cursor.execute("""
            SELECT COUNT(*)
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE p.tipo = 'DISPOSITIVO' AND i.estado = 'REINICIADO'
        """)
        metricas['dispositivos_reiniciados'] = cursor.fetchone()[0]
        
        # Dispositivos defectuosos (solo dispositivos)
        cursor.execute("""
            SELECT COUNT(*)
            FROM inventario i
            JOIN productos p ON i.producto_id = p.id
            WHERE p.tipo = 'DISPOSITIVO' AND i.estado = 'DEFECTUOSO'
        """)
        metricas['dispositivos_defectuosos'] = cursor.fetchone()[0]
        
        return metricas