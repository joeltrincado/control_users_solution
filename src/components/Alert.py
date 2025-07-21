import flet as ft

class Alert():
    def __init__(self, content, onAdd = None, onCancel = None, action = None, *args, **kwargs):
        self.content = content
        self.onAdd = onAdd
        self.onCancel = onCancel
        self.action = action
    def build(self):
        return ft.AlertDialog(
            content=self.content,
            actions=[
                ft.TextButton("Agregar" if self.action is None else self.action, on_click=self.onAdd),
                ft.TextButton("Cancelar" , on_click=self.onCancel),
            ],
            shape=ft.RoundedRectangleBorder(radius=10),
            )