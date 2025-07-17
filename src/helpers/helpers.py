import qrcode
from PIL import Image
import io
import base64
import flet as ft

def generate_qr_base64(data=None):
    # Generar el QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    # Si quieres un margen extra:
    background = Image.new("RGB", (qr_img.width + 20, qr_img.height + 20), (255, 255, 255))
    background.paste(qr_img, (10, 10))

    # Convertir a buffer
    buffered = io.BytesIO()
    background.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()

    # Codificar a base64
    img_base64 = base64.b64encode(img_bytes).decode()

    # Retornar el Data URI
    return img_base64

def getDatacell(data=None):
    users = []
    for user in data:
        users.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(user[0]))),  # id
                ft.DataCell(ft.Text(user[1])),       # nombre
                ft.DataCell(ft.Text(user[5])),       # empresa
                ft.DataCell(ft.Text(user[3])),       # fecha
                ft.DataCell(ft.Text(user[4])),       # hora
            ])
        )
    return users

def getDataColumns(data=None):
    columns = []
    for d in data:
        columns.append(ft.DataColumn(label=ft.Text(d,)))
    return columns




