#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generador de Encabezados y Licencias (GPLv3)

Descripción:
    Script que itera sobre todos los archivos de una extensión específica en un
    directorio y les añade un encabezado de licencia y metadatos con el formato
    estándar. Permite elegir entre un modo 'Genérico' (relleno automático con
    valores por defecto) y un modo 'Interactivo' (pedir detalles por cada script).

Uso:
    python3 generar_encabezados.py <extension_archivos> <directorio_archivos>
    Ejemplo: python3 generar_encabezados.py py "/home/usuario/proyectos/scripts/"
"""

import argparse
import glob
import os
import sys
from datetime import date

# --- Funciones de Solicitud de Datos ---


def solicitar_detalles_script(nombre_archivo, modo_generico=False):
    """
    Solicita los detalles específicos de un script (descripción, uso, etc.).
    Si modo_generico es True, usa textos de ejemplo para evitar la entrada manual.
    """

    # Definiciones de texto por defecto para el modo Genérico
    DEF_DESCRIPCION = f"Script de propósito general: {os.path.splitext(nombre_archivo)[0].replace('_', ' ').title()}."
    DEF_USO = "Ejecutar directamente sin argumentos o usar -h para ayuda."
    DEF_PARAMETROS = "No aplica."
    DEF_RETORNO = "Código de salida estándar (0 en éxito)."
    DEF_NOTAS = "Metadatos pendientes de revisión y edición manual."

    if modo_generico:
        return {
            "descripcion": DEF_DESCRIPCION,
            "uso": DEF_USO,
            "parametros": DEF_PARAMETROS,
            "retorno": DEF_RETORNO,
            "notas": DEF_NOTAS,
        }

    # Modo Interactivo: pedir los datos al usuario
    print(f"\n--- Detalles para: {nombre_archivo} ---")

    descripcion = input(f"Descripción [Por defecto: {DEF_DESCRIPCION}]: ")
    uso = input(f"Ejemplo de Uso [Por defecto: {DEF_USO}]: ")

    # Para parámetros y retorno, hacemos la entrada un poco más visible
    print("\nArgumentos / Parámetros (deja en blanco si no aplica):")
    parametros = input(">>> ")

    retorno = input(f"Valor de Retorno [Por defecto: {DEF_RETORNO}]: ")
    notas = input(f"Notas Adicionales [Por defecto: {DEF_NOTAS}]: ")

    return {
        "descripcion": descripcion.strip() or DEF_DESCRIPCION,
        "uso": uso.strip() or DEF_USO,
        "parametros": parametros.strip() or DEF_PARAMETROS,
        "retorno": retorno.strip() or DEF_RETORNO,
        "notas": notas.strip() or DEF_NOTAS,
    }


def generar_encabezado(nombre_archivo, metadatos):
    """Genera el encabezado completo utilizando la plantilla y los metadatos."""
    hoy = date.today()

    # Quitar la extensión del nombre del archivo para usarlo como título principal
    nombre_base, _ = os.path.splitext(nombre_archivo)
    titulo_principal = nombre_base.replace("_", " ").title()

    # Plantilla del encabezado utilizando f-strings para sustitución limpia
    HEADER_TEMPLATE = f"""
{titulo_principal}
--------------------------------------------
Versión: 1.0
Fecha: {hoy.strftime("%Y-%m-%d")}
Autor: {metadatos["autor"]}
Licencia: GPLv3
Copyright (C) {hoy.strftime("%Y")}

Descripción:
    {metadatos["descripcion"]}

Uso:
    {metadatos["uso"]}

Argumentos / Parámetros:
{metadatos["parametros"]}

Retorno:
    {metadatos["retorno"]}

Notas:
    {metadatos["notas"]}

Licencia (GPLv3):
    Este programa es software gratuito: puedes redistribuirlo y/o modificarlo bajo los 
    términos de la Licencia Pública General GNU publicada por la Free Software Foundation, 
    ya sea la versión 3 de la Licencia o (a su elección) cualquier versión posterior.
    Este programa se distribuye con la esperanza de que sea útil, pero SIN NINGUNA GARANTÍA; 
    sin siquiera la garantía implícita de COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR. 
    Consulte la Licencia pública general de GNU para obtener más detalles.
    Debería haber recibido una copia de la Licencia Pública General GNU 
    junto con este programa. En caso contrario, consulte <https://www.gnu.org/licenses/>.
