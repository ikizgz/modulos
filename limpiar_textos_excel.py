#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Limpia en un Excel TODAS las columnas de texto en las N primeras hojas (por defecto 1)
**sin recrear hojas** (edición IN-PLACE con openpyxl), para **preservar** objetos de Excel como
tablas dinámicas en otras hojas. Convierte a MAYÚSCULAS, elimina acentos y
caracteres no imprimibles, **respetando la Ñ** (que queda como Ñ mayúscula).
Permite EXCLUIR columnas específicas para que no sean procesadas.

USO RÁPIDO
----------
    python limpiar_textos_excel.py --input excel.xlsx \
                                   --output excel_LIMPIO.xlsx
    # Si no indicas --dry-run, preguntará por consola (s/n).

OPCIONES CLI
------------
--input, -i        Ruta del Excel de entrada.
                   Por defecto: "excel.xlsx"

--output, -o       Ruta del Excel de salida.
                   Por defecto: "excel_LIMPIO.xlsx"

--dry-run {on|off} Ejecuta en modo simulación (no guarda cambios) o guarda directamente.
                   - on  : Simulación (NO guarda, muestra lo que haría).
                   - off : Guarda cambios (crea backup del original).
                   Si no se indica, el script PREGUNTA por consola.

--sheets N         Nº de hojas iniciales a procesar (por orden del libro). Por defecto: 1.

--header-scan-rows N
                   Nº de filas superiores donde buscar la fila de cabecera. Por defecto: 5.

--samples N        Nº de ejemplos (antes → después) a mostrar por hoja. Por defecto: 5.

--exclude, -e      Lista de nombres de columnas a EXCLUIR de la limpieza (separados por espacios).
                   Ejemplo: -e ID Fecha Cantidad

--no-collapse-spaces
                   Desactiva la normalización de espacios (por defecto se colapsan múltiples
                   espacios y NBSP a un único espacio y se recortan extremos).

EJEMPLOS
--------
1) Preguntar por dry-run, limpiar todo excepto "ID" y "Fecha":
   python limpiar_textos_excel.py -i excel.xlsx -e ID Fecha

2) Forzar simulación sin excluir nada (limpia todas las columnas encontradas):
   python limpiar_textos_excel.py -i excel.xlsx -o out.xlsx --dry-run on

NOTAS
-----
- Se modifican de forma dinámica todas las columnas de la cabecera detectada que no estén excluidas.
- Se ignoran celdas combinadas no-maestras (MergedCell), ya que no admiten escritura.

Autor: Iñaki Izaguerri.
Licencia: GPLv3
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple, Dict

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.worksheet.worksheet import Worksheet

# ------------------- CONSTANTES POR DEFECTO -------------------
DEFAULT_INPUT_FILE = "excel.xlsx"
DEFAULT_OUTPUT_FILE = "excel_LIMPIO.xlsx"
NUM_SHEETS_TO_PROCESS = 1
HEADER_SCAN_ROWS = 5
COLLAPSE_SPACES = True
SHOW_SAMPLES_PER_SHEET = 5
DEFAULT_EXCLUDES: List[str] = []  # Columnas a excluir por defecto si se desea
# --------------------------------------------------------------


# ------------------- ESTRUCTURAS DE INFORME -------------------
@dataclass
class SheetReport:
    sheet_name: str
    header_row: Optional[int] = None
    columns_processed: List[str] = field(default_factory=list)
    rows_with_changes: int = 0
    total_cells_changed: int = 0
    samples: List[Tuple[str, int, str, str]] = field(default_factory=list)


# --------------------------------------------------------------


