import flet as ft
import pandas as pd
from components.Container import Container
from components.AppBar import AppBar
from components.TextField import TextField
from components.Button import Button
from components.Users import Users
from helpers.helpers import generate_qr_base64, getDatacell, getDataColumns
from database import init_db, get_all_registros, insert_registro, get_all_users, add_user_from_excel


def main(page: ft.Page):
    init_db()
    page_ = ""
    users = []
    # VARIABLES
    bisnness_name = "Corporación Tetronic"
    user = {
        "id": 1321,
        "name": "Joel Trincado",
        "company": "Corporación Tetronic",
        "date": "01/01/2022",
        "time": "00:00:00"
    }
    registers = get_all_registros()
    datacells = getDatacell(registers)
    columns = getDataColumns(["ID", "nombre", "EMPRESA", "FECHA", "HORA"])

    
    # PAGE PROPIETIES
    page.title = "Control " + bisnness_name
    page.theme_mode = ft.ThemeMode.DARK

    # ONCHANGE
    def onChangeReadQr(e):
        user = {
        "id": 1322,
        "name": "Joel Trincadoo",
        "company": "Corporación Tetronic",
        "date": "01/01/2022",
        "time": "00:00:00"
    }
        insert_registro(user["name"], user["name"], user["company"])
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
                            ft.Text(user["name"], size=26, weight=ft.FontWeight.BOLD),
                       ]
                   ),
                   ft.Row(
                       [
                           ft.Text(user["id"], size=14),
                       ]
                   )
                ], vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Row(
                [
                    ft.Text(user["company"], size=16, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.Text(user["date"], size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(user["time"], size=16, weight=ft.FontWeight.BOLD),
                        ], height=50
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Container(
                content=ft.Image(src_base64=qr_user, width=150, height=150),
                alignment=ft.alignment.center
            )
            ]
        read_qr.value = ""
        read_qr.focus()
        page.update()

    def onChangePage(e):
        nonlocal page_, users
        page_ = e
        match page_:
            case 0:
                page_0. visible = True
                page_1. visible = False
                page_2. visible = False
                page_3. visible = False
            case 1:
                page_0. visible = False
                page_1. visible = True
                page_2. visible = False
                page_3. visible = False
                users = get_all_users()
                if len(users) == 0:
                    page_1.controls = [
                        ft.Column(controls=[
                        ft.Row(
                            [Button(text="CARGAR ARCHIVO", width=200, icon=ft.Icons.UPLOAD, 
                                    on_click=lambda _: file_picker.pick_files(
                    allowed_extensions=["xlsx"],
                    allow_multiple=False
                )
                                    ).build()], expand=True, alignment=ft.MainAxisAlignment.CENTER
                        )
                    ], expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                ]
                else:
                    view_page_1()
            case 2:
                page_0. visible = False
                page_1. visible = False
                page_2. visible = True
                page_3. visible = False
            case 3:
                page_0. visible = False
                page_1. visible = False
                page_2. visible = False
                page_3. visible = True
        page.update()

    #ONCLICK
    def upload_files(path):
        nonlocal users
        try:
            users_path = path.replace("\\", "/")
            add_user_from_excel(users_path)
            snack_bar = ft.SnackBar(ft.Text("Usuarios cargados correctamente"))
            users = get_all_users()
            view_page_1()

            page.open(snack_bar)
        except Exception as e:
            print(e)
            snack_bar = ft.SnackBar(ft.Text("Error al cargar los usuarios"))
            page.open(snack_bar)
        page.update()
    

    #FUCTIONS
    def view_page_1():
        data = Users(users).build()
        page_1.controls.clear()
        page_1.controls = [
                ft.Column(
                    [
                        ft.Row(
                            [
                                Button(text="ACTUALIZAR USUARIOS", icon=ft.Icons.UPLOAD, 
                                        on_click=lambda _: file_picker.pick_files(
                            allowed_extensions=["xlsx"],
                            allow_multiple=False
                        )).build(),
                            ],
                            alignment=ft.MainAxisAlignment.END
                        ),
                        ft.Row(
                            [data],
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.START,
                            expand=True
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    expand=True
                )
            ]



    # page_0
    read_qr = TextField(label="Leer QR", onSubmit=onChangeReadQr).build()
    download_report = Button(text="DESCARGAR REPORTE").build()
    content_data = ft.Column(
        [
            ft.Row(
                [
                    read_qr
                ], height=50
            ),
            download_report
        ], alignment=ft.MainAxisAlignment.START
    )
    last_user = ft.Column(
        [
            ft.Text("ÚLTIMO REGISTRO", size=26, weight=ft.FontWeight.BOLD),
        ]
    )
    registers_database = registers_database = ft.DataTable(
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
                ], width=400
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
    
    page_1 = ft.Row(
       controls= [], expand=True, vertical_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER
    )
    page_1.visible = False
    page_2 = ft.Row(
      
    )
    page_2.visible = False
    page_3 = ft.Row(
      
    )
    page_3.visible = False
    # APPBAR
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
