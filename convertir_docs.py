#!/usr/bin/env python3

"""
convertir_docs.py
----------------
Conversión recursiva de documentos antiguos a formatos modernos (DOCX o PDF)
usando LibreOffice en modo headless con registro centralizado de LOGS.

FUNCIONALIDADES:
 - Conversión recursiva que respeta la estructura de carpetas.
 - Entrada por argumentos o diálogo interactivo (--origen, --destino).
 - Soporta: DEFAULT_EXTS = {".doc", ".dot", ".rtf"} (ampliable con --ext).
 - Conversión a DOCX o PDF (mediante --to).
 - Multiproceso opcional (--workers N).
 - Borrar el archivo original tras una conversión exitosa (--delete-original).
 - Mantener fecha de modificación original (--keep-time).
 - Reintentos en caso de fallos (MAX_REINTENTOS = 2 intentos por archivo).
 - Saltarse archivos ya convertidos.
 - Log de progreso (tqdm).
 - Multiplataforma (Linux, Windows, macOS).
 - Personalizable y extensible.


USO BÁSICO:
    python3 convertir_docs.py --origen /carpeta/origen --destino /carpeta/salida

CON MULTIPROCESO:
    python3 convertir_docs.py --origen /docs --destino /out --workers 4

CONVERSIÓN A PDF:
    python3 convertir_docs.py --origen /docs --destino /out --to pdf

EXTENDER TIPOS DE ARCHIVO:
    python3 convertir_docs.py --origen /docs --destino /out --ext .wps,.wpd

ESPECIFICAR RUTA SOFFICE:
    python3 convertir_docs.py --soffice "/usr/lib/libreoffice/program/soffice"

Autor: Iñaki Izaguerri.
Copyright (C) 2026 Iñaki Izaguerri

Licencia: GPLv3
Este programa es software libre: puedes redistribuirlo y/o modificarlo
bajo los términos de la Licencia Pública General GNU publicada por la
Free Software Foundation, ya sea la versión 3 de la Licencia, o
(cualquier versión posterior).
Este programa se distribuye con la esperanza de que sea útil,
pero SIN NINGUNA GARANTÍA; sin siquiera la garantía implícita de
COMERCIALIZACIÓN o IDONEIDAD PARA UN PROPÓSITO PARTICULAR.
Deberías haber recibido una copia de la Licencia Pública General GNU
junto con este programa. Si no, visita <https://www.gnu.org/licenses/>.
"""

import argparse
import logging
import multiprocessing
import os
import platform  # para detectar el sistema operativo
import shutil  # para mover archivos
import subprocess
import tempfile  # para usar una carpeta temporal local
from functools import partial
from pathlib import Path

from tqdm import tqdm

# logging_utils.py es un módulo auxiliar para configurar el logging de manera centralizada
from logging_utils import setup_logging

# ------------------------------
# CONFIGURACIÓN
# ------------------------------
DEFAULT_EXTS = {".doc", ".dot", ".rtf"}
MAX_REINTENTOS = 2


def filtro_para(formato_out):
    """Devuelve el filtro adecuado de LibreOffice según formato destino."""
    formato_out = formato_out.lower()
    if formato_out == "docx":
        return "docx:Office Open XML Text"
    elif formato_out == "pdf":
        return "pdf:writer_pdf_Export"
    else:
        raise ValueError(f"Formato de salida no soportado: {formato_out}")


# ------------------------------
# FUNCIÓN DE CONVERSIÓN
# ------------------------------
def convertir_archivo(src, source_root, target_root, soffice, keep_time, filtro):
    rel = Path(src).relative_to(source_root)
    outdir = target_root / rel.parent
    outdir.mkdir(parents=True, exist_ok=True)

    ext_dest = filtro.split(":")[0]  # docx o pdf
    outfile = outdir / (Path(src).stem + f".{ext_dest}")

    if outfile.exists():
        return (src, "skip", "Ya existía el archivo de salida")

    # CONVERSIÓN EN LOCAL (Rápida y segura)
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = [
            soffice,
            "--headless",
            "--convert-to",
            filtro,
            "--outdir",
            tmpdir,
            str(src),
        ]

        for intento in range(1, MAX_REINTENTOS + 1):
            res = subprocess.run(cmd, capture_output=True, text=True)

            # Comprobamos si se generó en el Temp local
            tmp_outfile = Path(tmpdir) / (Path(src).stem + f".{ext_dest}")

            if tmp_outfile.exists() and res.returncode == 0:
                try:
                    # Python se encarga del envío limpio a la red
                    shutil.move(str(tmp_outfile), str(outfile))
                    if keep_time:
                        ts = os.path.getmtime(src)
                        os.utime(outfile, (ts, ts))
                    return (src, "ok", f"Convertido en intento {intento}")
                except Exception as e:  # noqa: BLE001
                    return (src, "fail", f"Error al mover al destino: {e!s}")

        return (
            src,
            "fail",
            f"Fallo en conversión (Returncode={res.returncode}, stderr={res.stderr.strip()})",
        )


# ------------------------------
# LISTAR ARCHIVOS
# ------------------------------
def listar_archivos(origen, extensiones):
    lista = []
    for root, _, files in os.walk(origen):
        for f in files:
            suf = Path(f).suffix.lower()
            if suf in extensiones and not f.lower().endswith(".docx"):
                lista.append(os.path.join(root, f))
    return lista