# -------------------- UTILIDADES DE TEXTO ---------------------
def _to_text(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(
        value, (str, bool, int, float, Decimal, datetime, date, time, timedelta)
    ):
        return str(value)
    try:
        return str(value)
    except Exception:
        return None


def limpiar_texto(texto_in: object | None) -> str | None:
    """Normaliza texto:
    - Protege Ñ/ñ y elimina diacríticos (queda Ñ).
    - Convierte a MAYÚSCULAS.
    - Elimina no imprimibles.
    - Colapsa espacios y NBSP si COLLAPSE_SPACES=True.
    """
    texto = _to_text(texto_in)
    if texto is None:
        return None
    texto = texto.replace("Ñ", "__ENIE_MAYUS__").replace("ñ", "__ENIE_MINUS__")
    texto = "".join(
        c
        for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = texto.replace("__ENIE_MAYUS__", "Ñ").replace("__ENIE_MINUS__", "Ñ")
    texto = texto.upper()
    texto = "".join(c for c in texto if c.isprintable())
    if COLLAPSE_SPACES:
        texto = re.sub(r"[ \t\u00A0]+", " ", texto).strip()
    return texto


# --------------------------------------------------------------


# ------------------ LOCALIZACIÓN DE CABECERAS -----------------
def find_header_row(ws: Worksheet, scan_rows: int) -> Optional[int]:
    """Devuelve la fila (1-based) que parece contener la cabecera.
    Considera que es una cabecera si la fila tiene celdas con texto."""
    max_scan = min(ws.max_row, scan_rows)
    for r in range(1, max_scan + 1):
        # Si la fila contiene al menos algún valor de texto no vacío, la asumimos como cabecera
        if any(cell.value is not None and str(cell.value).strip() != "" for cell in ws[r]):
            return r
    return None


def get_active_columns(
    ws: Worksheet, header_row: int, exclude_headers: Sequence[str]
) -> Dict[int, str]:
    """Mapea el índice de la columna (1-based) con su nombre de cabecera,
    excluyendo las solicitadas por el usuario."""
    exclude_lower = {h.strip().lower() for h in exclude_headers}
    columns_map: Dict[int, str] = {}
    
    for cell in ws[header_row]:
        raw = cell.value
        if raw is not None:
            header_name = str(raw).strip()
            if header_name.lower() not in exclude_lower and cell.column is not None:
                columns_map[cell.column] = header_name
                
    return columns_map


# --------------------------------------------------------------


# ------------------------- BACKUP ------------------------------
def backup_file(path: str) -> str:
    """Crea una copia de seguridad con timestamp y devuelve su ruta."""
    base, ext = os.path.splitext(path)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{base}_BACKUP_{ts}{ext}"
    shutil.copy2(path, backup_path)
    return backup_path


# --------------------------------------------------------------


# ------------------ PROCESADO DE CADA HOJA --------------------
def process_sheet(
    ws: Worksheet,
    sheet_index: int,
    dry_run: bool,
    show_samples: int,
    exclude_headers: Sequence[str],
) -> SheetReport:
    """Procesa una hoja limpiando todas las columnas excepto las excluidas."""
    report = SheetReport(sheet_name=ws.title)

    header_row = find_header_row(ws, HEADER_SCAN_ROWS)
    if header_row is None:
        print(
            f"  ⚠️  [{sheet_index}] '{ws.title}': no se encontró fila de cabecera (1..{HEADER_SCAN_ROWS}). Omitida."
        )
        return report

    columns_to_process = get_active_columns(ws, header_row, exclude_headers)
    report.header_row = header_row
    report.columns_processed = list(columns_to_process.values())

    if not columns_to_process:
        print(
            f"  ⚠️  [{sheet_index}] '{ws.title}': no quedan columnas para procesar tras aplicar exclusiones. Omitida."
        )
        return report

    max_row = ws.max_row
    for r in range(header_row + 1, max_row + 1):
        row_changed = False

        for col_idx, col_name in columns_to_process.items():
            cell = ws.cell(row=r, column=col_idx)
            
            # Evitar celdas combinadas no-maestras
            if not isinstance(cell, MergedCell):
                before = cell.value
                # Solo procesamos si hay contenido de texto real
                if before is not None and str(before).strip() != "":
                    after = limpiar_texto(before)
                    if after != before:
                        if not dry_run:
                            cell.value = after
                        report.total_cells_changed += 1
                        row_changed = True
                        if len(report.samples) < show_samples:
                            report.samples.append(
                                (col_name, r, str(before), str(after))
                            )

        if row_changed:
            report.rows_with_changes += 1

    return report


# --------------------------------------------------------------


# ------------------------- CLI / MAIN -------------------------
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Limpia todas las columnas de texto en las N primeras hojas de un Excel (in-place) excepto las excluidas."
    )
    parser.add_argument(
        "--input", "-i", default=DEFAULT_INPUT_FILE, help="Ruta del Excel de entrada"
    )
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT_FILE, help="Ruta del Excel de salida"
    )
    parser.add_argument(
        "--dry-run",
        choices=("on", "off"),
        help="Simulación sin guardar cambios (on/off). Si no se indica, se preguntará interactivo.",
    )
    parser.add_argument(
        "--sheets",
        type=int,
        default=NUM_SHEETS_TO_PROCESS,
        help=f"Número de hojas iniciales a procesar (por defecto {NUM_SHEETS_TO_PROCESS})",
    )
    parser.add_argument(
        "--header-scan-rows",
        type=int,
        default=HEADER_SCAN_ROWS,
        help=f"Filas superiores a escanear en busca de cabecera (por defecto {HEADER_SCAN_ROWS})",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=SHOW_SAMPLES_PER_SHEET,
        help=f"Nº de muestras a mostrar por hoja (por defecto {SHOW_SAMPLES_PER_SHEET})",
    )
    parser.add_argument(
        "--exclude", "-e",
        nargs="+",
        default=DEFAULT_EXCLUDES,
        help="Lista de cabeceras de columnas a EXCLUIR del procesado (separadas por espacios)",
    )
    parser.add_argument(
        "--no-collapse-spaces",
        action="store_true",
        help="No colapsar espacios múltiples (por defecto se colapsan)",
    )
    return parser.parse_args(argv)


