import flet as ft
from datetime import datetime
import json
import math

from database import (
    init_db,
    get_all_entries, insert_entry, delete_all_entries,
    get_config, set_config, get_price_by_type, set_all_prices,
    get_all_registros, delete_all_registros,
    get_user_by_code, insert_user,
    get_all_users,  # <-- NUEVO
)

from helpers.helpers import (
    getDatacell, getDataColumns, print_ticket_usb
)


def main(page: ft.Page):
    # Componentes personalizados
    from components.Container import Container
    from components.Button import Button
    from components.TextField import TextField
    from components.Alert import Alert
    from components.AppBar import AppBar

    # Índices de páginas (evita números mágicos)
    PAGE_INICIO    = 0
    PAGE_ENTRADAS  = 1
    PAGE_IMPRESORA = 2
    PAGE_TARIFAS   = 3
    PAGE_USUARIOS  = 4
    PAGE_REGISTROS = 5

    init_db()

    # =========================
    # ESTADO / CONFIG
    # =========================
    state = {
        "business_name": "Comedor",
        "entries": [],
        "config": None,
        "printer": None,
    }

    # Paginación
    registros = []
    registros_current_page = 0
    REG_PAGE_SIZE = 100

    users = []
    users_current_page = 0
    USERS_PAGE_SIZE = 100

    datacells = getDatacell(state["entries"])
    columns = getDataColumns(["FOLIO", "CÓDIGO", "FECHA", "HORA", "TIPO USUARIO"])

    # PROPIEDADES DE PÁGINA
    page.title = "Control " + state["business_name"]
    page.theme_mode = ft.ThemeMode.DARK

    # =========================
    # FUNCIONES AUXILIARES
    # =========================

    def obtener_ultimo_registro():
        if state["entries"]:
            # Suponiendo que las entradas están ordenadas por fecha (descendente)
            ultimo_registro = state["entries"][0]
            nombre = ultimo_registro[1]  # Asumiendo que el nombre está en el índice 1
            codigo = ultimo_registro[0]  # Código del empleado
            empresa = ultimo_registro[2]  # Empresa
            fecha_entrada = ultimo_registro[3]  # Fecha de entrada
            hora_entrada = ultimo_registro[4]  # Hora de entrada
            
            # Contar las entradas del día
            hoy_iso = datetime.now().strftime("%Y-%m-%d")
            entradas_hoy = [e for e in state["entries"] if e[3] == hoy_iso]
            veces_entrado = len(entradas_hoy)

            return {
                "nombre": nombre,
                "codigo": codigo,
                "empresa": empresa,  # Aseguramos que la empresa se extrae correctamente
                "fecha_entrada": fecha_entrada,
                "hora_entrada": hora_entrada,  # Aseguramos que la hora se extrae correctamente
                "veces_entrado": veces_entrado
            }
        return None

    
    def formatear_fecha(fecha_iso: str):
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

    # --------- ENTRADAS (Comedor) ----------
    def refresh_entries():
        entradas = get_all_entries()
        state["entries"] = entradas
        rows = getDatacell(state["entries"])
        registers_database.rows.clear()
        registers_database.rows = rows
        actualizar_totales_hoy()
        page.update()

    def actualizar_totales_hoy():
        hoy_iso = datetime.now().strftime("%Y-%m-%d")
        hoy = [e for e in state["entries"] if e[3] == hoy_iso]
        total_hoy.value = str(len(hoy))

    def registrar_entrada_por_codigo(codigo_scan: str) -> bool:
        """
        Busca el empleado por código; si existe, imprime ticket e inserta la entrada.
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

        # Asumiendo que get_user_by_code devuelve (codigo, nombre, empresa)
        codigo_emp = str(u[0])  # Código de empleado
        nombre = str(u[1])  # Nombre del empleado
        empresa = str(u[2])  # Empresa del empleado

        if not state["printer"]:
            message("No hay impresora configurada. No se registró la entrada.")
            return False

        # Verifica conexión de impresora
        if not is_printer_connected(state["printer"]):
            message("La impresora configurada no está conectada.")
            return False

        # Fecha y hora de entrada
        now = datetime.now()
        hora = now.strftime("%H:%M:%S")
        fecha_iso = now.strftime("%Y-%m-%d")
        fecha_legible = formatear_fecha(fecha_iso)

        # Datos a imprimir en el ticket
        data = {
            "placa": codigo_emp,  # QR con el código del empleado
            "titulo": "Boleto de Comedor",
            "fecha_entrada": fecha_legible,
            "hora_entrada": hora,
            "empresa": empresa,  # Mostramos la empresa
        }

        try:
            print_ticket_usb(printer_name=state["printer"], data=data, entrada=True)
        except Exception as ex:
            message(f"Error al imprimir: {ex}")
            return False

        # Guardar en la base de datos
        try:
            insert_entry(
                codigo=codigo_emp,
                nombre=nombre,
                empresa=empresa,
                hora_entrada=hora,
                fecha_entrada=fecha_iso
            )
        except Exception as e:
            page.open(ft.SnackBar(ft.Text(f"Error al guardar entrada: {e}")))
            return False

        # Actualiza la sección control_usuario con el último registro de entrada
        ultimo_registro = obtener_ultimo_registro()
        if ultimo_registro:
            control_usuario.content = ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(f"Usuario: {ultimo_registro['nombre']}", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Empresa: {ultimo_registro['empresa']}", size=18),  # Mostramos la empresa
                            ft.Text(f"Fecha de Entrada: {ultimo_registro['fecha_entrada']}", size=18),
                            ft.Text(f"Hora de Entrada: {ultimo_registro['hora_entrada']}", size=18),  # Mostramos la hora de entrada
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,  # Reduce la separación entre los elementos
                        expand=True,
                    )
                ],
                expand=True
            )

        refresh_entries()
        page.open(ft.SnackBar(ft.Text(f"Entrada registrada para {nombre} ({empresa})")))
        page.update()
        return True







    # -------- Reporte CSV (Entradas) --------
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
        SUBJECT_PREFIX = "Reporte de salidas"
        BODY_TEXT = "Reporte de Usuarios"

        show_email_progress()

        # 1) Preparar mensaje + adjunto
        try:
            update_email_progress(0.10, "Preparando mensaje...")
            message = MIMEMultipart()
            message["From"] = EMAIL_FROM
            message["To"] = ", ".join(EMAIL_TO)
            message["Subject"] = f"{SUBJECT_PREFIX} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            message["Reply-To"] = EMAIL_REPLY_TO
            message.attach(MIMEText(BODY_TEXT, "plain", "utf-8"))

            update_email_progress(0.20, "Adjuntando archivo...")
            with open(file, "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="octet-stream")
            attachment.add_header("Content-Disposition", "attachment", filename=Path(file).name)
            message.attach(attachment)
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
                    server.sendmail(EMAIL_FROM, EMAIL_TO, message.as_string())
            else:
                update_email_progress(0.35, "Conectando...")
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                    if USE_STARTTLS:
                        update_email_progress(0.50, "Estableciendo TLS...")
                        server.starttls()
                    update_email_progress(0.65, "Autenticando...")
                    server.login(SMTP_USER, SMTP_PASS)
                    update_email_progress(0.90, "Enviando correo...")
                    server.sendmail(EMAIL_FROM, EMAIL_TO, message.as_string())

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

        # Usa exactamente lo que está en la lista (state["entries"])
        entradas = state["entries"] or []

        # r = [id, codigo, hora_entrada, fecha_entrada, hora_salida, fecha_salida, type_entry, precio, status]
        filas = [
            [r[0], r[1], r[3], r[2], r[6], float(r[7] or 0.0), r[8]]
            for r in entradas
        ]
        columnas = ["ID", "Código", "Fecha entrada", "Hora entrada", "Tipo usuario", "Precio (MXN)", "Estado"]

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

        # Si se creó bien, envíalo por correo con barra de progreso
        if filename:
            threading.Thread(target=lambda: send_email(filename), daemon=True).start()

    # -------- Impresoras --------
    def is_printer_connected(printer_name):
        try:
            import win32print
            hprinter = win32print.OpenPrinter(printer_name)
            win32print.ClosePrinter(hprinter)
            return True
        except Exception:
            return False

    def get_usb_printers():
        try:
            import win32print
            return [printer[2] for printer in win32print.EnumPrinters(2)]
        except Exception:
            return []

    def save_config(e):
        selected_printer = usb_selector.value
        available_printers = get_usb_printers()

        if not available_printers:
            page.open(ft.SnackBar(ft.Text("No hay impresoras disponibles")))
            return

        if selected_printer not in available_printers:
            page.open(ft.SnackBar(ft.Text("Selecciona una impresora válida")))
            return

        if not is_printer_connected(selected_printer):
            page.open(ft.SnackBar(ft.Text("La impresora seleccionada no está conectada")))
            return

        state["config"] = {"valor": selected_printer}
        state["printer"] = selected_printer
        try:
            set_config("impresora", json.dumps(state["config"]))
        except Exception as e:
            page.open(ft.SnackBar(ft.Text(f"Error al guardar configuración: {e}")))
            return

        show_page(PAGE_INICIO)
        page.open(ft.SnackBar(ft.Text("Impresora configurada correctamente")))

    # -------- Tarifas (solo Empleado) --------
    def load_prices():
        try:
            _, p_emp = get_price_by_type("empleado")
            price_emp.value = str(p_emp)
            page.update()
        except Exception as e:
            page.open(ft.SnackBar(ft.Text(f"Error al cargar tarifas: {e}")))

    def save_fee(e):
        try:
            set_all_prices(float(price_emp.value or 0), 0.0, 0.0)
            page.open(ft.SnackBar(ft.Text("Tarifa de Empleado guardada")))
            show_page(PAGE_INICIO)
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error al guardar tarifas: {ex}")))

    def load_config_impresora():
        # Rellena el dropdown con impresoras disponibles
        usb_selector.options = [ft.dropdown.Option(p) for p in get_usb_printers()]
        try:
            config_json = get_config("impresora")
            if config_json:
                config = json.loads(config_json)
                usb_selector.value = config.get("valor", None)
                state["config"] = config
                state["printer"] = config.get("valor", None)
        except Exception as e:
            page.open(ft.SnackBar(ft.Text(f"Error al cargar la configuración: {e}")))
        page.update()

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
            # Soporta (codigo, nombre, empresa) o (id, codigo, nombre, empresa)
            if len(u) >= 3:
                if len(u) == 3:
                    codigo, nombre, empresa = u[0], u[1], u[2]
                else:
                    codigo = u[1]
                    nombre = u[2] if len(u) > 2 else ""
                    empresa = u[3] if len(u) > 3 else ""
                rows.append(
                    ft.DataRow(
                        cells=[
                            ft.DataCell(ft.Text(str(codigo))),
                            ft.DataCell(ft.Text(str(nombre))),
                            ft.DataCell(ft.Text(str(empresa))),
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
                        # Actualiza barra y texto (muestra el código actual)
                        update_users_progress(done, total, extra=f"Código: {codigo if 'codigo' in locals() else ''}")

                # Cierra diálogo y muestra resumen
                hide_users_progress()
                page.open(ft.SnackBar(ft.Text(
                    f"Lista procesada. Agregados: {added}, Duplicados/omitidos: {skipped}, Errores: {errored}"
                )))

                # Refresca tabla si la vista Usuarios está visible
                if page_usuarios.visible:
                    load_usuarios()

            except Exception as ex:
                hide_users_progress()
                page.open(ft.SnackBar(ft.Text(f"Error leyendo archivo: {ex}")))
            finally:
                page.update()

        # Lanza el proceso en background
        threading.Thread(target=worker, daemon=True).start()

    # =========================
    # REGISTROS (vista con paginación)
    # =========================
    def load_registros():
        nonlocal registros, registros_current_page
        registros = get_all_registros() or []
        registros_current_page = 0
        update_registros_table()

    def make_registros_rows(items):
        rows = []
        for r in items:
            cells = [
                ft.DataCell(ft.Text(str(r[0]))),
                ft.DataCell(ft.Text(str(r[1]))),
                ft.DataCell(ft.Text(str(r[2]))),
                ft.DataCell(ft.Text(str(r[3]))),
                ft.DataCell(ft.Text(str(r[4]))),
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
            df = pd.DataFrame(data, columns=["ID", "Nombre", "Empresa", "Fecha", "Hora"])
            df.to_csv("reporte_registros.csv", index=False, encoding="utf-8-sig")
            page.open(ft.SnackBar(ft.Text("Reporte de registros guardado.")))
        except Exception as ex:
            page.open(ft.SnackBar(ft.Text(f"Error al guardar reporte: {ex}")))
        page.update()

    # =========================
    # NAVEGACIÓN
    # =========================
    def onChangePage(e):
        if e == PAGE_INICIO:
            filters_row_host.controls = []
            show_page(PAGE_INICIO)
            read_qr_inicio.focus()
        elif e == PAGE_ENTRADAS:
            filters_row_host.controls = []
            show_page(PAGE_ENTRADAS)
            read_qr.focus()
        elif e == PAGE_IMPRESORA:
            filters_row_host.controls = []
            show_page(PAGE_IMPRESORA, callback=load_config_impresora)
        elif e == PAGE_TARIFAS:
            filters_row_host.controls = []
            show_page(PAGE_TARIFAS, callback=load_prices)
        elif e == PAGE_USUARIOS:
            filters_row_host.controls = []
            show_page(PAGE_USUARIOS, callback=load_usuarios)
        elif e == PAGE_REGISTROS:
            filters_row_host.controls = []
            show_page(PAGE_REGISTROS, callback=load_registros)
        page.update()

    def show_page(index, callback=None):
        for i, p in enumerate([page_inicio, page_entradas, page_impresora, page_tarifas, page_usuarios, page_registros]):
            p.visible = (i == index)
        if callback:
            callback()
        # Foco
        if index == PAGE_INICIO:
            try: read_qr_inicio.focus()
            except Exception: pass
        elif index == PAGE_ENTRADAS:
            try: read_qr.focus()
            except Exception: pass
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

    # TextField de INICIO
    read_qr_inicio = TextField(
        label="Leer código de empleado",
        keyboard_type=ft.KeyboardType.TEXT,
        onSubmit=lambda e: onSubmitReadQr(e),
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
        "Usuarios", ft.Icons.PEOPLE, ft.Colors.TEAL_400,
        lambda e: show_page(PAGE_USUARIOS, callback=load_usuarios)
    )
    btn_registros = square_button(
        "Registros", ft.Icons.HISTORY, ft.Colors.CYAN_400,
        lambda e: show_page(PAGE_REGISTROS, callback=load_registros)  # <-- corregido a PAGE_REGISTROS
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

    control_usuario = ft.Container(
        content=ft.Row(
            [
                ft.Column(
            [
                ft.Text("ÚLTIMA ENTRADA", size=18, weight=ft.FontWeight.BOLD, expand=True),
                ft.Text("", size=18, expand=True),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            expand=True,
            
        )
            ], expand=True
        ), bgcolor=ft.colors.TRANSPARENT,expand=True
    )

    inicio_content = ft.Column(
        [
            ft.Row([read_qr_inicio], alignment=ft.MainAxisAlignment.CENTER),
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

    total_hoy = ft.Text("0", size=44, text_align=ft.TextAlign.CENTER, expand=True)
    totales_card = Container(
        business_name=state["business_name"],
        content=ft.Column(
            [
                ft.Row([ft.Text("SERVIDOS HOY", size=16, weight=ft.FontWeight.BOLD, expand=True)]),
                ft.Row([total_hoy], expand=True, alignment=ft.MainAxisAlignment.CENTER)
            ]
        ),
        height=130
    ).build()

    # --- ENTRADAS (comedor) ---
    read_qr = TextField(
        label="Leer código de empleado",
        keyboard_type=ft.KeyboardType.TEXT,
        onSubmit=onSubmitReadQr
    ).build()

    download_report_btn = Button(text="DESCARGAR REPORTE", on_click=download_report_csv).build()
    delete_registers_button = Button(
        text="BORRAR REGISTROS ENTRADAS", bgcolor=ft.Colors.RED_400,
        icon=ft.Icons.DELETE, on_click=lambda e: open_delete_entries_alert()
    ).build()

    alert_delete_entries = Alert(
        content=ft.Text("¿Seguro que desea borrar TODOS los registros de 'Entradas' del comedor?"),
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
        delete_all_entries()
        alert_delete_entries.open = False
        refresh_entries()
        page.open(ft.SnackBar(ft.Text("Entradas del comedor borradas.")))
        page.update()

    # Contenido de la vista principal
    content_data = ft.Column(
        [
            ft.Row([read_qr], height=50),  # TextField
            download_report_btn,           # Botón para descargar reporte
            delete_registers_button,       # Botón para borrar registros
            alert_delete_entries           # Alerta de eliminación
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        spacing=10,  # Espaciado entre elementos
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


    registers_database = ft.DataTable(columns=columns, rows=datacells, expand=True)

    page_entradas = ft.Row(
        [
            ft.Column(
                [
                    Container(height=200, business_name=state["business_name"], content=content_data).build(),
                    totales_card,
                ],
                width=350,
                scroll=ft.ScrollMode.AUTO
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
        expand=True, vertical_alignment=ft.CrossAxisAlignment.START,
    )
    page_entradas.visible = False

    # --- IMPRESORA ---
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

    # --- TARIFAS (solo Empleado) ---
    price_emp = TextField(label="Tarifa Empleado (MXN)", keyboard_type=ft.KeyboardType.NUMBER, width=300).build()

    fee_container = Container(
        business_name=state["business_name"],
        content=ft.Column(
            [
                ft.Text("CONFIGURACIÓN DE TARIFA (Empleado)", size=26, weight=ft.FontWeight.BOLD),
                ft.Row([ft.Column([price_emp])], expand=True, alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([Button(text="GUARDAR", icon=ft.Icons.SAVE, width=300, on_click=save_fee).build()],
                       expand=True, alignment=ft.MainAxisAlignment.CENTER),
            ],
            spacing=20, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        height=300,
    ).build()

    page_tarifas = ft.Row(
        [ft.Column([fee_container], expand=True, alignment=ft.MainAxisAlignment.START,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER)],
        expand=True
    )
    page_tarifas.visible = False

    # --- USUARIOS (tabla paginada) ---
    users_columns = [
        ft.DataColumn(ft.Text("Código")),
        ft.DataColumn(ft.Text("Nombre")),
        ft.DataColumn(ft.Text("Empresa")),
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

    page_registros = ft.Row(
        [
            ft.Column(
                [
                    Container(
                        business_name=state["business_name"],
                        content=ft.Column(
                            [
                                ft.Row([btn_reg_csv, btn_reg_borrar], alignment=ft.MainAxisAlignment.START, spacing=10),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Row([registros_table], expand=True),
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
                        ),
                    ).build(),
                ],
                expand=True
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
    def load_background_data():
        init_db()

        # Impresora
        try:
            impresora_config = get_config("impresora")
            if impresora_config:
                config = json.loads(impresora_config)
                state["config"] = config
                state["printer"] = config.get("valor", None)
        except Exception:
            pass

        # Entradas
        state["entries"] = get_all_entries()
        rows = getDatacell(state["entries"])
        registers_database.rows.clear()
        registers_database.rows = rows

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
                    page_tarifas,
                    page_usuarios,
                    page_registros,
                    alert_ring,
                    alert_user,
                    users_progress_dialog,
                    email_progress_dialog,  # <-- AÑADIDO
                ],
                expand=True
            ),
            expand=True
        )
    )



        show_page(PAGE_INICIO)
        try: read_qr_inicio.focus()
        except Exception: pass
        refresh_entries()
        page.update()

    threading.Thread(target=load_background_data, daemon=True).start()

ft.app(main)
