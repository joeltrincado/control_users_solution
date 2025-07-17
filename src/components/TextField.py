import flet as ft

class TextField():
    def __init__(self,label = None, onChange = None, onSubmit = None, value = None, width = None, *args, **kwargs):
        self.label = label
        self.onChange = onChange
        self.onSubmit = onSubmit
        self.value = value
        self.width = width

    def focus(self):
        self.build().focus()

    def build(self):
        return ft.TextField(
            label=self.label if self.label is not None else None,
            
            value=self.value if self.value is not None else None,
            on_change=self.onChange if self.onChange is not None else None,
            on_submit=self.onSubmit if self.onSubmit is not None else None,
            expand=True,
            border_radius=10,
            color=ft.Colors.WHITE,
            border_color=ft.Colors.WHITE,

        )