"""
    return HEADER_TEMPLATE.strip()


# Definición de los delimitadores de comentario para varios lenguajes
comentario_comun = {
    "inicio": "/*",
    "fin": "*/",
}
comentarios = {
    "txt": {"inicio": "", "fin": ""},
    "ts": comentario_comun,
    "js": comentario_comun,
    "ino": comentario_comun,  # Arduino/Processing
    "java": comentario_comun,
    "php": {"inicio": "<?php\n/*", "fin": "*/\n?>"},
    # El caso 'py' es especial ya que incluye el shebang y el docstring
    "py": {
        "inicio": '#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n"""',
        "fin": '"""',
    },
    "html": {"inicio": "<!--", "fin": "-->"},
    "go": comentario_comun,
    "c": comentario_comun,
    "cpp": comentario_comun,
}


def main():
    parser = argparse.ArgumentParser(
        description="Agrega un encabezado de metadatos y licencia GPLv3 a múltiples archivos."
    )
    parser.add_argument(
        "extension", help="Extensión de los archivos a modificar (ej: py, js, html)"
    )
    parser.add_argument(
        "directorio_archivos",
        help="Ubicación del directorio que tiene los archivos con la extensión indicada",
    )
    argumentos = parser.parse_args()

    if argumentos.extension not in comentarios:
        print(f"Error: Extensión '{argumentos.extension}' todavía no soportada.")
        sys.exit(-1)

    # 1. Solicitar Autor (Común y Obligatorio)
    autor = input(
        "Introduce tu Nombre y Contacto (ej: Iñaki Izaguerri <igizca@mail.com>): "
    )

    # 2. Elegir Modo de Procesamiento
    while True:
        modo = input(
            "\n¿Deseas aplicar metadatos Genéricos (G) a TODOS los scripts, o Interactivo (I) para cada uno? (G/I): "
        ).upper()
        if modo in ("G", "I"):
            break
        print("Opción no válida. Introduce G para Genérico o I para Interactivo.")

    if modo == "G":
        # En modo genérico, se recogen los detalles una sola vez (se usará el nombre base por defecto)
        print(
            "\nUsando modo GENÉRICO. Los campos serán rellenados con un texto por defecto que deberá editar manualmente después."
        )
        # Nota: Los metadatos específicos del script (descripción basada en el nombre) se generan dentro del bucle.

    # 3. Procesar archivos
    comentarios_archivo_actual = comentarios[argumentos.extension]
    directorio = argumentos.directorio_archivos

    try:
        os.chdir(directorio)
    except FileNotFoundError:
        print(f"Error: Directorio no encontrado: {directorio}")
        sys.exit(-1)

    archivos_procesados = 0

    for nombre_archivo in glob.glob("*." + argumentos.extension):
        # Determinar los metadatos a usar para este archivo
        if modo == "G":
            # 3.1. Usar los datos genéricos (con el nombre del archivo específico)
            # Re-generamos los metadatos genéricos para que la descripción
            # se actualice con el nombre de archivo correcto.
            metadatos_archivo = solicitar_detalles_script(
                nombre_archivo, modo_generico=True
            )
        else:
            # 3.2. Pide los datos específicos para este archivo
            metadatos_archivo = solicitar_detalles_script(
                nombre_archivo, modo_generico=False
            )

        # Combinar autor (constante) con los detalles del script
        metadatos_final = {"autor": autor, **metadatos_archivo}

        # 4. Generar el encabezado específico para este archivo
        encabezado = generar_encabezado(nombre_archivo, metadatos_final)

        # 5. Construir y escribir el contenido final
        ruta_completa = os.path.join(directorio, nombre_archivo)

        try:
            with open(ruta_completa, "r") as archivo:
                contenido_existente = archivo.read()

            contenido_final = (
                comentarios_archivo_actual["inicio"]
                + encabezado
                + comentarios_archivo_actual["fin"]
                + "\n\n"
                + contenido_existente
            )

            with open(ruta_completa, "w") as archivo:
                archivo.write(contenido_final)

            print(f"✅ Agregado encabezado a: {nombre_archivo}")
            archivos_procesados += 1

        except Exception as e:
            print(f"❌ Error al procesar {nombre_archivo}: {e}")

    print(f"\n--- Resumen: Se procesaron {archivos_procesados} archivos ---")


if __name__ == "__main__":
    main()
