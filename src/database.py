import sqlite3
import datetime

def create_connection():
    return sqlite3.connect("visitas.db")

def init_db():
    with create_connection() as conn:
        c = conn.cursor()

        # Eliminar la tabla de entradas (opcional: solo si puedes perder los datos)
        c.execute("DROP TABLE IF EXISTS entradas")

        # Crear la nueva tabla con solo las columnas necesarias
        c.execute("""
            CREATE TABLE IF NOT EXISTS entradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                empresa TEXT NOT NULL,
                hora_entrada TEXT NOT NULL,
                fecha_entrada TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_codigo_entrada ON entradas(codigo)")

        # Crear el resto de las tablas necesarias
        c.execute(""" 
            CREATE TABLE IF NOT EXISTS configuraciones (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                empresa TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_empresa ON users(empresa)")

        # Nuevos registros para el histórico de accesos
        c.execute("""
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                empresa TEXT NOT NULL,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL
            )
        """)

        # Valores por defecto (opcional)
        c.execute("INSERT OR IGNORE INTO configuraciones (clave, valor) VALUES ('cajones_normales','19')")
        conn.commit()



# --------- ENTRADAS (helpers que usas en main) ---------
def get_all_entries():
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT codigo, nombre, empresa, hora_entrada, fecha_entrada FROM entradas")
        return c.fetchall()



def insert_entry(codigo, nombre, empresa, hora_entrada, fecha_entrada):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO entradas (codigo, nombre, empresa, hora_entrada, fecha_entrada)
            VALUES (?, ?, ?, ?, ?)
        """, (codigo, nombre, empresa, hora_entrada, fecha_entrada))
        conn.commit()



def delete_all_entries():
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM entradas")
        conn.commit()

# --------- USERS ---------
def get_user_by_code(codigo: str):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT codigo, nombre, empresa FROM users WHERE codigo=?", (codigo,))
        return c.fetchone()  # (codigo, nombre, empresa) o None

def insert_user(codigo: str, nombre: str, empresa: str):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO users (codigo, nombre, empresa)
            VALUES (?, ?, ?)
        """, (codigo, nombre, empresa))
        conn.commit()

# (Opcional) si quieres listarlos:
def get_all_users():
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT codigo, nombre, empresa FROM users")
        return c.fetchall()

# --------- REGISTROS (para tu vista paginada) ---------
def get_all_registros():
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, nombre, empresa, fecha, hora FROM registros ORDER BY id DESC")
        return c.fetchall()

def insert_registro(nombre: str, empresa: str, fecha: str, hora: str):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO registros (nombre, empresa, fecha, hora)
            VALUES (?, ?, ?, ?)
        """, (nombre, empresa, fecha, hora))
        conn.commit()

def delete_all_registros():
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM registros")
        conn.commit()

# --------- CONFIG / PRECIOS ---------
def get_config(clave):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT valor FROM configuraciones WHERE clave=?", (clave,))
        row = c.fetchone()
        return row[0] if row else None

def set_config(clave, valor):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO configuraciones (clave, valor) VALUES (?, ?)
            ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor
        """, (clave, valor))
        conn.commit()

def get_price_by_type(tipo):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT nombre, precio FROM prices WHERE tipo=?", (tipo,))
        row = c.fetchone()
        return row if row else ("", 0.0)

# Ajusta esta firma según cómo la llames desde main.py (aquí: 3 precios)
def set_all_prices(precio_empleado: float, precio_estudiante: float, precio_visitante: float):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO prices (nombre, precio, tipo) VALUES ('Tarifa empleado', ?, 'empleado')
            ON CONFLICT(tipo) DO UPDATE SET precio=excluded.precio, nombre=excluded.nombre
        """, (precio_empleado,))
        c.execute("""
            INSERT INTO prices (nombre, precio, tipo) VALUES ('Tarifa estudiante', ?, 'estudiante')
            ON CONFLICT(tipo) DO UPDATE SET precio=excluded.precio, nombre=excluded.nombre
        """, (precio_estudiante,))
        c.execute("""
            INSERT INTO prices (nombre, precio, tipo) VALUES ('Tarifa visitante', ?, 'visitante')
            ON CONFLICT(tipo) DO UPDATE SET precio=excluded.precio, nombre=excluded.nombre
        """, (precio_visitante,))
        conn.commit()


def get_price_by_type(tipo: str):
    """tipo: 'empleado' | 'estudiante' | 'visitante' (minúsculas)"""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT tipo, precio FROM prices WHERE tipo=?", (tipo,))
        row = c.fetchone()
        if row:
            return row[0], float(row[1] or 0.0)
        return tipo, 0.0

# === FUNCIONES NUEVAS (pégalas en cualquier parte de database.py) ===

def insert_user(codigo: str, nombre: str, empresa: str):
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO users (codigo, nombre, empresa)
            VALUES (?, ?, ?)
        """, (codigo, nombre, empresa))
        conn.commit()


def get_user_by_code(codigo: str):
    """Devuelve (codigo, nombre, empresa) o None."""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT codigo, nombre, empresa FROM users WHERE codigo=?", (codigo,))
        return c.fetchone()

def get_all_registros():
    """Devuelve lista de filas: [id, nombre, empresa, fecha, hora]"""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, nombre, empresa, fecha, hora FROM registros ORDER BY id DESC")
        return c.fetchall()

def insert_registro(nombre: str, empresa: str, fecha: str | None = None, hora: str | None = None):
    """Inserta un registro manual (por si te sirve después)."""
    try:
        if not fecha or not hora:
            now = datetime.now()
            fecha = fecha or now.strftime("%Y-%m-%d")
            hora = hora or now.strftime("%H:%M:%S")
        with create_connection() as conn:
            c = conn.cursor()
            c.execute(
                "INSERT INTO registros (nombre, empresa, fecha, hora) VALUES (?, ?, ?, ?)",
                (nombre.strip(), empresa.strip(), fecha, hora)
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"[DB] Error insert_registro: {e}")

def delete_all_registros():
    """Borra todos los registros."""
    try:
        with create_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM registros")
            conn.commit()
    except sqlite3.Error as e:
        print(f"[DB] Error delete_all_registros: {e}")
