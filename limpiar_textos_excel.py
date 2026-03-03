#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Limpia en un Excel las columnas TARGET_HEADERS de las constantes en las N primeras hojas (por defecto 2)
**sin recrear hojas** (edición IN-PLACE con openpyxl), para **preservar** objetos de Excel como
tablas dinámicas en otras hojas. Convierte a MAYÚSCULAS, elimina acentos y
caracteres no imprimibles, **respetando la Ñ** (que queda como Ñ mayúscula).

USO RÁPIDO
----------
    python limpia_nombres_excel.py --input excel.xlsx \
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

--sheets N         Nº de hojas iniciales a procesar (por orden del libro). Por defecto: 2.

--header-scan-rows N
                   Nº de filas superiores donde buscar la fila de cabecera. Por defecto: 5.

--samples N        Nº de ejemplos (antes → después) a mostrar por hoja. Por defecto: 5.

--no-collapse-spaces
                   Desactiva la normalización de espacios (por defecto se colapsan múltiples
                   espacios y NBSP a un único espacio y se recortan extremos).

EJEMPLOS
--------
1) Preguntar por dry-run y generar salida por defecto:
   python limpia_nombres_excel.py -i excel.xlsx

2) Forzar simulación (no guarda):
   python limpia_nombres_excel.py -i excel.xlsx -o out.xlsx --dry-run on

3) Guardar sin preguntar (crea backup y escribe out.xlsx):
   python limpia_nombres_excel.py -i excel.xlsx -o out.xlsx --dry-run off

NOTAS
-----
- Solo se modifican celdas de 'First Name' y 'Last Name' en las N primeras hojas; **no se recrean hojas**.
- La hoja 5 (con Pivot) se mantiene intacta; al abrir Excel puedes refrescar la Pivot si procede.
- Se ignoran celdas combinadas no-maestras (MergedCell), ya que no admiten escritura.

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

from __future__ import annotations

import argparse
import os
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.worksheet.worksheet import Worksheet

# ------------------- CONSTANTES POR DEFECTO -------------------
DEFAULT_INPUT_FILE = "excel.xlsx"  # Cambia a lo que corresponda
DEFAULT_OUTPUT_FILE = "excel_LIMPIO.xlsx"  # Cambia a lo que corresponda
NUM_SHEETS_TO_PROCESS = 2  # Número de hojas iniciales a procesar (por orden del libro)
TARGET_HEADERS: Tuple[str, str] = ("Col1", "Col2")  # Cambia a lo que corresponda
HEADER_SCAN_ROWS = 5  # Número de filas superiores a escanear para encontrar la cabecera
COLLAPSE_SPACES = True  # Si True, colapsa múltiples espacios y NBSP a un único espacio y recorta extremos
SHOW_SAMPLES_PER_SHEET = (
    5  # Número de ejemplos (antes → después) a mostrar por hoja en el informe
)
# --------------------------------------------------------------


# ------------------- ESTRUCTURAS DE INFORME -------------------
@dataclass
class SheetReport:
    sheet_name: str
    header_row: Optional[int] = None
    col_first: Optional[int] = None  # 1-based
    col_last: Optional[int] = None  # 1-based
    rows_with_changes: int = 0
    cells_changed_first: int = 0
    cells_changed_last: int = 0
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
def find_header_row(
    ws: Worksheet, target_headers: Sequence[str], scan_rows: int
) -> Optional[int]:
    """Devuelve la fila (1-based) que contiene alguna de las cabeceras objetivo."""
    wanted_lower = {h.lower() for h in target_headers}
    max_scan = min(ws.max_row, scan_rows)
    for r in range(1, max_scan + 1):
        row_lower = [
            (str(cell.value).strip().lower() if cell.value is not None else "")
            for cell in ws[r]
        ]
        if any(h in row_lower for h in wanted_lower):
            return r
    return None


