# -*- coding: utf-8 -*-
# logging_utils.py

import logging
import os
import sys
from datetime import datetime


def setup_logging(app_name: str = "app"):
    """
    Configura logging en consola + archivo logs/<app_name>_YYYYMMDD_HHMMSS.log

    app_name: nombre base del archivo de log (ej. "actualizar_bd", "preprocesador")
    """

    # Crear directorio logs si no existe
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Archivo nuevo para cada ejecución
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{app_name}_{timestamp}.log")

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Muy importante: limpiar handlers previos
    if logger.hasHandlers():
        logger.handlers.clear()

    # Formatos
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")

    # Handler archivo
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Handler consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logging.info(f"*** Logging configurado. Archivo: {log_path} ***")
