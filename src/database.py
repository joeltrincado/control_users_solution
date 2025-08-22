import sqlite3
import datetime

def create_connection():
    return sqlite3.connect("visitas.db")

def init_db():
    with create_connection() as conn:
        c = conn.cursor()
        
        # Crear la nueva tabla con solo las columnas necesarias para los registros
        c.execute(""" 
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                empresa TEXT NOT NULL,
                hora_entrada TEXT NOT NULL,
                fecha_entrada TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_codigo_entrada ON registros(codigo)")

        # Crear la tabla de usuarios
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                codigo TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                empresa TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_empresa ON users(empresa)")

        # Crear la tabla de configuraciones
        c.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave TEXT NOT NULL UNIQUE,
                value TEXT NOT NULL
            )
        """)
        conn.commit()




# --------- REGISTROS (helpers que usas en main) ---------
def get_all_registros():
    """Devuelve todos los registros de la base de datos."""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id, codigo, nombre, empresa, hora_entrada, fecha_entrada FROM registros ORDER BY id DESC")
        return c.fetchall()

def insert_registro(codigo, nombre, empresa, hora_entrada, fecha_entrada):
    """Inserta un nuevo registro en la base de datos."""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute(""" 
            INSERT INTO registros (codigo, nombre, empresa, hora_entrada, fecha_entrada)
            VALUES (?, ?, ?, ?, ?)
        """, (codigo, nombre, empresa, hora_entrada, fecha_entrada))
        conn.commit()  # Asegúrate de hacer commit


def delete_all_registros():
    """Elimina todos los registros de la base de datos."""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM registros")
        conn.commit()


# --------- USERS ---------
def get_user_by_code(codigo: str):
    """Devuelve el usuario por código o None si no existe."""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT codigo, nombre, empresa FROM users WHERE codigo=?", (codigo,))
        return c.fetchone()

def insert_user(codigo: str, nombre: str, empresa: str):
    """Inserta un nuevo usuario en la base de datos."""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO users (codigo, nombre, empresa)
            VALUES (?, ?, ?)
        """, (codigo, nombre, empresa))
        conn.commit()

def get_all_users():
    """Devuelve todos los usuarios registrados."""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT codigo, nombre, empresa FROM users")
        return c.fetchall()

def set_config(clave, valor):
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO configuracion (clave, value)
                VALUES (?, ?)
                ON CONFLICT(clave) DO UPDATE SET value=excluded.value
            """, (clave, valor))
            conn.commit()
    except sqlite3.Error as e:
        print(f"[DB] Error set_config: {e}")


def get_config(clave):
    """Devuelve el valor de la clave de configuración (como 'printer_name')."""
    try:
        with create_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT value FROM configuracion WHERE clave = ?", (clave,))
            result = c.fetchone()
            return result[0] if result else None  # Retorna el valor si existe, o None si no se encuentra
    except sqlite3.Error as e:
        print(f"[DB] Error get_config: {e}")
        return None

def delete_empleado(codigo: str):
    """Elimina un empleado de la base de datos por su código"""
    with create_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE codigo=?", (codigo,))
        conn.commit()