import flet as ft

class AppBar():
    def __init__(self, bisnness_name=None, items = None, onChange = None, *args, **kwargs):
        self.bisnness_name = bisnness_name
        self.items = items
        self.onChange = onChange

    def build(self):
        # Índices de páginas
        PAGE_INICIO    = 0
        PAGE_ENTRADAS  = 1
        PAGE_IMPRESORA = 2  # Persistencia eliminada; se usa en memoria
        PAGE_USUARIOS  = 3
        PAGE_REGISTROS = 4
        i = []
        if self.items is not None:
            for item in self.items:
                i.append(
                    ft.PopupMenuItem(
                        text=item["text"],
                        on_click=item.get("on_click")  # Asegúrate de usar on_click
                    )
                )
        else:
            i = [
                    ft.PopupMenuItem(icon=ft.Icons.HOME,text="Inicio", on_click=lambda e: self.onChange(PAGE_ENTRADAS)),  # Cambiar a PAGE_ENTRADAS
                    ft.PopupMenuItem(icon=ft.Icons.DASHBOARD,text="Control", on_click=lambda e: self.onChange(PAGE_INICIO)),  # Cambiar a PAGE_INICIO
                    ft.PopupMenuItem(icon=ft.Icons.LIST,text="Registros", on_click=lambda e: self.onChange(PAGE_REGISTROS)),
                    ft.PopupMenuItem(icon=ft.Icons.PERSON,text="Usuarios", on_click=lambda e: self.onChange(PAGE_USUARIOS)),
                    ft.PopupMenuItem(icon=ft.Icons.SETTINGS,text="Configuraciones", on_click=lambda e: self.onChange(PAGE_IMPRESORA)),
                ]
            
        return ft.AppBar(
        leading=ft.Icon(ft.Icons.APP_REGISTRATION, size=30),
        leading_width=40,
        title=ft.Text("CONTROL DE COMEDOR" + self.bisnness_name if self.bisnness_name  is not None else "CONTROL DE COMEDOR", size=20, weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=[
            ft.PopupMenuButton(
                icon=ft.Icons.MENU,
                tooltip="Menú",
                items=i
            ),
        ],
    )
