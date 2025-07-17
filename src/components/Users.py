import flet as ft

class Users():
    def __init__(self, users=None):
        self.users = users
        self.rows = []

    def generate_rows(self):
        rows = []
        for items in self.users:
            rows.append( ft.DataRow(cells=[
                ft.DataCell(ft.Text(str(items[0]))),  # id
                ft.DataCell(ft.Text(items[1])),       # nombre
                ft.DataCell(ft.Text(items[2])),       # empresa
            ])
            )
        return rows


    def build(self):
        self.rows = self.generate_rows()
        return ft.DataTable(columns=[
            ft.DataColumn(label=ft.Text("CÓDIGO")),
            ft.DataColumn(label=ft.Text("NOMBRE")),
            ft.DataColumn(label=ft.Text("EMPRESA")),
        ], rows=self.rows, expand=True)