def ask_dry_run() -> bool:
    """Pregunta interactiva si ejecutar en dry-run. Devuelve True si dry-run."""
    while True:
        ans = (
            input("¿Ejecutar en modo simulación (dry-run) sin guardar? [s/n]: ")
            .strip()
            .lower()
        )
        if ans in ("s", "si", "sí"):
            return True
        if ans in ("n", "no"):
            return False
        print("Respuesta no válida. Escribe 's' o 'n'.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    global COLLAPSE_SPACES, HEADER_SCAN_ROWS
    COLLAPSE_SPACES = not args.no_collapse_spaces
    HEADER_SCAN_ROWS = args.header_scan_rows

    input_file: str = args.input
    output_file: str = args.output
    sheets_to_process: int = max(0, args.sheets)
    exclude_headers: List[str] = args.exclude

    if args.dry_run == "on":
        dry_run = True
    elif args.dry_run == "off":
        dry_run = False
    else:
        dry_run = ask_dry_run()

    print("────────────────────────────────────────────────────────────────")
    print(" Limpieza dinámica de texto en Excel (in‑place, preserva pivots)")
    print("────────────────────────────────────────────────────────────────")
    print(f"Archivo de entrada  : {input_file}")
    print(f"Archivo de salida   : {output_file}")
    print(f"Dry-run (simulación): {dry_run}")
    print(f"Colapsar espacios   : {COLLAPSE_SPACES}")
    print(f"Hojas a procesar    : {sheets_to_process} primeras")
    if exclude_headers:
        print(f"Columnas excluidas  : {', '.join(exclude_headers)}")
    else:
        print("Columnas excluidas  : Ninguna (se procesará todo)")
    print("────────────────────────────────────────────────────────────────")

    if not os.path.exists(input_file):
        print(f"❌ No se encuentra el archivo de entrada: {input_file}")
        return 1

    if not dry_run:
        backup_path = backup_file(input_file)
        print(f"🛡  Backup creado    : {backup_path}")

    wb = load_workbook(input_file)
    sheetnames: List[str] = list(wb.sheetnames)

    if sheets_to_process <= 0:
        print("⚠️  Número de hojas a procesar es 0. Nada que hacer.")
        return 0

    to_process = sheetnames[: min(sheets_to_process, len(sheetnames))]
    reports: List[SheetReport] = []

    for idx, sname in enumerate(to_process, start=1):
        ws: Worksheet = wb[sname]
        print(f"\n→ Procesando [{idx}] hoja '{sname}' ...")
        rep = process_sheet(ws, idx, dry_run=dry_run, show_samples=args.samples, exclude_headers=exclude_headers)
        reports.append(rep)

        if rep.header_row is None:
            continue

        print(f"   Cabecera en fila  : {rep.header_row}")
        print(f"   Columnas activas  : {len(rep.columns_processed)} detectadas")
        print(f"   Filas con cambios : {rep.rows_with_changes}")
        print(f"   Celdas cambiadas  : {rep.total_cells_changed}")

        if rep.samples:
            print("   Muestras de cambios:")
            for col_label, row, before, after in rep.samples[: args.samples]:
                print(f"     - Fila {row:>5}  [{col_label}]  '{before}'  →  '{after}'")

    if not dry_run:
        wb.save(output_file)
        print("\n✅ Archivo guardado:", output_file)
        print("ℹ️  Las hojas restantes (p. ej. con tablas dinámicas) NO se han modificado.")

    # Resumen global
    total_cells = sum(r.total_cells_changed for r in reports)
    total_rows = sum(r.rows_with_changes for r in reports)
    print("\n────────────────────────────────────────────────────────────────")
    print(" RESUMEN GLOBAL")
    print("────────────────────────────────────────────────────────────────")
    print(f" Hojas procesadas        : {len(to_process)}")
    print(f" Filas con cambios       : {total_rows}")
    print(f" Total celdas cambiadas  : {total_cells}")
    print("────────────────────────────────────────────────────────────────")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
