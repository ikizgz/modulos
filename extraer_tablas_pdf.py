#!/usr/bin/env python3
"""
===============================================================================
Script de Extracción Masiva de Tablas Escaneadas (PDF a Excel con IA)
===============================================================================
Propósito:
    Este script procesa documentos PDF escaneados (incluso de cientos de páginas)
    donde los métodos tradicionales de extracción de texto fallan. Convierte
    cada página en imagen de alta resolución, la envía al modelo multimodal
    de Gemini para extraer las tablas con precisión milimétrica, y unifica
    todos los resultados en un único archivo Excel (.xlsx) limpio y estructurado,
    forzando que todos los campos se traten como texto para no perder ceros a la izquierda.

Requisitos previos:
    - Librerías instaladas: pip install google-genai pandas pymupdf openpyxl
    - Clave de API configurada (en el script o como variable de entorno).

Ejemplo de uso desde la terminal:
    python3 extraer_tablas_pdf.py --input "mi_escalafon.pdf" --output "resultado_final.xlsx"
    (Si omites el parámetro --output, se llamará automáticamente como el PDF original).

    python3 extraer_tablas_pdf.py --input "mi_escalafon.pdf" --max-paginas 5
    (Procesará únicamente las primeras 5 páginas, útil para pruebas rápidas).
===============================================================================
"""

from __future__ import annotations

import argparse
import io
import logging
import os
from collections.abc import Sequence

import fitz  # PyMuPDF
import pandas as pd
from google import genai
from google.genai import types

# Importación del módulo auxiliar centralizado
from logging_utils import setup_logging

# Logger instanciado a nivel de módulo
logger = logging.getLogger(__name__)


def procesar_pdf_a_excel(
    pdf_path: str,
    excel_output: str,
    api_key: str | None = None,
    max_paginas: int | None = None,
) -> None:
    """Función principal que gestiona la conversión de páginas y llamadas a la IA."""

    if not os.path.exists(pdf_path):
        logger.error(
            f"El archivo PDF de entrada no existe en la ruta especificada: {pdf_path}"
        )
        return

    logger.info(f"Iniciando apertura del documento PDF: '{pdf_path}'")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:  # noqa: BLE001
        logger.error(f"No se pudo abrir el archivo PDF. Error técnico: {e}")
        return

    total_paginas = len(doc)
    logger.info(f"PDF abierto con éxito. Total de páginas detectadas: {total_paginas}")

    # Inicializar el cliente de la API de Gemini
    # Si 'api_key' es None, la librería buscará automáticamente la variable de entorno GEMINI_API_KEY
    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error al inicializar el cliente de la API de Gemini: {e}")
        return

    lista_dataframes = []

    # Recorrer cada página del documento PDF
    if max_paginas:
        total_paginas = min(total_paginas, max_paginas)
        logger.info(
            f"Modo de prueba activo: procesando únicamente las primeras {total_paginas} páginas."
        )

    for i in range(total_paginas):
        page = doc[i]
        num_pag = i + 1
        logger.info(f"--- Procesando página {num_pag} de {total_paginas} ---")
        image_path = f"temp_pag_{num_pag}.png"

        try:
            # Rasterizar la página a imagen PNG con buena resolución (300 DPI)
            pix = page.get_pixmap(dpi=300)
            pix.save(image_path)

            # Prompt estructurado para guiar al modelo de visión
            prompt = """
            Analiza esta imagen escaneada de un documento de tabla de datos/escalafón. 
            Extrae toda la información de la tabla con absoluta precisión.
            Devuelve el resultado strictly en formato CSV (delimitado por comas), 
            donde la primera línea sean los encabezados de las columnas y las siguientes los registros. 
            No incluyas saludos, explicaciones, bloques de código markdown extra ni texto adicional, 
            únicamente el contenido tabular CSV limpio.
            """

            # Abrir la imagen usando un gestor de contexto para asegurar su cierre correcto
            with open(image_path, "rb") as img_file:
                imagen_bytes = img_file.read()

            # Llamada al modelo multimodal actual de Gemini
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=imagen_bytes,
                        mime_type="image/png",
                    ),
                ],
            )

            # Asegurar que response.text no sea None
            csv_data = response.text if response.text else ""

            # Limpiar posibles bloques de código markdown que a veces envuelve la IA (ej. ```csv ... ```)
            csv_data = csv_data.strip()
            if csv_data.startswith("```csv"):
                csv_data = csv_data[6:]
            elif csv_data.startswith("```"):
                csv_data = csv_data[3:]
            csv_data = csv_data.removesuffix("```")
            csv_data = csv_data.strip()

            # Leer el CSV asegurando que todo sea texto (dtype=str) para preservar ceros a la izquierda
            df_pagina = pd.read_csv(io.StringIO(csv_data), dtype=str)

            if not df_pagina.empty:
                lista_dataframes.append(df_pagina)
                logger.info(
                    f"Página {num_pag} procesada con éxito ({len(df_pagina)} filas extraídas)."
                )
            else:
                logger.warning(
                    f"La página {num_pag} no devolvió datos tabulares válidos."
                )

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error crítico al procesar la página {num_pag}: {e}")

        finally:
            # Limpieza obligatoria de la imagen temporal generada en disco
            if os.path.exists(image_path):
                os.remove(image_path)

    # Unir todas las tablas recopiladas y exportar al archivo Excel final
    if lista_dataframes:
        logger.info("Consolidando todas las páginas en una única estructura...")
        df_final = pd.concat(lista_dataframes, ignore_index=True)

        try:
            df_final.to_excel(excel_output, index=False)
            logger.info(
                f"¡Proceso completado con éxito! Archivo Excel guardado en: '{excel_output}'"
            )
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error al intentar guardar el archivo Excel final: {e}")
    else:
        logger.warning(
            "No se ha podido extraer información de ninguna página del documento."
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script automatizado para extraer tablas de PDFs escaneados masivos utilizando Google Gemini y exportarlas a Excel."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Ruta del archivo PDF escaneado que deseas procesar (ej: --input documento.pdf)",
    )
    parser.add_argument(
        "--max-paginas",
        "-m",
        type=int,
        required=False,
        help="Número máximo de páginas a procesar (opcional, útil para pruebas).",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=False,
        help="Ruta o nombre del archivo Excel de salida (opcional). Por defecto usará el mismo nombre del PDF.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Nivel de detalle del log (por defecto: INFO)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    # Configuración centralizada de logging
    log_level = getattr(logging, args.log_level.upper())
    setup_logging(app_name="extraer_tablas_pdf", level=log_level)

    # Determinar dinámicamente el nombre de salida si no se proporciona explícitamente
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(args.input)[0]
        output_file = f"{base_name}.xlsx"

    # Clave de API configurada
    MI_API_KEY = "AQ.Ab8RN6IY9HJaAxjIGewqFDEhk2FljyPRkdZLfRYivuRRdUL8CA"

    procesar_pdf_a_excel(
        pdf_path=args.input,
        excel_output=output_file,
        api_key=MI_API_KEY,
        max_paginas=args.max_paginas,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
