def print_ticket_usb(printer_name=None, data=None, error=None, err_printer=None, entrada=True):

    """
    Ticket de COMEDOR en ZPL (impresoras Zebra o compatibles ZPL).
    data:
      - titulo, codigo, fecha_entrada, hora_entrada, empresa
    """
    import win32print

    try:
        entrada = int(entrada) + 1
    except Exception:
        entrada = 1

    if data is None:
        data = {}

    titulo  = data.get("titulo", "Boleto de Comedor")
    fecha   = data.get("fecha_entrada", "")
    hora    = data.get("hora_entrada", "")
    codigo  = data.get("codigo", "")
    nombre = data.get("nombre", "")
    zpl = f"""
        ^XA
        ~JSN
        ^LT0
        ^LH0,0
        ^JMA
        ^PR5,10
        ~SD15
        ^JUS
        ^LRN
        ^CI27
        ^PA0,1,1,0
        ^MMT
        ^PW609
        ^LL815
        ^LS0
        ^FPH,6^FT32,100^A0N,56,56^FH\^CI28^FD{titulo}^FS^CI27
        ^FPH,1^FT167,141^A0N,27,28^FH\^CI28^FD{fecha}^FS^CI27
        ^FPH,1^FT32,197^A0N,27,28^FH\^CI28^FDHora^FS^CI27
        ^FPH,1^FT475,197^A0N,27,28^FH\^CI28^FD{hora}^FS^CI27
        ^FO29,211^GB549,0,2^FS
        ^FT230,402^BQN,2,7
        ^FH\^FDLA,Nombre: {nombre}, Folio:{entrada}^FS
        ^FPH,1^FT217,427^A0N,27,28^FH\^CI28^FDCódigo: {codigo}^FS^CI27
        ^FPH,1^FT1,455^A0N,18,18^FB606,1,5,C^FH\^CI28^FDVálido únicamente para el día y horario indicado. Conserve su\5C&^FS^CI27
        ^FPH,1^FT1,478^A0N,18,18^FB606,1,5,C^FH\^CI28^FDticket\5C&^FS^CI27
        ^FO29,506^GB549,0,2^FS
        ^FPH,6^FT20,559^A0N,32,33^FH\^CI28^FDInnovación Culinaria Industrial^FS^CI27
        ^XZ
            """

    if printer_name:
        try:
            h = win32print.OpenPrinter(printer_name)
            try:
                job = win32print.StartDocPrinter(h, 1, ("Ticket Comedor ZPL", None, "RAW"))
                win32print.StartPagePrinter(h)
                # UTF-8 para ^CI28
                win32print.WritePrinter(h, zpl.encode("utf-8", errors="replace"))
                win32print.EndPagePrinter(h)
                win32print.EndDocPrinter(h)
            finally:
                win32print.ClosePrinter(h)
        except Exception as e:
            return error if error else print("Error al imprimir:", e)
    else:
        return err_printer if err_printer else print("No se ha seleccionado una impresora")

