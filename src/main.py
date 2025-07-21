import flet as ft
import pandas as pd
import json
import math
from datetime import datetime
from components.Container import Container
from components.AppBar import AppBar
from components.TextField import TextField
from components.Button import Button
from components.Users import Users
from components.Alert import Alert
from helpers.helpers import generate_qr_base64, getDatacell, getDataColumns, print_ticket_ethernet#, print_ticket_usb
from database import init_db, get_all_registros, insert_registro, get_all_users, delete_all_registros, get_user_by_code, add_user_from_excel, set_config, get_config, insert_user


def main(page: ft.Page):   
    init_db()
    current_tab = 0
    config = None
    users = []
    data_table = None
    current_page = 0
    page_size = 100  # usuarios por página
    # VARIABLES
    bisnness_name = "Corporación Tetronic"
    registers = get_all_registros()
    datacells = getDatacell(registers)
    columns = getDataColumns(["ID", "NOMBRE", "EMPRESA", "FECHA", "HORA"])

    
    # PAGE PROPIETIES
    page.title = "Control " + bisnness_name
    page.theme_mode = ft.ThemeMode.DARK

    # ONCHANGE & ONSUBMIT
    def onSubmitReadQr(e):
        nonlocal config
        config = get_config("impresora")
        config = json.loads(config)
        ip = config['ip']
        port = config['puerto']
        user = e.control.value
        search_user = get_user_by_code(user)
        if search_user is not None:
            insert_registro(search_user[0] ,search_user[1], search_user[1], search_user[2])
            date = datetime.now().strftime("%Y-%m-%d")
            time = datetime.now().strftime("%H:%M:%S")
            data = get_all_registros()
            datacells = getDatacell(data)
            registers_database.rows = datacells
            qr_user = generate_qr_base64(user)
            last_user.controls.clear()
            last_user.controls = [
                ft.Text("ÚLTIMO REGISTRO", size=26, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Row(
                    [
                    ft.Row(
                        [
                                ft.Icon(ft.Icons.PERSON, size=26),
                                ft.Text(search_user[1], size=26, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    ft.Row(
                        [
                            ft.Text(search_user[0], size=14),
                        ]
                    )
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Row(
                    [
                        ft.Text(search_user[2], size=16, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [
                                ft.Text(date, size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(time, size=16, weight=ft.FontWeight.BOLD),
                            ], height=50
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Container(
                    content=ft.Image(src_base64=qr_user, width=150, height=150),
                    alignment=ft.alignment.center
                )
                ]
            # if config["tipo"] == "USB":
            #     print_ticket_usb(printer_name=config["impresora"])
            # else:
            #     print_ticket_ethernet(ip=config["ip"], port=config["puerto"])
            # read_qr.focus()
            print_ticket_ethernet(ip=str(ip), port=port, user=search_user, date=date, time=time)
            read_qr.value = ""
            read_qr.focus()
        else:
            snack_bar = ft.SnackBar(ft.Text("Usuario no registrado. Ve a la pantalla de Usuarios para agregarlo."))
            read_qr.value = ""
            page.open(snack_bar)
            read_qr.focus()
        page.update()

    
    def show_page(index, callback=None):
    # Oculta todas
        for i, p in enumerate([page_0, page_1, page_2, page_3]):
            p.visible = (i == index)
            
        # Ejecuta la lógica especial para esa página (si se pasa)
        if callback:
            callback()

        page.update()

    def onChangePage(e):
        nonlocal current_tab, users
        current_tab = e

        match current_tab:
            case 0:
                show_page(0)
            case 1:
                def load_users():
                    nonlocal users
                    users = get_all_users()
                    if len(users) == 0:
                        page_1.controls = [
                            ft.Column(
                                controls=[
                                    ft.Row(
                                        [
                                            Button(
                                                text="CARGAR ARCHIVO",
                                                width=200,
                                                icon=ft.Icons.UPLOAD,
                                                on_click=lambda _: file_picker.pick_files(
                                                    allowed_extensions=["xlsx"],
                                                    allow_multiple=False
                                                )
                                            ).build()
                                        ],
                                        expand=True,
                                        alignment=ft.MainAxisAlignment.CENTER
                                    )
                                ],
                                expand=True,
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER
                            )
                        ]
                    else:
                        show_page(1, callback=view_page_1)
                show_page(1, callback=load_users)
            case 2:
                show_page(2, callback=load_config)

            case 3:
                show_page(3)


    #ONCLICK
    def upload_files(path):
        nonlocal users, data_table
        try:
            users_path = path.replace("\\", "/")
            add_user_from_excel(users_path)
            users = get_all_users()
            show_page(0)
            page.update()
            dt = Users(users[:page_size]).build()
            data_table = ft.DataTable(
                columns=[
                    ft.DataColumn(ft.Text("ID")),
                    ft.DataColumn(ft.Text("Nombre")),
                    ft.DataColumn(ft.Text("Empresa")),
                ],
                rows=dt.rows,
                expand=True,
            )

            page_text.value = f"Página 1 de {math.ceil(len(users)/page_size)}"
            snack_bar = ft.SnackBar(ft.Text("Usuarios cargados correctamente"))
            page.open(snack_bar)
            page.update()

        except Exception as e:
            print(e)
            snack_bar = ft.SnackBar(ft.Text(f"Error al cargar los usuarios: {users_path}"))
            page.open(snack_bar)

        page.update()

    def delete_registers(e):
        delete_all_registros()
        data = get_all_registros()
        datacells = getDatacell(data)
        registers_database.rows = datacells
        alert_delete_registers.open = False
        snack_bar = ft.SnackBar(ft.Text("Registros eliminados correctamente"))
        page.open(snack_bar)
        last_user.controls.clear()
        last_user.controls = [
            ft.Text("ÚLTIMO REGISTRO", size=26, weight=ft.FontWeight.BOLD),
        ]
        page.update()

    def openAlertRegisters(e):
        alert_delete_registers.open = True
        page.update()

    def closeAlertRegisters(e):
        alert_delete_registers.open = False
        page.update()


    import os

    def download_report_csv(e):

        plain_data = get_plain_data()
        columns = ["ID", "Nombre", "Empresa", "Fecha", "Hora"]
        df = pd.DataFrame(plain_data, columns=columns)

        try:
            
            df.to_csv(path_or_buf=f'/storage/emulated/0/Download/reporte.csv', index=False)
            snack_bar = ft.SnackBar(ft.Text(f"Reporte guardado en {os.getcwd()}"))
            page.open(snack_bar)
        except Exception as ex:
            snack_bar = ft.SnackBar(ft.Text("Error al guardar el reporte: " + str(ex)))
            page.open(snack_bar)
        page.update()

    #FUCTIONS
    def get_plain_data():
        registros = get_all_registros()
        return [
            [r[0], r[1], r[2], r[3], r[4]]
            for r in registros
        ]
    
    def update_table():
        start = current_page * page_size
        end = start + page_size
        visible_users = users[start:end]
        data_table.rows = Users(visible_users).build().rows
        page_text.value = f"Página {current_page + 1} de {math.ceil(len(users)/page_size)}"
        page.update()
        page.scroll_to(offset=0)

    def go_next(e):
        nonlocal current_page
        if (current_page + 1) * page_size < len(users):
            current_page += 1
            update_table()

    def go_prev(e):
        nonlocal current_page
        if current_page > 0:
            current_page -= 1
            update_table()

    def view_page_1():
        nonlocal users, data_table, current_page
        users = users  # ya los cargaste en load_users
        current_page = 0

        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Nombre")),
                ft.DataColumn(ft.Text("Empresa")),
            ],
            rows=[], expand=True
        )

        update_table()  # carga la primera página

        page_1.controls.clear()
        page_1.controls = [
            ft.Column([
                ft.Row([
                    Button(
                        text="ACTUALIZAR USUARIOS",
                        icon=ft.Icons.UPLOAD,
                        on_click=lambda _: file_picker.pick_files(
                            allowed_extensions=["xlsx"],
                            allow_multiple=False,
                        ),
                            width=150
                    ).build(),
                    Button(
                        text="AGREGAR USUARIO",
                        icon=ft.Icons.ADD,
                        bgcolor=ft.Colors.GREEN_400,
                        color=ft.Colors.WHITE,
                        on_click=lambda _: openAlertUser(),
                        width=150
                    ).build()
                ], alignment=ft.MainAxisAlignment.END),
                ft.Container(
                    content=ft.Column([
                        ft.Row([data_table,], expand=True),
                        ft.Row([
                        ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=go_prev),
                        page_text,
                        ft.IconButton(icon=ft.icons.ARROW_FORWARD, on_click=go_next),
                    ], alignment=ft.MainAxisAlignment.CENTER)
                    ], expand=True, scroll=ft.ScrollMode.ALWAYS),
                    expand=True
                )
            ], expand=True)
        ]


    def onCloseAlertUser(e):
        alert_user.open = False
        page.update()

    def onAddUser(e):
        alert_user.open = False
        codigo = codigo_field.value
        name = name_field.value
        company = company_field.value

        duplicate = get_user_by_code(codigo)
        if duplicate:
            codigo_field.value = ""
            name_field.value = ""
            company_field.value = ""
            page.open(ft.SnackBar(ft.Text("El usuario ya existe")))
            page.update()
            return

        insert_user(codigo, name, company)
        codigo_field.value = ""
        name_field.value = ""
        company_field.value = ""
        page.open(ft.SnackBar(ft.Text("Usuario agregado correctamente")))
        show_page(0)
        page.update()


    def openAlertUser():
        page.open(alert_user)
        page.update()
    
    def get_usb_printers():
            try:
                import win32print
                return [printer[2] for printer in win32print.EnumPrinters(2)]
            except:
                return []

    def toggle_config_mode():
        if modo_impresora.value == "USB":
            usb_selector.visible = True
            ip_field.visible = False
            port_field.visible = False
        else:
            usb_selector.visible = False
            ip_field.visible = True
            port_field.visible = True
        page.update()

    def guardar_configuracion(e):
        nonlocal config
        if modo_impresora.value == "USB":
            config = {
                "tipo": "USB",
                "impresora": usb_selector.value
            }
        else:
            config = {
                "tipo": "Ethernet",
                "ip": ip_field.value,
                "puerto": port_field.value
            }
        set_config("impresora", json.dumps(config))  # Serializa a JSON
        show_page(0)
        page.open(ft.SnackBar(ft.Text("Configuración guardada")))

    def load_config():
        try:
            config_json = get_config("impresora")
            if config_json:
                config = json.loads(config_json)
                if config["tipo"] == "USB":
                    modo_impresora.value = "USB"
                    usb_selector.value = config.get("impresora", None)
                elif config["tipo"] == "Ethernet":
                    modo_impresora.value = "Ethernet"
                    ip_field.value = config.get("ip", "")
                    port_field.value = config.get("puerto", "9100")
                toggle_config_mode()
        except Exception as e:
            print(f"Error al cargar configuración: {e}")


    # page_0
    read_qr = TextField(label="Leer QR", onSubmit=onSubmitReadQr, keyboard_type=ft.KeyboardType.NUMBER).build()
    download_report = Button(text="DESCARGAR REPORTE", on_click=download_report_csv).build()
    delete_registers_button = Button(text="BORRAR REGISTROS", on_click=openAlertRegisters, bgcolor=ft.Colors.RED_400, icon=ft.Icons.DELETE).build()
    alert_delete_registers = Alert(content=ft.Text("Seguro que desea borrar los registros?"), action="Borrar", onAdd=delete_registers, onCancel=closeAlertRegisters).build()
    alert_delete_registers.open = False
    content_data = ft.Column(
        [
            ft.Row(
                [
                    read_qr
                ], height=50
            ),
            download_report,
            delete_registers_button,
            alert_delete_registers
        ], alignment=ft.MainAxisAlignment.START
    )
    last_user = ft.Column(
        [
            ft.Text("ÚLTIMO REGISTRO", size=26, weight=ft.FontWeight.BOLD),
        ]
    )
    registers_database = ft.DataTable(
    columns= columns,
    rows=datacells,
    expand=True,


)   
    page_0 = ft.Row(
        [
            ft.Column(
                [
                    Container(height=200, business_name=bisnness_name, content=content_data).build(),
                    Container(business_name=bisnness_name, content=last_user).build(),
                ], width=450
            ),
            ft.Column(
                [
                     Container(business_name=bisnness_name, content=ft.Row(
                         [
                             registers_database
                         ], expand=True
                     )).build(),
                ], expand=True
            ),

        ], expand=True
    )

    # page_1
    file_picker = ft.FilePicker(
    on_result=lambda e: upload_files(e.files[0].path)) 
    page.overlay.append(file_picker) 
    codigo_field = TextField(label="Código", keyboard_type=ft.KeyboardType.NUMBER).build()
    name_field = TextField(label="Nombre").build()
    company_field = TextField(label="Empresa").build()
    page_text = ft.Text("", size=16)

    alert_user = Alert(content=ft.Column(
        [
            codigo_field,
            name_field,
            company_field
        ], expand=True, height=200, width=300
    )
                       , onCancel=onCloseAlertUser, onAdd=onAddUser).build()
    page_1 = ft.Row(
       controls= [], expand=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER
    )
    page_1.visible = False

    # page_2: Configuración de impresora
    modo_impresora = ft.Dropdown(
        label="Tipo de conexión",
        options=[
            #ft.dropdown.Option("USB"),
            ft.dropdown.Option("Ethernet")
        ],
        value="Ethernet",  # por defecto
        width=300,
        on_change=lambda e: toggle_config_mode(),
        border_color=ft.Colors.WHITE
    )

    usb_selector = ft.Dropdown(
        label="Impresoras USB",
        options=[ft.dropdown.Option(p) for p in get_usb_printers()],
        width=300, border_color=ft.Colors.WHITE,
    )

    ip_field = TextField(label="Dirección IP", width=300, keyboard_type=ft.KeyboardType.NUMBER).build()
    port_field = TextField(label="Puerto", width=300, value="9100", keyboard_type=ft.KeyboardType.NUMBER).build()

    config_container = Container(
        business_name=bisnness_name,
        content=ft.Column(
            [
                ft.Text("CONFIGURACIÓN DE IMPRESORA", size=26, weight=ft.FontWeight.BOLD),
                modo_impresora,
                usb_selector,
                ip_field,
                port_field,
                ft.Row(
                    [
                        Button(text="GUARDAR", on_click=guardar_configuracion, icon=ft.Icons.SAVE, width=300).build(),
                    ], expand=True, alignment=ft.MainAxisAlignment.CENTER
                ),
            ],
            spacing=20, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        height=400,
    ).build()

    page_2 = ft.Row(
        [
            ft.Column(
                [config_container],
                expand=True,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        ],
        expand=True
    )

    page_2.visible = False
    page_3 = ft.Row(
      
    )
    page_3.visible = False
    # APPBAR
    toggle_config_mode()
    page.appbar = AppBar(bisnness_name=bisnness_name, onChange=onChangePage).build()
    page.add(
        ft.SafeArea(
            ft.Column(
                [
                    page_0,
                    page_1,
                    page_2,
                    page_3
                ], expand=True
            ), expand=True
        )
    )
    
    read_qr.focus()
ft.app(main)
