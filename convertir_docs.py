#!/usr/bin/env python3
"""
convertir_docs.py
----------------
Conversión recursiva de documentos antiguos a formatos modernos (DOCX o PDF)
usando LibreOffice en modo headless.

FUNCIONALIDADES:
 - Conversión recursiva que respeta la estructura de carpetas.
 - Entrada por argumentos o diálogo interactivo (--origen, --destino).
 - Soporta: .doc, .dot, .rtf (ampliable con --ext).
 - Conversión a DOCX o PDF mediante --to.
 - Multiproceso opcional (--workers N).
 - Log de progreso (tqdm).
 - Archivo CSV con resultados (--csv).
 - Reintentos en caso de fallos (2 intentos por archivo).
 - Saltarse archivos ya convertidos.
 - Mantener fecha de modificación original (--keep-time).
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
import csv
import multiprocessing
import os
import platform  # para detectar el sistema operativo
import shutil  # para mover archivos
import subprocess
import tempfile  # para usar una carpeta temporal local
from functools import partial
from pathlib import Path

from tqdm import tqdm

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
        return (src, "skip", "Ya existía")

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
                    return (src, "ok", f"Intento {intento}")
                except Exception as e:
                    return (src, "fail", f"Error al mover al destino: {str(e)}")

        return (
            src,
            "fail",
            f"Returncode={res.returncode}, stderr={res.stderr.strip()}",
        )


# ------------------------------
# LISTAR ARCHIVOS
# ------------------------------
def listar_archivos(origen, extensiones):
    lista = []
    for root, _, files in os.walk(origen):
        for f in files:
            suf = Path(f).suffix.lower()
            if suf in extensiones:
                if not f.lower().endswith(".docx"):
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

    # 2. Usar la variable detectada como 'default'
    parser.add_argument("--soffice", default=soffice_default, help="Ruta a soffice")
    parser.add_argument(
        "--csv",
        default="resultado_conversion.csv",
        help="Informe en CSV (se guardará en la carpeta destino si es un nombre relativo)",
    )

    args = parser.parse_args()

    if not args.origen:
        args.origen = input("Carpeta de origen: ").strip()
    if not args.destino:
        args.destino = input("Carpeta de destino: ").strip()

    origen = Path(args.origen).expanduser().resolve()
    destino = Path(args.destino).expanduser().resolve()
    destino.mkdir(parents=True, exist_ok=True)
    # Enrutar el CSV a la carpeta destino
    ruta_csv = Path(args.csv)
    # Si el usuario no ha puesto una ruta absoluta (ej. C:\informe.csv),
    # lo metemos dentro de la carpeta destino
    if not ruta_csv.is_absolute():
        ruta_csv = destino / ruta_csv

    extensiones = set(DEFAULT_EXTS)
    if args.ext:
        extensiones |= {e.strip().lower() for e in args.ext.split(",")}

    filtro = filtro_para(args.to)

    print("\n🔍 Escaneando archivos...")
    archivos = listar_archivos(origen, extensiones)
    print(f"Se encontraron {len(archivos)} archivos.\n")

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
        print(f"⚡ Usando {args.workers} procesos...")
        with multiprocessing.Pool(args.workers) as pool:
            for r in tqdm(
                pool.imap_unordered(f_convertir, archivos), total=len(archivos)
            ):
                resultados.append(r)
    else:
        print("Modo secuencial…")
        for src in tqdm(archivos):
            resultados.append(f_convertir(src))

    # Guardar CSV
    print(f"\n📄 Guardando CSV en {ruta_csv} ...")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "estado", "detalle"])
        for fila in resultados:
            w.writerow(fila)

    oks = sum(1 for r in resultados if r[1] == "ok")
    fails = sum(1 for r in resultados if r[1] == "fail")
    skips = sum(1 for r in resultados if r[1] == "skip")

    print("\n===== RESUMEN =====")
    print(f"✔ Correctos : {oks}")
    print(f"↷ Saltados  : {skips}")
    print(f"❌ Fallidos  : {fails}")
    print("\n¡Finalizado! 🎉")


if __name__ == "__main__":
    main()
