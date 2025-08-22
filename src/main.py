import flet as ft
from datetime import datetime, timedelta
import math
import json

from database import (
    init_db,
    get_all_registros, insert_registro, delete_all_registros,
    get_user_by_code, insert_user, set_config, get_config,
    get_all_users, delete_empleado
)

from helpers.helpers import (
    print_ticket_usb  # getDatacell/getDataColumns no se usan con este schema
)


def main(page: ft.Page):
    # Componentes personalizados
    from components.Container import Container
    from components.Button import Button
    from components.TextField import TextField
    from components.Alert import Alert
    from components.AppBar import AppBar

    # Índices de páginas
    PAGE_INICIO    = 0
    PAGE_ENTRADAS  = 1
    PAGE_IMPRESORA = 2  # Persistencia eliminada; se usa en memoria
    PAGE_USUARIOS  = 3
    PAGE_REGISTROS = 4

    init_db()

    # =========================
    # ESTADO / CONFIG
    # =========================
    state = {
        "business_name": "Comedor",
        "entries": [],      # registros (id, codigo, nombre, empresa, hora_entrada, fecha_entrada)
        "printer": None,    # solo memoria
    }

    # Paginación
    registros = []
    registros_current_page = 0
    REG_PAGE_SIZE = 100

    users = []
    users_current_page = 0
    USERS_PAGE_SIZE = 100

    # PROPIEDADES DE PÁGINA
    page.title = "Control " + state["business_name"]
    page.theme_mode = ft.ThemeMode.DARK

    impresora_config = get_config("impresora")
    if impresora_config:
        try:
            config = json.loads(impresora_config)
            state["config"] = config
            state["printer"] = config.get("valor", None)
        except:
            message("Error al cargar la configuración de la impresora")


    # =========================
    # FUNCIONES AUXILIARES
    # =========================
    def obtener_ultimo_registro():
        if state["entries"]:
            # Traemos de DB ordenados DESC; el 0 es el más reciente
            r = state["entries"][0]
            # r = (id, codigo, nombre, empresa, hora_entrada, fecha_entrada)
            return {
                "id": r[0],
                "codigo": r[1],
                "nombre": r[2],
                "empresa": r[3],
                "hora_entrada": r[4],
                "fecha_entrada": r[5],
            }
        return None

    def formatear_fecha_legible(fecha_iso: str):
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        fecha = datetime.strptime(fecha_iso, "%Y-%m-%d")
        return f"{fecha.day} de {meses[fecha.month - 1]} del {fecha.year}"

    def message(text=None, ok=False, target_input: ft.TextField | None = None):
        snack_bar = ft.SnackBar(
            ft.Text(
                "Acción no válida" if text is None else text,
                size=20,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.WHITE
            ),
            bgcolor=(ft.Colors.GREEN_400 if ok else ft.Colors.RED_400),
            duration=ft.Duration(seconds=3)
        )
        if target_input is not None:
            target_input.value = ""
            target_input.focus()
        page.open(snack_bar)
        page.update()

    # --------- ENTRADAS (Registros) ----------
    def make_entries_rows(items):
        rows = []
        for r in items:
            # r = (id, codigo, nombre, empresa, hora_entrada, fecha_entrada)
            cells = [
                ft.DataCell(ft.Text(str(r[0]))),  # ID
                ft.DataCell(ft.Text(str(r[1]))),  # Código
                ft.DataCell(ft.Text(str(r[2]))),  # Nombre
                ft.DataCell(ft.Text(str(r[3]))),  # Empresa
                ft.DataCell(ft.Text(str(r[5]))),  # Fecha
                ft.DataCell(ft.Text(str(r[4]))),  # Hora
            ]
            rows.append(ft.DataRow(cells=cells))
        return rows

    def refresh_entries():
        # Cargar los registros desde la base de datos
        state["entries"] = get_all_registros() or []  # Recargar registros de la DB
        registers_database.rows = make_entries_rows(state["entries"])  # Actualiza la tabla con los registros

        # Actualiza el total de registros para hoy
        actualizar_totales_hoy()

        # Actualiza la información de la última entrada
        ultimo_registro = obtener_ultimo_registro()
        if ultimo_registro:
            control_usuario.content = ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("ÚLTIMA ENTRADA", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Usuario: {ultimo_registro['nombre']}", size=18),
                            ft.Text(f"Empresa: {ultimo_registro['empresa']}", size=18),
                            ft.Text(f"Fecha de Entrada: {ultimo_registro['fecha_entrada']}", size=18),
                            ft.Text(f"Hora de Entrada: {ultimo_registro['hora_entrada']}", size=18),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                        expand=True,
                    ),
                    totales_card,  # Mantener el totales_card
                ],
                expand=True
            )
        page.update()

    def actualizar_totales_hoy():
        hoy_iso = datetime.now().strftime("%Y-%m-%d")
        hoy = [e for e in state["entries"] if e[5] == hoy_iso]  # fecha_entrada = índice 5
        total_hoy.value = str(len(hoy))  # Actualiza el total de registros para hoy
        page.update()  # Asegúrate de actualizar la interfaz después de cambiar el valor

    def registrar_entrada_por_codigo(codigo_scan: str) -> bool:
        """
        Busca el empleado por código; si existe, opcionalmente imprime ticket e inserta la entrada.
        Devuelve True si registró; False si el código es inválido.
        """
        try:
            u = get_user_by_code(codigo_scan)
        except Exception as e:
            page.open(ft.SnackBar(ft.Text(f"Error al buscar empleado: {e}")))
            return False

        if not u:
            page.open(ft.SnackBar(ft.Text("Código inválido — empleado no encontrado")))
            return False

        # u = (codigo, nombre, empresa)
        codigo_emp, nombre, empresa = str(u[0]), str(u[1]), str(u[2])

        # Fecha y hora de entrada
        now = datetime.now()
        hora = now.strftime("%H:%M:%S")
        fecha_iso = now.strftime("%Y-%m-%d")
        fecha_legible = formatear_fecha_legible(fecha_iso)

        # Intento de impresión si hay impresora seleccionada en memoria
        if state["printer"]:
            try:
                data = {
                    "placa": codigo_emp,           # contenido para QR/Texto en tu helper
                    "titulo": "Boleto de Comedor",
                    "fecha_entrada": fecha_legible,
                    "hora_entrada": hora,
                    "empresa": empresa,
                }
                print_ticket_usb(printer_name=state["printer"], data=data, entrada=True)
            except Exception as ex:
                # No bloquea el registro si falla la impresión
                message(f"No se pudo imprimir el ticket: {ex}")

        # Guardar en la base de datos (tabla registros)
        try:
            insert_registro(
                codigo=codigo_emp,
                nombre=nombre,
                empresa=empresa,
                hora_entrada=hora,
                fecha_entrada=fecha_iso
            )
        except Exception as e:
            page.open(ft.SnackBar(ft.Text(f"Error al guardar entrada: {e}")))
            return False

        refresh_entries()
        page.open(ft.SnackBar(ft.Text(f"Entrada registrada para {nombre} ({empresa})")))
        return True

    # -------- Reporte CSV (Registros actuales) --------
    progress_ring = ft.ProgressRing()
    alert_ring = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=5),
        title=ft.Text("Generando reporte..."),
        content=ft.Row([progress_ring], width=50, height=50, alignment=ft.MainAxisAlignment.CENTER),
        alignment=ft.alignment.center,
    )
    alert_ring.open = False

    def send_email(file: str):
        import smtplib
        from datetime import datetime
        from pathlib import Path
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.application import MIMEApplication

        SMTP_HOST = "smtp.gmail.com"
        SMTP_PORT = 587
        SMTP_USER = "reportestectronic@gmail.com"
        SMTP_PASS = "tdllhiwbqmrzpqec"
        USE_SSL = False
        USE_STARTTLS = True

        EMAIL_FROM = SMTP_USER
        EMAIL_REPLY_TO = "joeltrincadov@gmail.com"
        EMAIL_TO = ["joeltrincadov@gmail.com"]
        SUBJECT_PREFIX = "Reporte de entradas"
        BODY_TEXT = "Reporte de Registros"

        show_email_progress()

        # 1) Preparar mensaje + adjunto
        try:
            update_email_progress(0.10, "Preparando mensaje...")
            message_m = MIMEMultipart()
            message_m["From"] = EMAIL_FROM
            message_m["To"] = ", ".join(EMAIL_TO)
            message_m["Subject"] = f"{SUBJECT_PREFIX} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            message_m["Reply-To"] = EMAIL_REPLY_TO
            message_m.attach(MIMEText(BODY_TEXT, "plain", "utf-8"))

            update_email_progress(0.20, "Adjuntando archivo...")
            with open(file, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="octet-stream")
            attachment.add_header("Content-Disposition", "attachment", filename=Path(file).name)
            message_m.attach(attachment)
        except Exception as e:
            hide_email_progress()
            page.open(ft.SnackBar(ft.Text(f"No se pudo adjuntar el archivo: {e}")))
            page.update()
            return

        # 2) Conectar / TLS / Login / Enviar
        try:
            if USE_SSL:
                update_email_progress(0.35, "Conectando (SSL)...")
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                    update_email_progress(0.60, "Autenticando...")
                    server.login(SMTP_USER, SMTP_PASS)
                    update_email_progress(0.85, "Enviando correo...")
                    server.sendmail(EMAIL_FROM, EMAIL_TO, message_m.as_string())
            else:
                update_email_progress(0.35, "Conectando...")
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                    if USE_STARTTLS:
                        update_email_progress(0.50, "Estableciendo TLS...")
                        server.starttls()
                    update_email_progress(0.65, "Autenticando...")
                    server.login(SMTP_USER, SMTP_PASS)
                    update_email_progress(0.90, "Enviando correo...")
                    server.sendmail(EMAIL_FROM, EMAIL_TO, message_m.as_string())

            update_email_progress(1.00, "¡Correo enviado!")
            hide_email_progress()
            page.open(ft.SnackBar(ft.Text("Correo enviado correctamente")))
        except Exception as e:
            hide_email_progress()
            page.open(ft.SnackBar(ft.Text(f"Error al enviar el correo: {e}")))
        finally:
            page.update()

    def download_report_csv(e):
        import pandas as pd
        import threading

        entradas = state["entries"] or []
        # r = (id, codigo, nombre, empresa, hora_entrada, fecha_entrada)
        filas = [
            [r[0], r[1], r[2], r[3], r[5], r[4]]
            for r in entradas
        ]
        columnas = ["ID", "Código", "Nombre", "Empresa", "Fecha entrada", "Hora entrada"]

        alert_ring.open = True
        page.update()

        filename = None
        try:
            df = pd.DataFrame(filas, columns=columnas)
            filename = f"reporte_entradas_comedor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            page.open(ft.SnackBar(ft.Text(f"Reporte guardado: {filename}")))
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error al guardar el reporte: {ex}")))
        finally:
            alert_ring.open = False
            page.update()

        if filename:
            threading.Thread(target=lambda: send_email(filename), daemon=True).start()

    # -------- Impresoras (en memoria, sin DB) --------
    def get_usb_printers():
        try:
            import win32print
            return [printer[2] for printer in win32print.EnumPrinters(2)]
        except Exception:
            return []

    def is_printer_connected(printer_name):
        try:
            import win32print
            hprinter = win32print.OpenPrinter(printer_name)
            win32print.ClosePrinter(hprinter)
            return True
        except:
            return False
    
    def save_config(e):
        """Guardar la impresora seleccionada en la base de datos."""
        selected_printer = usb_selector.value
        available_printers = get_usb_printers()

        if not available_printers:
            page.open(ft.SnackBar(ft.Text("No hay impresoras disponibles", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_400))
            return

        if selected_printer not in available_printers:
            page.open(ft.SnackBar(ft.Text("Selecciona una impresora válida", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), bgcolor=ft.Colors.RED_400))
            return

        # Guardamos la impresora seleccionada en la base de datos
        set_config("printer_name", selected_printer)

        # Actualizamos el estado de la impresora en memoria
        state["printer"] = selected_printer
        page.open(ft.SnackBar(ft.Text("Impresora configurada correctamente", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), bgcolor=ft.Colors.GREEN_400))
        show_page(PAGE_INICIO)






    # =========================
    # USUARIOS (Tabla paginada y altas)
    # =========================
    def load_usuarios():
        nonlocal users, users_current_page
        users = get_all_users() or []
        users_current_page = 0
        update_users_table()

    def make_users_rows(items):
        rows = []
        for u in items:
            # u = (codigo, nombre, empresa)
            codigo, nombre, empresa = u[0], u[1], u[2]
            
            # Botón de eliminación
            delete_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                on_click=lambda e, codigo=codigo: open_delete_user_alert(codigo)
            )
            
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(codigo))),
                        ft.DataCell(ft.Text(str(nombre))),
                        ft.DataCell(ft.Text(str(empresa))),
                        ft.DataCell(delete_button),  # Columna de acción
                    ]
                )
            )
        return rows


    def update_users_table():
        start = users_current_page * USERS_PAGE_SIZE
        end = start + USERS_PAGE_SIZE
        slice_items = users[start:end]
        users_table.rows = make_users_rows(slice_items)
        users_page_text.value = f"Página {users_current_page + 1} de {max(1, math.ceil(len(users)/USERS_PAGE_SIZE))}"
        page.update()

    def users_next(e):
        nonlocal users_current_page
        if (users_current_page + 1) * USERS_PAGE_SIZE < len(users):
            users_current_page += 1
            update_users_table()

    def users_prev(e):
        nonlocal users_current_page
        if users_current_page > 0:
            users_current_page -= 1
            update_users_table()

    def open_add_user_alert(e=None):
        codigo_field.value = ""
        name_field.value = ""
        company_field.value = ""
        alert_user.open = True
        page.update()
        try:
            codigo_field.focus()
        except Exception:
            pass

    def close_add_user_alert(e=None):
        alert_user.open = False
        page.update()

    def add_user_now(e):
        try:
            codigo = str(codigo_field.value or "").strip()
            nombre = str(name_field.value or "").strip()
            empresa = str(company_field.value or "").strip()

            if not codigo or not nombre or not empresa:
                page.open(ft.SnackBar(ft.Text("Completa Código, Nombre y Empresa.")))
                return

            if get_user_by_code(codigo):
                page.open(ft.SnackBar(ft.Text("El código ya existe.")))
                return

            insert_user(codigo, nombre, empresa)

            codigo_field.value = ""
            name_field.value = ""
            company_field.value = ""
            alert_user.open = False
            page.open(ft.SnackBar(ft.Text("Empleado agregado.")))

            if page_usuarios.visible:
                load_usuarios()

            page.update()
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error al agregar empleado: {ex}")))
            page.update()

    # Carga masiva de empleados
    def on_files_picked(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        path = e.files[0].path
        bulk_insert_users(path)

    def bulk_insert_users(path: str):
        import os
        import pandas as pd
        import threading

        def worker():
            added = 0
            skipped = 0
            errored = 0
            total = 0

            try:
                # Lectura de archivo
                ext = os.path.splitext(path)[1].lower()
                if ext == ".csv":
                    df = pd.read_csv(path)
                elif ext in (".xlsx", ".xls"):
                    df = pd.read_excel(path)
                else:
                    page.open(ft.SnackBar(ft.Text("Formato no soportado. Usa .xlsx o .csv")))
                    return

                # Mapeo flexible de columnas
                cols = {str(c).lower().strip(): c for c in df.columns}
                c_codigo  = next((cols[k] for k in cols if k in ("codigo", "código", "code")), None)
                c_nombre  = next((cols[k] for k in cols if k in ("nombre", "name")), None)
                c_empresa = next((cols[k] for k in cols if k in ("empresa", "company")), None)

                if not (c_codigo and c_nombre and c_empresa):
                    page.open(ft.SnackBar(ft.Text("El archivo debe contener columnas: Código, Nombre y Empresa.")))
                    return

                total = len(df)
                show_users_progress("Cargando usuarios desde archivo")

                # Inserción fila por fila con progreso
                done = 0
                for _, row in df.iterrows():
                    try:
                        codigo  = str(row[c_codigo]).strip()
                        nombre  = str(row[c_nombre]).strip()
                        empresa = str(row[c_empresa]).strip()

                        if not codigo or not nombre or not empresa:
                            skipped += 1
                        elif get_user_by_code(codigo):
                            skipped += 1
                        else:
                            insert_user(codigo, nombre, empresa)
                            added += 1
                    except Exception:
                        errored += 1
                    finally:
                        done += 1
                        update_users_progress(done, total, extra=f"Código: {codigo if 'codigo' in locals() else ''}")

                hide_users_progress()
                page.open(ft.SnackBar(ft.Text(
                    f"Lista procesada. Agregados: {added}, Duplicados/omitidos: {skipped}, Errores: {errored}"
                )))

                if page_usuarios.visible:
                    load_usuarios()

            except Exception as ex:
                hide_users_progress()
                page.open(ft.SnackBar(ft.Text(f"Error leyendo archivo: {ex}")))
            finally:
                page.update()

        threading.Thread(target=worker, daemon=True).start()

    # =========================
    # REGISTROS (vista con paginación) — ya usamos la misma tabla de registros
    # =========================
    def load_registros():
        registros = get_all_registros() or []
        state["entries"] = registros  # Asegúrate de tener todos los registros cargados
        registers_database.rows = make_entries_rows(registros)  # Actualiza la tabla con todos los registros
        reg_page_text.value = f"Página 1 de {max(1, math.ceil(len(registros)/REG_PAGE_SIZE))}"
        page.update()


    def make_registros_rows(items):
        rows = []
        for r in items:
            # r = (id, codigo, nombre, empresa, hora_entrada, fecha_entrada)
            cells = [
                ft.DataCell(ft.Text(str(r[0]))),  # ID
                ft.DataCell(ft.Text(str(r[2]))),  # Nombre
                ft.DataCell(ft.Text(str(r[3]))),  # Empresa
                ft.DataCell(ft.Text(str(r[5]))),  # Fecha
                ft.DataCell(ft.Text(str(r[4]))),  # Hora
            ]
            rows.append(ft.DataRow(cells=cells))
        return rows

    def update_registros_table():
        start = registros_current_page * REG_PAGE_SIZE
        end = start + REG_PAGE_SIZE
        slice_items = registros[start:end]
        registros_table.rows = make_registros_rows(slice_items)
        reg_page_text.value = f"Página {registros_current_page + 1} de {max(1, math.ceil(len(registros)/REG_PAGE_SIZE))}"
        page.update()

    def reg_next(e):
        nonlocal registros_current_page
        if (registros_current_page + 1) * REG_PAGE_SIZE < len(registros):
            registros_current_page += 1
            update_registros_table()

    def reg_prev(e):
        nonlocal registros_current_page
        if registros_current_page > 0:
            registros_current_page -= 1
            update_registros_table()

    def reg_delete_all(e):
        delete_all_registros()
        load_registros()
        page.open(ft.SnackBar(ft.Text("Registros eliminados.")))

    def reg_download_csv(e):
        import pandas as pd
        data = get_all_registros() or []
        try:
            df = pd.DataFrame(
                [[r[0], r[1], r[2], r[3], r[5], r[4]] for r in data],
                columns=["ID", "Código", "Nombre", "Empresa", "Fecha", "Hora"]
            )
            df.to_csv("reporte_registros.csv", index=False, encoding="utf-8-sig")
            page.open(ft.SnackBar(ft.Text("Reporte de registros guardado.")))
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error al guardar reporte: {ex}")))
        page.update()

    def load_config_impresora():
        """Cargar la impresora configurada desde la base de datos y actualizar el dropdown."""
        printer_name = get_config("printer_name")
        print(printer_name, "printer_name")
        
        if printer_name:
            state["printer"] = printer_name  # Guardamos la impresora seleccionada en memoria
            usb_selector.value = printer_name  # Preseleccionamos la impresora en el selector
        else:
            state["printer"] = None  # Si no hay impresora configurada, dejamos el valor en None
            usb_selector.value = None  # Dejamos vacío el valor del dropdown

        # Cargar impresoras disponibles
        usb_selector.options = [ft.dropdown.Option(p) for p in get_usb_printers()]
        
        page.update()  # Actualiza la UI para reflejar la impresora seleccionada

    # =========================
    # NAVEGACIÓN
    # =========================
    def onChangePage(e):
        if e == PAGE_INICIO:
            filters_row_host.controls = []
            show_page(PAGE_INICIO)
        elif e == PAGE_ENTRADAS:
            print("onChangePage", e)
            filters_row_host.controls = []
            show_page(PAGE_REGISTROS, callback=load_registros)
        elif e == PAGE_IMPRESORA:
            filters_row_host.controls = []
            show_page(PAGE_IMPRESORA, callback=load_config_impresora)
        elif e == PAGE_USUARIOS:
            filters_row_host.controls = []
            show_page(PAGE_USUARIOS, callback=load_usuarios)
        elif e == PAGE_REGISTROS:
            filters_row_host.controls = []
            show_page(PAGE_REGISTROS, callback=load_registros)
        page.update()

    def show_page(index, callback=None):
        for i, p in enumerate([page_inicio, page_entradas, page_impresora, page_usuarios, page_registros]):
            p.visible = (i == index)
        if callback:
            callback()
        page.update()


    # -------- Entrada por comando / QR (comedor) --------
    def onSubmitReadQr(e):
        input_field = e.control  # puede ser read_qr_inicio o read_qr
        codigo_scan = (input_field.value or "").strip()
        if not codigo_scan:
            message("Ingresa o escanea un código de empleado", target_input=input_field)
            return
        registrar_entrada_por_codigo(codigo_scan)
        input_field.value = ""
        input_field.focus()
        page.update()

    def filter_by_date_range(range_type: str):
        # Obtén la fecha actual
        today = datetime.today()

        if range_type == "today":
            # Filtrar solo registros del día de hoy
            filtered_entries = [e for e in state["entries"] if e[5] == today.strftime("%Y-%m-%d")]
        elif range_type == "7_days":
            # Filtrar registros de los últimos 7 días
            start_date = today - timedelta(days=7)
            filtered_entries = [e for e in state["entries"] if datetime.strptime(e[5], "%Y-%m-%d") >= start_date]
        elif range_type == "month":
            # Filtrar registros del mes actual
            start_date = today.replace(day=1)
            filtered_entries = [e for e in state["entries"] if datetime.strptime(e[5], "%Y-%m-%d") >= start_date]
        elif range_type == "year":
            # Filtrar registros del año actual
            start_date = today.replace(month=1, day=1)
            filtered_entries = [e for e in state["entries"] if datetime.strptime(e[5], "%Y-%m-%d") >= start_date]
        else:
            filtered_entries = state["entries"]

        # Actualizar la tabla de registros
        registers_database.rows = make_entries_rows(filtered_entries)
        page.update()

    def apply_date_filter(selected_filter: str):
        # Obtén la fecha actual
        today = datetime.today()

        if selected_filter == "Hoy":
            # Filtrar solo registros del día de hoy
            filtered_entries = [e for e in state["entries"] if e[5] == today.strftime("%Y-%m-%d")]
        elif selected_filter == "Últimos 7 días":
            # Filtrar registros de los últimos 7 días
            start_date = today - timedelta(days=7)
            filtered_entries = [e for e in state["entries"] if datetime.strptime(e[5], "%Y-%m-%d") >= start_date]
        elif selected_filter == "Este mes":
            # Filtrar registros del mes actual
            start_date = today.replace(day=1)
            filtered_entries = [e for e in state["entries"] if datetime.strptime(e[5], "%Y-%m-%d") >= start_date]
        elif selected_filter == "Este año":
            # Filtrar registros del año actual
            start_date = today.replace(month=1, day=1)
            filtered_entries = [e for e in state["entries"] if datetime.strptime(e[5], "%Y-%m-%d") >= start_date]
        else:
            # Si no hay filtro, mostrar todos los registros
            filtered_entries = state["entries"]

        # Actualiza la tabla con los registros filtrados
        registers_database.rows = make_entries_rows(filtered_entries)
        page.update()

    def update_printer_dropdown():
        """Actualizar el dropdown de impresoras disponibles."""
        available_printers = get_usb_printers()
        usb_selector.options = [ft.dropdown.Option(p) for p in available_printers]
        
        # Si hay una impresora configurada, preseleccionarla
        if state["printer"]:
            usb_selector.value = state["printer"]
        page.update()



    # =========================
    # UI
    # =========================
    # FilePicker global (para Agregar Lista)
    file_picker = ft.FilePicker(on_result=on_files_picked)
    page.overlay.append(file_picker)

    # --- INICIO ---
    def square_button(texto, icono, color, on_click):
        return ft.Container(
            width=180, height=150, bgcolor=color, border_radius=12,
            ink=True, on_click=on_click,
            content=ft.Column(
                [ft.Icon(icono, size=40),
                 ft.Text(texto, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER)],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8
            )
        )
    
    def refresh_users():
        """Recarga la lista de usuarios y actualiza la tabla"""
        users = get_all_users() or []
        users_table.rows = make_users_rows(users)
        page.update()

    def open_delete_user_alert(codigo: str):
        """Abre el alert para confirmar la eliminación del usuario"""
        global user_to_delete
        user_to_delete = codigo  # Guardamos el código del usuario a eliminar
        alert_delete_user.open = True
        page.update()

    def close_delete_user_alert():
        """Cierra el alert sin realizar la eliminación"""
        alert_delete_user.open = False
        page.update()

    def do_delete_user(e):
        """Elimina el usuario de la base de datos"""
        try:
            delete_empleado(user_to_delete)  # Llamamos a la función para eliminar el usuario
            refresh_users()  # Actualizamos la tabla de usuarios
            page.open(ft.SnackBar(ft.Text("Usuario eliminado.")))
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error al eliminar usuario: {ex}")))
        finally:
            close_delete_user_alert()


    

        # Alerta de confirmación de eliminación
    alert_delete_user = ft.AlertDialog(
    title=ft.Text("Eliminar usuario"),
    content=ft.Text("¿Seguro que deseas eliminar a este usuario?"),
        actions=[
            ft.TextButton(
                text="Cancelar", 
                on_click=close_delete_user_alert
            ),
            ft.TextButton(
                text="Eliminar", 
                on_click=do_delete_user
            ),
        ],
    )
    alert_delete_user.open = False

    # TextField de INICIO
    read_qr_inicio = TextField(
        label="Leer código de empleado --> QR",
        keyboard_type=ft.KeyboardType.TEXT,
        onSubmit=lambda e: onSubmitReadQr(e),
        height=60,
        width=300,
        
    ).build()
    read_qr_inicio.autofocus = True

    # Botones de INICIO
    btn_lista = square_button(
        "Agregar Lista de empleados", ft.Icons.UPLOAD, ft.Colors.BLUE_400,
        lambda e: file_picker.pick_files(allowed_extensions=["xlsx", "xls", "csv"], allow_multiple=False)
    )
    btn_add_user = square_button(
        "Agregar empleado", ft.Icons.PERSON_ADD, ft.Colors.GREEN_400, open_add_user_alert
    )
    btn_usuarios = square_button(
        "Empleados", ft.Icons.PEOPLE, ft.Colors.TEAL_400,
        lambda e: show_page(PAGE_USUARIOS, callback=load_usuarios)
    )
    btn_registros = square_button(
        "Registros", ft.Icons.HISTORY, ft.Colors.CYAN_400,
        lambda e: show_page(PAGE_REGISTROS, callback=load_registros)
    )
    btn_reporte = square_button(
        "Descargar\nReporte", ft.Icons.DOWNLOAD, ft.Colors.PURPLE_400, download_report_csv
    )

    inicio_grid = ft.Column(
        [
            ft.Row([btn_lista, btn_add_user, btn_usuarios, btn_registros, btn_reporte],
                   alignment=ft.MainAxisAlignment.CENTER, spacing=24),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=24,
    )
    total_hoy = ft.Text("0", size=112, text_align=ft.TextAlign.CENTER, expand=True)
    totales_card = Container(
        business_name=state["business_name"],
        content=ft.Column(
            [
                ft.Row([ft.Text("SERVIDOS HOY", size=24, weight=ft.FontWeight.BOLD, expand=True)]),
                ft.Row([total_hoy], expand=True, alignment=ft.MainAxisAlignment.CENTER)
            ], expand=True
        ),
    ).build()

    control_usuario = ft.Container(
        content=ft.Row(
            [
                ft.Container(
                    content= ft.Column(
                    [
                        ft.Text("ÚLTIMA ENTRADA", size=24, weight=ft.FontWeight.BOLD, expand=True),
                        ft.Text("", size=24, expand=True),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.START,
                    spacing=8,
                    expand=True,
                ),
                gradient=ft.LinearGradient(colors=[ft.Colors.BLACK54, ft.Colors.GREY_900]),
                border_radius=10,
                padding=10, expand=True
                ),
                totales_card,  # Mantener el total_hoy actualizado
            ], expand=True
        ),
        expand=True
    )


    inicio_content = ft.Column(
        [
            ft.Row([read_qr_inicio], alignment=ft.MainAxisAlignment.CENTER, height=60),
            control_usuario,
            inicio_grid,
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page_inicio = ft.Row(
        [ft.Container(content=inicio_content, expand=True)],
        expand=True, vertical_alignment=ft.CrossAxisAlignment.START,
    )
    delete_registers_button = Button(
        text="BORRAR REGISTROS", bgcolor=ft.Colors.RED_400,
        icon=ft.Icons.DELETE, on_click=lambda e: open_delete_entries_alert()
    ).build()

    alert_delete_entries = Alert(
        content=ft.Text("¿Seguro que desea borrar TODOS los registros?"),
        action="Borrar",
        onAdd=lambda e: do_delete_entries(),
        onCancel=lambda e: close_delete_entries_alert()
    ).build()
    alert_delete_entries.open = False

    def open_delete_entries_alert():
        alert_delete_entries.open = True
        page.update()

    def close_delete_entries_alert():
        alert_delete_entries.open = False
        page.update()

    def do_delete_entries():
        delete_all_registros()
        refresh_entries()
        actualizar_totales_hoy() 
        page.open(ft.SnackBar(ft.Text("Registros eliminados.")))  # Muestra un mensaje de confirmación
        page.update()

    entries_columns = [
        ft.DataColumn(ft.Text("ID")),
        ft.DataColumn(ft.Text("Código")),
        ft.DataColumn(ft.Text("Nombre")),
        ft.DataColumn(ft.Text("Empresa")),
        ft.DataColumn(ft.Text("Fecha")),
        ft.DataColumn(ft.Text("Hora")),
    ]
    registers_database = ft.DataTable(columns=entries_columns, rows=[], expand=True)

    page_entradas = ft.Column(
        [
            ft.Row(
                [
                    delete_registers_button,
                    alert_delete_entries
                ], expand=True, alignment=ft.MainAxisAlignment.END
            ),
            ft.Column(
                [
                    Container(
                        business_name=state["business_name"],
                        content=ft.Row([registers_database], expand=True),
                        height=None, expand=True
                    ).build()
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.START,
            ),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )
    page_entradas.visible = False

    # --- IMPRESORA (sin persistencia) ---
    usb_selector = ft.Dropdown(label="Impresoras USB", width=300, border_color=ft.Colors.WHITE)

    config_container = Container(
        business_name=state["business_name"],
        content=ft.Column(
            [
                ft.Text("CONFIGURACIÓN DE IMPRESORA", size=26, weight=ft.FontWeight.BOLD),
                usb_selector,
                ft.Row([Button(text="GUARDAR", on_click=save_config, icon=ft.Icons.SAVE, width=300).build()],
                       expand=True, alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=20, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        height=400,
    ).build()

    page_impresora = ft.Row(
        [ft.Column([config_container], expand=True,
                   alignment=ft.MainAxisAlignment.START,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER)],
        expand=True
    )
    page_impresora.visible = False

    # --- USUARIOS (tabla paginada) ---
    users_columns = [
        ft.DataColumn(ft.Text("Código")),
        ft.DataColumn(ft.Text("Nombre")),
        ft.DataColumn(ft.Text("Empresa")),
        ft.DataColumn(ft.Text("Acciones")),
    ]
    users_table = ft.DataTable(columns=users_columns, rows=[], expand=True)
    users_page_text = ft.Text("", size=16)

    page_usuarios = ft.Row(
        [
            ft.Column(
                [
                    Container(
                        business_name=state["business_name"],
                        content=ft.Column(
                            [
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Row([users_table], expand=True),
                                            ft.Row(
                                                [
                                                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=users_prev),
                                                    users_page_text,
                                                    ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=users_next),
                                                ],
                                                alignment=ft.MainAxisAlignment.CENTER
                                            ),
                                        ],
                                        expand=True,
                                        scroll=ft.ScrollMode.AUTO
                                    ),
                                    expand=True
                                ),
                            ],
                            expand=True
                        ),
                    ).build(),
                ],
                expand=True
            )
        ],
        expand=True
    )
    page_usuarios.visible = False

    # --- REGISTROS (paginado) ---
    registros_columns = [
        ft.DataColumn(ft.Text("ID")),
        ft.DataColumn(ft.Text("Nombre")),
        ft.DataColumn(ft.Text("Empresa")),
        ft.DataColumn(ft.Text("Fecha")),
        ft.DataColumn(ft.Text("Hora")),
    ]
    registros_table = ft.DataTable(columns=registros_columns, rows=[], expand=True)
    reg_page_text = ft.Text("", size=16)

    btn_reg_borrar = Button(
        text="BORRAR REGISTROS", bgcolor=ft.Colors.RED_400, icon=ft.Icons.DELETE, on_click=reg_delete_all
    ).build()
    btn_reg_csv = Button(
        text="DESCARGAR REPORTE", icon=ft.Icons.DOWNLOAD, on_click=reg_download_csv
    ).build()

    date_filter_dropdown = ft.Dropdown(
        label="Filtrar por fechas",
        options=[
            ft.dropdown.Option("Hoy"),
            ft.dropdown.Option("Últimos 7 días"),
            ft.dropdown.Option("Este mes"),
            ft.dropdown.Option("Este año"),
        ],
        on_change=lambda e: apply_date_filter(e.control.value), width=200
    )

    # Vista de Registros
    page_registros = ft.Row(
        [
            ft.Column(
                [
                    ft.Row([date_filter_dropdown, btn_reg_borrar], alignment=ft.MainAxisAlignment.END),  # Fila con el dropdown
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([registers_database], expand=True),
                                ft.Row(
                                    [
                                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=reg_prev),
                                        reg_page_text,
                                        ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=reg_next),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER
                                ),
                            ],
                            expand=True, scroll=ft.ScrollMode.AUTO
                        ),
                        expand=True
                    ),
                ], expand=True
            )
        ],
        expand=True
    )
    page_registros.visible = False


    # --- ALERT: Agregar empleado ---
    codigo_field = TextField(label="Código", keyboard_type=ft.KeyboardType.TEXT).build()
    name_field = TextField(label="Nombre").build()
    company_field = TextField(label="Empresa").build()

    alert_user = Alert(
        title="Agregar empleado",
        content=ft.Column([codigo_field, name_field, company_field], spacing=10, height=200, expand=True, width=300),
        onCancel=close_add_user_alert,
        onAdd=add_user_now,
        action="Agregar"
    ).build()
    alert_user.open = False

    # --- ALERT: Progreso de envío de correo ---
    email_progress_bar = ft.ProgressBar(width=400, value=0)
    email_progress_text = ft.Text("Preparando...", size=14)

    email_progress_dialog = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=8),
        title=ft.Text("Enviando reporte por correo..."),
        content=ft.Column(
            [
                email_progress_bar,
                email_progress_text,
            ],
            tight=True, spacing=10, width=420
        )
    )

    def show_email_progress(title: str = "Enviando reporte por correo..."):
        email_progress_dialog.title = ft.Text(title)
        email_progress_bar.value = 0
        email_progress_text.value = "Preparando..."
        email_progress_dialog.open = True
        page.update()

    def update_email_progress(val: float, msg: str = ""):
        try:
            email_progress_bar.value = val
        except Exception:
            email_progress_bar.value = None  # indeterminado
        email_progress_text.value = msg
        page.update()

    def hide_email_progress():
        email_progress_dialog.open = False
        page.update()

    # --- ALERT: Progreso de carga masiva de usuarios ---
    users_progress_bar = ft.ProgressBar(width=400, value=0)
    users_progress_text = ft.Text("Esperando archivo...", size=14)

    users_progress_dialog = ft.AlertDialog(
        modal=True,
        shape=ft.RoundedRectangleBorder(radius=8),
        title=ft.Text("Cargando usuarios..."),
        content=ft.Column(
            [
                users_progress_bar,
                users_progress_text,
            ],
            tight=True, spacing=10, width=420
        )
    )

    def show_users_progress(title: str = "Cargando usuarios..."):
        users_progress_dialog.title = ft.Text(title)
        users_progress_bar.value = 0
        users_progress_text.value = "Preparando..."
        users_progress_dialog.open = True
        page.update()

    def update_users_progress(done: int, total: int, extra: str = ""):
        try:
            users_progress_bar.value = 0 if total == 0 else done / total
        except Exception:
            users_progress_bar.value = None  # indeterminado
        users_progress_text.value = f"{done}/{total} {('- ' + extra) if extra else ''}"
        page.update()

    def hide_users_progress():
        users_progress_dialog.open = False
        page.update()

    # Loading
    loading_indicator = ft.ProgressRing(width=60, height=60)
    loading_text = ft.Text("Cargando sistema, por favor espera...", size=16)
    loading_screen = ft.Column(
        [loading_indicator, loading_text],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True
    )
    page.add(loading_screen)
    page.update()

    # Filtros AppBar
    filters_row_host = ft.Row([], expand=True, alignment=ft.MainAxisAlignment.END)

    # Carga inicial (daemon)
    import threading
    # Carga inicial (daemon) - Asegúrate de que cargue los registros correctamente al inicio
    def load_background_data():
        init_db()

        # Cargar configuración de la impresora
        load_config_impresora()  # Esta función ahora cargará la impresora configurada

        # El resto del código para cargar registros y usuarios
        page.controls.clear()
        page.appbar = AppBar(
            business_name=state["business_name"],
            onChange=onChangePage,
            filters=filters_row_host
        ).build()

        filters_row_host.controls = []

        page.add(
            ft.SafeArea(
                ft.Column(
                    [
                        page_inicio,
                        page_entradas,
                        page_impresora,
                        page_usuarios,
                        alert_delete_user,
                        page_registros,
                        alert_ring,
                        alert_user,
                        users_progress_dialog,
                        email_progress_dialog,
                    ],
                    expand=True
                ),
                expand=True
            )
        )

        # Inicializa las tablas con los registros
        registers_database.rows = make_entries_rows(state["entries"])  # Asegúrate de cargar los registros
        load_registros()  # Actualiza la vista de registros
        load_usuarios()

        show_page(PAGE_INICIO)
        try:
            read_qr_inicio.focus()
        except Exception:
            pass
        refresh_entries()  # Llama a la función que actualiza la tabla de registros
        page.update()

    # Llamamos al hilo de carga
    threading.Thread(target=load_background_data, daemon=True).start()


ft.app(main)