# ------------------------------
# MAIN
# ------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Conversión recursiva DOC/DOT/RTF → DOCX o PDF usando LibreOffice."
    )

    # 1. Detectar la ruta por defecto según el Sistema Operativo
    if platform.system() == "Windows":
        # Rutas típicas en Windows (64-bit y 32-bit)
        ruta_64 = r"C:\Program Files\LibreOffice\program\soffice.exe"
        ruta_32 = r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"

        if os.path.exists(ruta_64):
            soffice_default = ruta_64
        elif os.path.exists(ruta_32):
            soffice_default = ruta_32
        else:
            soffice_default = "soffice.exe"  # Si no se encuentra, dejamos el fallback
    else:
        # Linux / macOS
        soffice_default = "soffice"

    parser.add_argument("--origen", help="Carpeta origen")
    parser.add_argument("--destino", help="Carpeta destino")
    parser.add_argument("--ext", help="Extensiones extra (.wps,.wpd)", default="")
    parser.add_argument("--workers", type=int, default=1, help="Procesos paralelos")
    parser.add_argument("--to", default="docx", help="Formato de salida: docx o pdf")
    parser.add_argument(
        "--keep-time", action="store_true", help="Mantener fecha original"
    )
    parser.add_argument(
        "--delete-original",
        action="store_true",
        help="Borrar el archivo original tras una conversión exitosa",
    )
    # 2. Usar la variable detectada como 'default' para el argumento --soffice
    parser.add_argument("--soffice", default=soffice_default, help="Ruta a soffice")

    args = parser.parse_args()

    if not args.origen:
        user_input = input("Carpeta de origen [por defecto: ./]: ").strip()
        # Si el usuario pulsa Intro sin mirar, le asignamos './'
        args.origen = user_input if user_input else "./"

    if not args.destino:
        user_input = input("Carpeta de destino [por defecto: ./]: ").strip()
        # Si el usuario pulsa Intro sin mirar, le asignamos './'
        args.destino = user_input if user_input else "./"

    # Validación y resolución segura de rutas
    try:
        origen = Path(args.origen).expanduser().resolve()
        destino = Path(args.destino).expanduser().resolve()

        # Comprobar primero si la carpeta origen realmente existe
        if not origen.exists():
            print(f"❌ Error: La carpeta de origen no existe:\n   '{origen}'")
            return 1

        if not origen.is_dir():
            print(
                f"❌ Error: La ruta de origen especificada no es un directorio válido:\n   '{origen}'"
            )
            return 1

        # Intentar crear la carpeta destino de forma segura
        destino.mkdir(parents=True, exist_ok=True)

    except (OSError, FileNotFoundError) as e:
        print("\n" + "!" * 70)
        print(
            "❌ ERROR CRÍTICO: La sintaxis o los caracteres de las rutas no son válidos."
        )
        print(f"   Detalle del sistema: {e}")
        print(
            "   Por favor, revisa que no hayas duplicado letras de unidad (ej. U:) o metido caracteres prohibidos."
        )
        print("!" * 70 + "\n")
        return 1

    # ¡Ahora pasamos la carpeta destino directamente aquí habiendo asegurado que es correcta!
    setup_logging(app_name="convertir_docs", target_dir=destino)

    extensiones = set(DEFAULT_EXTS)
    if args.ext:
        extensiones |= {e.strip().lower() for e in args.ext.split(",")}

    filtro = filtro_para(args.to)

    logging.info("🔍 Escaneando archivos de origen...")
    archivos = listar_archivos(origen, extensiones)
    logging.info(f"Se encontraron {len(archivos)} archivos aptos para procesar.")

    f_convertir = partial(
        convertir_archivo,
        source_root=origen,
        target_root=destino,
        soffice=args.soffice,
        keep_time=args.keep_time,
        filtro=filtro,
    )

    resultados = []

    if args.workers > 1:
        logging.info(f"⚡ Iniciando multiproceso con {args.workers} workers...")
        with multiprocessing.Pool(args.workers) as pool:
            for r in tqdm(
                pool.imap_unordered(f_convertir, archivos), total=len(archivos)
            ):
                resultados.append(r)
    else:
        logging.info("Modo secuencial activo…")
        for src in tqdm(archivos):
            resultados.append(f_convertir(src))

    # Volcar todos los resultados de la conversión al archivo de registro
    for src_path, estado, detalle in resultados:
        msg = f"Archivo: {src_path} | Estado: [{estado.upper()}] | Detalle: {detalle}"
        if estado == "ok" or estado == "skip":
            logging.info(msg)
        else:
            logging.error(msg)

    # Post-procesado seguro: Borrado de archivos originales si se activa la flag
    deleted_count = 0
    if args.delete_original:
        logging.info(
            "🗑️  Iniciando proceso de limpieza de archivos originales convertidos..."
        )
        for src_path, estado, _ in resultados:
            if estado == "ok":
                try:
                    os.remove(src_path)
                    deleted_count += 1
                    logging.info(f"Eliminado original correctamente: {src_path}")
                except Exception as e:
                    logging.error(
                        f"❌ Error crítico al intentar eliminar {src_path}. Detalle del sistema: {e}",
                        exc_info=True,
                    )

    oks = sum(1 for r in resultados if r[1] == "ok")
    fails = sum(1 for r in resultados if r[1] == "fail")
    skips = sum(1 for r in resultados if r[1] == "skip")

    # Resumen final
    logging.info("===== RESUMEN DE EJECUCIÓN =====")
    logging.info(f"✔ Correctos : {oks}")
    if args.delete_original:
        logging.info(f"🗑  Borrados  : {deleted_count}")
        if deleted_count < oks:
            logging.warning(
                f"⚠️  Atención: {oks - deleted_count} archivos 'ok' no pudieron ser eliminados. Revisa los errores previos."
            )
    logging.info(f"↷ Saltados  : {skips}")
    logging.info(f"❌ Fallidos  : {fails}")
    logging.info("¡Proceso finalizado! 🎉")


if __name__ == "__main__":
    main()
