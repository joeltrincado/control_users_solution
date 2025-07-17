import sqlite3
from datetime import datetime
import pandas as pd
import json

def create_connection():
    conn = sqlite3.connect("visitas.db")
    return conn

def init_db():
    conn = create_connection()
    cursor = conn.cursor()

    # Tabla de registros
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            fecha_entrada TEXT NOT NULL,
            hora_entrada TEXT NOT NULL,
            empresa TEXT NOT NULL
        )
    """)

    # Tabla de usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            codigo TEXT PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            empresa TEXT NOT NULL
        )
    """)

    # Tabla de configuraciones
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuraciones (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    conn.commit()
    conn.close()


def insert_registro(nombre, apellido, empresa):
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    hora_actual = datetime.now().strftime("%H:%M:%S")
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO registros (nombre, apellido, fecha_entrada, hora_entrada, empresa)
        VALUES (?, ?, ?, ?, ?)
    """, (nombre, apellido, fecha_actual, hora_actual, empresa))
    conn.commit()
    conn.close()

def get_all_registros():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM registros ORDER BY fecha_entrada ASC, hora_entrada ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def insert_user(codigo, nombre_completo, empresa):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO usuarios (codigo, nombre_completo, empresa)
        VALUES (?, ?, ?)
    """, (codigo, nombre_completo, empresa))
    conn.commit()
    conn.close()

def get_all_users():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios ORDER BY nombre_completo ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_user_from_excel(path_excel):
    """
    path_excel: ruta al archivo Excel.
    El Excel debe tener columnas: Código, Nombre, Empresa
    """
    df = pd.read_excel(path_excel)

    conn = create_connection()
    cursor = conn.cursor()

    # Borra todos los usuarios anteriores
    cursor.execute("DELETE FROM usuarios")

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO usuarios (codigo, nombre_completo, empresa)
            VALUES (?, ?, ?)
        """, (
            str(row['Código']).strip(),
            str(row['Nombre']).strip(),
            str(row['Empresa']).strip()
        ))

    conn.commit()
    conn.close()


def get_config(clave):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT valor FROM configuraciones WHERE clave=?", (clave,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_config(clave, valor):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO configuraciones (clave, valor)
        VALUES (?, ?)
        ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor
    """, (clave, valor))
    conn.commit()
    conn.close()

def get_user_by_code(code):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE codigo=?", (code,))
    row = cursor.fetchone()
    conn.close()
    return row