def get_column_indices(
    ws: Worksheet, header_row: int
) -> Tuple[Optional[int], Optional[int]]:
    col_first: Optional[int] = None
    col_last: Optional[int] = None
    for cell in ws[header_row]:
        raw = cell.value
        val = str(raw).strip().lower() if raw is not None else ""
        if val == "first name" and col_first is None:
            col = cell.column
            if isinstance(col, int):
                col_first = col
        elif val == "last name" and col_last is None:
            col = cell.column
            if isinstance(col, int):
                col_last = col
        if col_first is not None and col_last is not None:
            break
    return col_first, col_last


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
) -> SheetReport:
    """Procesa una hoja limpiando columnas objetivo. Devuelve el informe."""
    report = SheetReport(sheet_name=ws.title)

    header_row = find_header_row(ws, TARGET_HEADERS, HEADER_SCAN_ROWS)
    if header_row is None:
        print(
            f"  ⚠️  [{sheet_index}] '{ws.title}': no se encontró fila de cabecera (1..{HEADER_SCAN_ROWS}). Omitida."
        )
        return report

    col_first, col_last = get_column_indices(ws, header_row)
    report.header_row = header_row
    report.col_first = col_first
    report.col_last = col_last

    if col_first is None and col_last is None:
        print(
            f"  ⚠️  [{sheet_index}] '{ws.title}': no existen columnas {TARGET_HEADERS}. Omitida."
        )
        return report

    max_row = ws.max_row
    for r in range(header_row + 1, max_row + 1):
        row_changed = False

        if col_first is not None:
            cell_f = ws.cell(row=r, column=col_first)
            # Evitar celdas combinadas no-maestras
            if not isinstance(cell_f, MergedCell):
                before_f = cell_f.value
                if before_f is not None and str(before_f).strip() != "":
                    after_f = limpiar_texto(before_f)
                    if after_f != before_f:
                        if not dry_run:
                            cell_f.value = after_f
                        report.cells_changed_first += 1
                        row_changed = True
                        if len(report.samples) < show_samples:
                            report.samples.append(
                                ("First Name", r, str(before_f), str(after_f))
                            )

        if col_last is not None:
            cell_l = ws.cell(row=r, column=col_last)
            if not isinstance(cell_l, MergedCell):
                before_l = cell_l.value
                if before_l is not None and str(before_l).strip() != "":
                    after_l = limpiar_texto(before_l)
                    if after_l != before_l:
                        if not dry_run:
                            cell_l.value = after_l
                        report.cells_changed_last += 1
                        row_changed = True
                        if len(report.samples) < show_samples:
                            report.samples.append(
                                ("Last Name", r, str(before_l), str(after_l))
                            )

        if row_changed:
            report.rows_with_changes += 1

    return report


# --------------------------------------------------------------


# ------------------------- CLI / MAIN -------------------------
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Limpia 'First Name' y 'Last Name' en las N primeras hojas de un Excel (in-place), preservando pivots."
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

    # Config global dependiente de flags
    global COLLAPSE_SPACES, HEADER_SCAN_ROWS
    COLLAPSE_SPACES = not args.no_collapse_spaces
    HEADER_SCAN_ROWS = args.header_scan_rows

    input_file: str = args.input
    output_file: str = args.output
    sheets_to_process: int = max(0, args.sheets)

    # Determinar dry-run según CLI o prompt
    if args.dry_run == "on":
        dry_run = True
    elif args.dry_run == "off":
        dry_run = False
    else:
        dry_run = ask_dry_run()

    print("────────────────────────────────────────────────────────────────")
    print(" Limpieza de nombres en Excel (in‑place, preserva pivots)")
    print("────────────────────────────────────────────────────────────────")
    print(f"Archivo de entrada : {input_file}")
    print(f"Archivo de salida  : {output_file}")
    print(f"Dry-run (simulación): {dry_run}")
    print(f"Colapsar espacios  : {COLLAPSE_SPACES}")
    print(f"Hojas a procesar   : {sheets_to_process} primeras")
    print("────────────────────────────────────────────────────────────────")

    if not os.path.exists(input_file):
        print(f"❌ No se encuentra el archivo de entrada: {input_file}")
        return 1

    # Backup si no es dry-run
    if not dry_run:
        backup_path = backup_file(input_file)
        print(f"🛡  Backup creado   : {backup_path}")

    # Cargar libro
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
        rep = process_sheet(ws, idx, dry_run=dry_run, show_samples=args.samples)
        reports.append(rep)

        if rep.header_row is None:
            continue

        print(f"   Cabecera en fila : {rep.header_row}")
        print(f"   Col 'First Name' : {rep.col_first}")
        print(f"   Col 'Last Name'  : {rep.col_last}")
        print(f"   Filas con cambios: {rep.rows_with_changes}")
        print(
            f"   Celdas cambiadas : First={rep.cells_changed_first}, Last={rep.cells_changed_last}"
        )

        if rep.samples:
            print("   Muestras de cambios:")
            for col_label, row, before, after in rep.samples[: args.samples]:
                print(f"     - Fila {row:>5}  [{col_label}]  '{before}'  →  '{after}'")

    if not dry_run:
        wb.save(output_file)
        print("\n✅ Archivo guardado:", output_file)
        print("ℹ️  La hoja 5 (p. ej. con tabla dinámica) NO se ha modificado.")

    # Resumen global
    total_first = sum(r.cells_changed_first for r in reports)
    total_last = sum(r.cells_changed_last for r in reports)
    total_rows = sum(r.rows_with_changes for r in reports)
    print("\n────────────────────────────────────────────────────────────────")
    print(" RESUMEN GLOBAL")
    print("────────────────────────────────────────────────────────────────")
    print(f" Hojas procesadas       : {len(to_process)}")
    print(f" Filas con cambios      : {total_rows}")
    print(f" Celdas cambiadas First : {total_first}")
    print(f" Celdas cambiadas Last  : {total_last}")
    print("────────────────────────────────────────────────────────────────")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
