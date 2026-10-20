#!/usr/bin/env python3
"""
===============================================================================
Script de Generación de Capa de Texto OCR para PDFs Escaneados Problemáticos
===============================================================================
Propósito:
    Este script procesa documentos PDF escaneados con baja calidad de tinta,
    fondos sucios o descoloridos (como documentos antiguos). Aplica técnicas
    de preprocesamiento de imagen con OpenCV (umbral adaptativo y reducción
    de ruido) para maximizar el contraste, ejecuta OCR con Tesseract, y
    genera un nuevo PDF searchable que conserva la imagen original pero
    con una capa de texto transparente seleccionable y buscable.

Requisitos previos:
    - Librerías: pip install pymupdf opencv-python pytesseract pillow
    - Tesseract-OCR instalado en el sistema operativo y accesible en el PATH.

Ejemplo de uso desde la terminal:
    python3 ocr_pdf.py --input "archivo.pdf" --output "archivo_ocr.pdf"

    (Si omites el parámetro --output, se llamará automáticamente añadiendo "_ocr.pdf").

    python3 ocr_pdf.py --input "archivo.pdf" --max-paginas 3
    (Procesará únicamente las primeras 3 páginas para pruebas rápidas).
===============================================================================
"""

from __future__ import annotations

import argparse
import logging
import os
from collections.abc import Sequence

import cv2
import fitz  # PyMuPDF
import pytesseract
from PIL import Image

# Importación del módulo auxiliar centralizado de logs
from logging_utils import setup_logging

# Logger instanciado a nivel de módulo
logger = logging.getLogger(__name__)


def optimizar_imagen_para_ocr(image_path: str) -> str:
    """
    Aplica técnicas de procesamiento de imagen con OpenCV para mejorar
    drásticamente el contraste en documentos con baja tinta o fondos sucios.
    """
    # Leer la imagen en escala de grises
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        logger.error(f"No se pudo cargar la imagen para optimizar: {image_path}")
        return image_path

    # 1. Reducir ruido conservando los bordes del texto
    img_denoised = cv2.fastNlMeansDenoising(img, h=30)

    # 2. Binarización adaptativa (Thresholding): Convierte a blanco y negro puro
    # adaptándose a las zonas más oscuras o claras de la página escaneada.
    img_thresh = cv2.adaptiveThreshold(
        img_denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,  # Tamaño de vecindad para calcular el umbral
        C=15,  # Constante para limpiar fondos grises
    )

    processed_path = "temp_processed.png"
    cv2.imwrite(processed_path, img_thresh)
    return processed_path


def convertir_pdf_a_buscable(
    pdf_entrada: str, pdf_salida: str, max_paginas: int | None = None
) -> None:
    """Función principal que gestiona la apertura, optimización y OCR por páginas."""

    if not os.path.exists(pdf_entrada):
        logger.error(
            f"El archivo PDF de entrada no existe en la ruta especificada: {pdf_entrada}"
        )
        return

    logger.info(f"Iniciando apertura del documento PDF: '{pdf_entrada}'")

    try:
        doc_original = fitz.open(pdf_entrada)
    except Exception as e:  # noqa: BLE001
        logger.error(f"No se pudo abrir el archivo PDF. Error técnico: {e}")
        return

    total_paginas = len(doc_original)
    logger.info(f"PDF abierto con éxito. Total de páginas detectadas: {total_paginas}")

    if max_paginas:
        total_paginas = min(total_paginas, max_paginas)
        logger.info(
            f"Modo de prueba activo: procesando únicamente las primeras {total_paginas} páginas."
        )

    # Crear un documento PDF vacío donde iremos añadiendo las páginas con capa de texto
    doc_salida = fitz.open()

    for i in range(total_paginas):
        page = doc_original[i]
        num_pag = i + 1
        logger.info(
            f"--- Procesando y mejorando OCR de la página {num_pag} de {total_paginas} ---"
        )

        temp_img = f"temp_page_{num_pag}.png"
        processed_img = "temp_processed.png"

        try:
            # 1. Rasterizar página a alta resolución (300 DPI)
            pix = page.get_pixmap(dpi=300)
            pix.save(temp_img)

            # 2. Preprocesar la imagen con OpenCV para solucionar el problema de la tinta tenue
            imagen_limpia_path = optimizar_imagen_para_ocr(temp_img)

            # 3. Generar PDF con capa de texto usando Tesseract (formato PDF searchable)
            with Image.open(imagen_limpia_path) as img_pil:
                pdf_bytes_tesseract = pytesseract.image_to_pdf_or_hocr(
                    img_pil,
                    extension="pdf",
                    lang="spa",  # Idioma español para mejorar el diccionario del OCR
                )

            # 4. Fusionar la página procesada en el documento final de salida
            with fitz.open(
                stream=pdf_bytes_tesseract, filetype="pdf"
            ) as pagina_pdf_temporal:
                doc_salida.insert_pdf(pagina_pdf_temporal)

            logger.info(
                f"Página {num_pag} procesada y añadida al PDF searchable con éxito."
            )

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error crítico al procesar la página {num_pag} con OCR: {e}")

        finally:
            # Limpieza obligatoria de archivos temporales de esta página
            for archivo in [temp_img, processed_img]:
                if os.path.exists(archivo):
                    os.remove(archivo)

    try:
        doc_salida.save(pdf_salida)
        logger.info(
            f"¡Proceso completado con éxito! PDF con capa de texto guardado como: '{pdf_salida}'"
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error al intentar guardar el PDF final: {e}")
    finally:
        doc_salida.close()
        doc_original.close()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script para convertir PDFs escaneados problemáticos en PDFs con capa de texto seleccionable usando OpenCV y Tesseract."
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Ruta del archivo PDF escaneado que deseas procesar (ej: --input Escalafon.pdf)",
    )
    parser.add_argument(
        "--max-paginas",
        "-m",
        type=int,
        required=False,
        help="Número máximo de páginas a procesar (opcional, útil para pruebas rápidas).",
    )
    parser.add_argument(
        "--output",
        "-o",
        required=False,
        help="Ruta o nombre del PDF de salida (opcional). Por defecto añadirá '_ocr.pdf'.",
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

    # Configuración centralizada de logging idéntica a tus otros scripts
    log_level = getattr(logging, args.log_level.upper())
    setup_logging(app_name="ocr_pdf", level=log_level)

    # Determinar dinámicamente el nombre de salida si no se proporciona
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(args.input)[0]
        output_file = f"{base_name}_ocr.pdf"

    convertir_pdf_a_buscable(
        pdf_entrada=args.input,
        pdf_salida=output_file,
        max_paginas=args.max_paginas,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
