# Guía de Python: funciones útiles para LibreOffice - The Document Foundation Wiki

# Importa el módulo 'uno', que es la base para interactuar con la API de LibreOffice (UNO)
# Es esencial para conectar tu script con la suite ofimática.
import uno
# Importa la clase 'MessageBoxButtons' del módulo de la API 'com.sun.star.awt'.
# Esta clase define las constantes para los tipos de botones que se pueden usar en los cuadros de mensaje,
# como OK, Cancelar, Sí, No, etc.
from com.sun.star.awt import MessageBoxButtons as MSG_BUTTONS
# Importa la clase 'PropertyValue' de 'com.sun.star.beans'.
# Se usa para definir las propiedades de objetos de la API de LibreOffice,
# como las opciones al abrir un documento (solo lectura, etc.).
from com.sun.star.beans import PropertyValue

# Obtiene el contexto de componentes de UNO, que es el punto de entrada a la API.
# Es como el "punto de inicio" para todas las interacciones con LibreOffice.
CTX = uno.getComponentContext()
# Obtiene el gestor de servicios del contexto.
# Este objeto es responsable de crear instancias de los servicios de LibreOffice.
SM = CTX.getServiceManager()


def create_instance(name, with_context=False):
    """
    Crea una instancia de un servicio de la API de LibreOffice.
    
    Args:
        name (str): El nombre del servicio que se quiere crear (ej. "com.sun.star.frame.Desktop").
        with_context (bool): Si es True, crea la instancia con el contexto de UNO.
                             Esto es necesario para servicios de nivel superior como el Escritorio.

    Returns:
        object: La instancia del servicio creado.
    """
    if with_context:
        # Crea una instancia del servicio usando el contexto global de UNO.
        instance = SM.createInstanceWithContext(name, CTX)
    else:
        # Crea una instancia sin pasar el contexto.
        instance = SM.createInstance(name)
    return instance


def get_desktop():
    """
    Obtiene el servicio de Escritorio de LibreOffice.
    El servicio 'Desktop' es el punto de control principal de la interfaz de usuario de LibreOffice.
    """
    return create_instance("com.sun.star.frame.Desktop", True)


def call_dispatch(doc, url, args=()):
    """
    Ejecuta un comando de "dispatch" para realizar una acción en un documento.
    Los "dispatch commands" son URLs que permiten ejecutar acciones como guardar, imprimir, o formatear.

    Args:
        doc (object): El objeto del documento (ej. un documento de Writer o Calc).
        url (str): La URL del comando de dispatch a ejecutar (ej. ".uno:Save").
        args (tuple): Una tupla de argumentos de tipo 'PropertyValue' para el comando.
    """
    # Obtiene el frame (marco) del documento, que es el contenedor de la ventana.
    frame = doc.getCurrentController().getFrame()
    # Crea una instancia de 'DispatchHelper' para ejecutar comandos de dispatch.
    dispatch = create_instance("com.sun.star.frame.DispatchHelper")
    # Llama al comando 'executeDispatch' con el frame, la URL del comando, y los argumentos.
    dispatch.executeDispatch(frame, url, "", 0, args)
    return

# Cuadro de mensaje
def msgbox(
    message, title="LibreOffice", buttons=MSG_BUTTONS.BUTTONS_OK, type_msg="infobox"
):
    """
    Crea un cuadro de mensaje (message box) en la interfaz de LibreOffice.

    Args:
        message (str): El texto del mensaje a mostrar.
        title (str): El título de la ventana del cuadro de mensaje.
        buttons (int): El tipo de botones a mostrar (ej. BUTTONS_OK).
        type_msg (str): El tipo de cuadro de mensaje (infobox, warningbox, errorbox, etc.).

    Returns:
        int: El valor del botón que el usuario presionó.
    """
    # Crea una instancia del 'Toolkit', que es el punto de entrada para la API de la interfaz de usuario.
    toolkit = create_instance("com.sun.star.awt.Toolkit")
    # Obtiene la ventana principal del escritorio de LibreOffice para que el cuadro de mensaje sea su hijo.
    parent = toolkit.getDesktopWindow()
    # Crea el objeto del cuadro de mensaje con los parámetros dados.
    mb = toolkit.createMessageBox(parent, type_msg, buttons, title, str(message))
    # Muestra el cuadro de mensaje y devuelve el resultado de la interacción del usuario.
    return mb.execute()

# Diccionario de propiedades
def dict_to_property(values, uno_any=False):
    """
    Convierte un diccionario de valores a una tupla de objetos 'PropertyValue'.
    Este formato es el que usa la API de LibreOffice para pasar argumentos a funciones.

    Args:
        values (dict): Un diccionario donde las claves son nombres de propiedades y los valores son sus respectivos valores.
        uno_any (bool): Si es True, encapsula la tupla de propiedades en un objeto 'uno.Any'.

    Returns:
        tuple o uno.Any: Una tupla o un objeto uno.Any que contiene los objetos 'PropertyValue'.
    """
    # Crea una tupla de objetos PropertyValue a partir de los ítems del diccionario.
    ps = tuple([PropertyValue(Name=n, Value=v) for n, v in values.items()])
    if uno_any:
        # Si uno_any es True, empaqueta la tupla en un objeto uno.Any, lo que a veces es necesario para la API.
        ps = uno.Any("[]com.sun.star.beans.PropertyValue", ps)
    return ps

# Coger un color
def get_color(red, green, blue):
    """
    Convierte los valores de color RGB (rojo, verde, azul) a un solo número entero.
    Este es el formato que la API de LibreOffice utiliza para representar colores.

    Args:
        red (int): El valor del componente rojo (0-255).
        green (int): El valor del componente verde (0-255).
        blue (int): El valor del componente azul (0-255).

    Returns:
        int: Un único número entero que representa el color.
    """
    # Combina los valores de RGB usando desplazamientos de bits.
    color = (red << 16) + (green << 8) + blue
    return color

# Para abrir un documento de Calc use el siguiente bloque de código
def new_doc_calc():
    """
    Abre un nuevo documento de Calc (hoja de cálculo).
    """
    desktop = create_instance('com.sun.star.frame.Desktop', True)
    # Define la URL de la fábrica para crear un nuevo documento de Calc.
    path = 'private:factory/scalc'
    # Carga el nuevo componente de documento usando la URL de la fábrica.
    doc = desktop.loadComponentFromURL(path, '_default', 0, ())
    return


# Para abrir un documento de Writer use el siguiente bloque de código
def new_doc_writer():
    """
    Abre un nuevo documento de Writer (procesador de textos).
    """
    desktop = create_instance('com.sun.star.frame.Desktop', True)
    # Define la URL de la fábrica para crear un nuevo documento de Writer.
    path = 'private:factory/swriter'
    # Carga el nuevo componente de documento usando la URL de la fábrica.
    doc = desktop.loadComponentFromURL(path, '_default', 0, ())
    return
