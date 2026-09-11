#!/usr/bin/env python3
"""
Generador de requirements.txt por análisis estático de imports

Uso:
  python3 scripts/generate_requirements.py --input /ruta/al/proyecto --map-pypi --include-local --output requirements.txt

Notas:
  - El script intenta resolver automáticamente los módulos usando el entorno actual (importlib.metadata).
  - Si un módulo o subpaquete no está instalado en el entorno, extraerá hasta el segundo nivel (ej: google.genai).
  - Si usamos --map-pypi, se aplicarán heurísticas para mapear módulos comunes a nombres de paquetes PyPI conocidos.
  - Si usamos --include-local, se incluirán módulos locales en la salida, aunque normalmente se omiten.
"""

import argparse
import ast
import os
import sys

COMMON_PYPI_MAP = {
    # --- IA, Visión y Tratamiento de Imágenes ---
    "cv2": "opencv-python",
    "PIL": "Pillow",
    "fitz": "PyMuPDF",
    "skimage": "scikit-image",
    # --- Ciencia de Datos y Machine Learning ---
    "sklearn": "scikit-learn",
    "bs4": "beautifulsoup4",
    "yaml": "PyYAML",
    # --- Criptografía y Seguridad ---
    "Crypto": "pycryptodome",
    "jose": "python-jose",
    "jwt": "PyJWT",
    # --- Utilidades web, Redes y APIs ---
    "websocket": "websocket-client",
    "telegram": "python-telegram-bot",
    "attr": "attrs",
    "serial": "pyserial",
    "usb": "pyusb",
    "dateutil": "python-dateutil",
    "dotenv": "python-dotenv",
    "magic": "python-magic",
    # --- Automatización y GUIs ---
    "wx": "wxPython",
    "setuptools": "setuptools",
}

SKIP_DIRS = {
    "__pycache__",
    ".git",
    ".github",
    "venv",
    ".venv",
    "env",
    "build",
    "dist",
    ".eggs",
}

# Tratar de importar importlib.metadata o su backport
try:
    import importlib.metadata as importlib_metadata
except ImportError:
    try:
        import importlib_metadata
    except ImportError:
        importlib_metadata = None


def find_py_files(root):
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]
        for f in filenames:
            if f.endswith(".py"):
                py_files.append(os.path.join(dirpath, f))
    return py_files


def extract_imports_from_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except (OSError, UnicodeDecodeError):
        return set()
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError:
        return set()
    mods = set()

    def process_name(full_name):
        parts = full_name.split(".")
        # Añadir el módulo raíz (ej: 'google')
        mods.add(parts[0])
        # Si tiene subpaquetes, añadir también el segundo nivel (ej: 'google.genai')
        if len(parts) > 1:
            mods.add(f"{parts[0]}.{parts[1]}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name:
                    process_name(n.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module is None:
                continue
            if node.module:
                process_name(node.module)
    return mods


def build_stdlib_set():
    stdlib = set()
    stdlib_names = getattr(sys, "stdlib_module_names", None)
    if stdlib_names is not None:
        stdlib.update(stdlib_names)
    else:
        stdlib.update(sys.builtin_module_names)
        common = [
            "os",
            "sys",
            "re",
            "subprocess",
            "math",
            "json",
            "collections",
            "itertools",
            "functools",
            "pathlib",
            "typing",
            "datetime",
            "logging",
            "threading",
            "multiprocessing",
            "http",
            "urllib",
            "email",
            "xml",
            "sqlite3",
            "argparse",
            "shutil",
            "tempfile",
            "statistics",
            "inspect",
            "importlib",
            "pkgutil",
        ]
        stdlib.update(common)
    return stdlib


def build_local_names(py_files, root):
    names = set()
    for p in py_files:
        rel = os.path.relpath(p, root)
        base = os.path.splitext(os.path.basename(rel))[0]
        if base:
            names.add(base)
        parts = rel.split(os.sep)
        for part in parts[:-1]:
            if part and part != "__pycache__":
                names.add(part)
    return names


def build_env_package_map():
    if importlib_metadata is None:
        return {}
    try:
        return importlib_metadata.packages_distributions()
    except (AttributeError, ImportError, OSError, ValueError):
        return {}


def map_to_pypi(names, use_env_map=None):
    out = []
    seen = set()
    for n in names:
        if not n or n in seen:
            continue
        pkg = None

        # 1. Prioridad: Consulta de distribuciones instaladas en el entorno
        if use_env_map and n in use_env_map:
            dists = use_env_map.get(n)
            if dists:
                pkg = dists[0]

        # 2. Segunda opción: Mapa estático heurístico
        if pkg is None:
            pkg = COMMON_PYPI_MAP.get(n)

        # 3. Si es un subpaquete sin mapear (ej: google.genai), no usar la raíz si es ambigua
        if pkg is None:
            pkg = n

        if pkg not in seen:
            out.append(pkg)
            seen.add(pkg)
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Generar requirements.txt por análisis estático de imports"
    )
    parser.add_argument(
        "--input", "-i", default=".", help="Carpeta raíz del proyecto a escanear"
    )
    parser.add_argument(
        "--output", "-o", default="requirements.txt", help="Archivo de salida"
    )
    parser.add_argument(
        "--map-pypi",
        "-m",
        action="store_true",
        help="Mapear módulos comunes a nombres de paquetes PyPI (siempre intenta usar entorno)",
    )
    parser.add_argument(
        "--include-local",
        "-l",
        action="store_true",
        help="Incluir módulos locales en la salida",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Mostrar salida detallada"
    )
    args = parser.parse_args()

    root = os.path.abspath(args.input)
    if args.verbose:
        print("Escaneando:", root)

    py_files = find_py_files(root)
    if args.verbose:
        print(f"Archivos .py encontrados: {len(py_files)}")

    all_imports = set()
    for p in py_files:
        mods = extract_imports_from_file(p)
        all_imports.update(mods)

    stdlib = build_stdlib_set()
    local_names = build_local_names(py_files, root)

    candidates = []
    for m in sorted(all_imports):
        if not m or m.startswith("_"):
            continue
        # Descartar si el módulo raíz o el subpaquete pertenece a la librería estándar o local
        root_mod = m.split(".")[0]
        if (root_mod in stdlib) or (root_mod in local_names) or (m in local_names):
            if args.include_local and (m in local_names):
                candidates.append(m)
            continue
        candidates.append(m)

    # Cargar siempre la información del entorno si está disponible
    env_map = build_env_package_map()
    if args.verbose and env_map:
        print(f"Mapa de entorno disponible para {len(env_map)} entradas de paquetes")

    # Mapear los candidatos
    mapped = map_to_pypi(candidates, use_env_map=env_map)

    # Filtrado inteligente: Si conviven 'google' y 'google-genai' (o 'google.genai'),
    # eliminar 'google' para no dejar dependencias genéricas redundantes
    final = []
    has_specific_subpkgs = any("." in item or "-" in item for item in mapped)
    for item in mapped:
        if item == "google" and has_specific_subpkgs:
            continue
        if item not in final:
            final.append(item)

    out_path = os.path.abspath(args.output)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.writelines(pkg + "\n" for pkg in final)

    print(f"Escrito {len(final)} entradas en {out_path}")


if __name__ == "__main__":
    main()
