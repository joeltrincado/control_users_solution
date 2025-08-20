import flet as ft

def getDatacell(data=None):
    """
    data rows (entradas):
    [id, codigo, hora_entrada, fecha_entrada, hora_salida, fecha_salida, type_entry, precio, status]
    """
    if not data:
        return []
    return [
        ft.DataRow(cells=[
                ft.DataCell(ft.Text(value=row[0], selectable=True)),  # Código
                ft.DataCell(ft.Text(value=row[1], selectable=True)),  # Nombre
                ft.DataCell(ft.Text(value=row[2], selectable=True)),  # Empresa
                ft.DataCell(ft.Text(value=row[3], selectable=True)),  # Hora de entrada
                ft.DataCell(ft.Text(value=row[4], selectable=True)),  # Fecha de entrada
            ])
        for row in data
    ]


def getDataColumns(data=None):
    if not data:
        return []
    return [ft.DataColumn(label=ft.Text(col)) for col in data]


def print_ticket_usb(printer_name=None, data=None, error=None, err_printer=None, entrada=True):
    """
    Impresión ESC/POS (USB) para boleto de COMEDOR.
    - Solo se usa 'entrada=True' (no hay salidas en comedor).
    Campos esperados en data:
      - titulo (str), codigo (str), fecha_entrada (str), hora_entrada (str),
        tipo (str), precio (str)  -> p.ej. "25.00 MXN"
    """
    import win32print
    import struct

    if data is None:
        data = {}

    ESC = b"\x1b"
    GS  = b"\x1d"

    def init():
        return bytearray(ESC + b"@" + ESC + b"t" + bytes([16]))  # CP1252

    def align(n: int):
        return ESC + b"a" + bytes([n])  # 0=left,1=center,2=right

    def font(n: int):
        return ESC + b"M" + bytes([n])  # 0=A, 1=B

    def bold(on: bool):
        return ESC + b"E" + (b"\x01" if on else b"\x00")

    def size(w=1, h=1):
        n = (max(1, min(8, h)) - 1) * 16 + (max(1, min(8, w)) - 1)
        return GS + b"!" + bytes([n])

    def feed(n: int = 1):
        return b"\n" * max(0, n)

    def cut(partial: bool = True):
        return GS + b"V" + (b"\x42" if partial else b"\x41") + b"\x00"

    def txt(s: str):
        return s.encode("cp1252", errors="replace")

    def rule(cols: int = 42, ch: str = "-"):
        return txt(ch * cols) + b"\n"

    def kv_line(left: str, right: str, cols: int = 42):
        left = left.strip()
        right = right.strip()
        space = max(1, cols - len(left) - len(right))
        return txt(left + (" " * space) + right) + b"\n"

    def qr_bytes(payload: str, size_mod: int = 6, ec: str = "M"):
        ec_map = {"L": 48, "M": 49, "Q": 50, "H": 51}
        ec_v = ec_map.get(ec.upper(), 49)
        data_b = payload.encode("utf-8")

        b = bytearray()
        # Model 2
        b += GS + b"(k" + struct.pack("<H", 4) + b"\x31\x41\x32\x00"
        # Tamaño módulo
        b += GS + b"(k" + struct.pack("<H", 3) + b"\x31\x43" + bytes([max(1, min(16, size_mod))])
        # ECC
        b += GS + b"(k" + struct.pack("<H", 3) + b"\x31\x45" + bytes([ec_v])
        # Store data
        b += GS + b"(k" + struct.pack("<H", len(data_b) + 3) + b"\x31\x50\x30" + data_b
        # Print
        b += GS + b"(k" + struct.pack("<H", 3) + b"\x31\x51\x30"
        return b

    # --- Construcción del ticket ---
    buf = init()

    title = str(data.get("titulo", "Boleto de Comedor"))
    buf += align(1) + bold(True) + size(2, 2) + txt(title) + feed(1)
    buf += bold(False) + size(1, 1)

    # Datos
    fecha_legible = str(data.get("fecha_entrada", ""))
    hora = str(data.get("hora_entrada", ""))
    tipo = str(data.get("tipo", ""))
    precio = str(data.get("precio", ""))  # "XX.XX MXN"
    codigo = str(data.get("codigo", "")).strip()

    # Cabecera
    buf += align(1) + txt(fecha_legible) + feed(1)
    buf += align(0) + kv_line("Hora:", hora)
    if tipo:
        buf += kv_line("Tipo de usuario:", tipo)
    if precio:
        buf += kv_line("Tarifa aplicada:", precio)
    buf += rule()

    # QR (payload: código)
    if codigo:
        buf += align(1) + qr_bytes(f"{codigo}", size_mod=6, ec="M") + feed(1)
        buf += align(1) + txt(f"Código: {codigo}") + feed(1)

    # Leyenda breve (comedor)
    buf += font(1)
    for line in [
        "Válido únicamente para el día y horario indicado.",
        "Personal no transferible. Conserve su ticket.",
    ]:
        buf += txt(line) + b"\n"
    buf += font(0) + rule()

    # Cierre
    buf += align(1) + txt("¡Buen provecho!") + feed(3)
    buf += cut(partial=True)

    if printer_name:
        try:
            h = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(h, 1, ("Ticket Comedor ESC/POS", None, "RAW"))
                win32print.StartPagePrinter(h)
                win32print.WritePrinter(h, bytes(buf))
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
            finally:
                win32print.ClosePrinter(h)
        except Exception as e:
            return error if error else print("Error al imprimir:", e)
    else:
        return err_printer if err_printer else print("No se ha seleccionado una impresora")
