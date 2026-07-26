#!/usr/bin/env python3
"""
Generador de requirements.txt por análisis estático de imports

Uso:
  python3 scripts/generate_requirements.py --root /ruta/al/proyecto --output requirements.txt

Opciones principales:
  --root      Carpeta raíz a escanear (por defecto: .)
  --output    Ruta del archivo de salida (por defecto: requirements.txt)
  --map-pypi  Intentar mapear nombres de módulos comunes a nombres de paquetes PyPI
  --use-env-mapping  Intentar resolver módulos usando importlib.metadata (distribuciones instaladas en el entorno)
  --include-local  Incluir módulos locales del propio repositorio en la salida
  --verbose   Salida más detallada

Notas:
  - El script usa ast para detectar imports estáticos; imports dinámicos o generados en tiempo de ejecución no siempre se detectan.
  - Revisa manualmente el resultado: algunos módulos necesitan que pongas el nombre PyPI adecuado o añadas versiones.
"""

import ast
import os
import sys
import argparse

# Mapeos heurísticos comunes de top-level module -> PyPI package name
COMMON_PYPI_MAP = {
    'bs4': 'beautifulsoup4',
    'PIL': 'Pillow',
    'cv2': 'opencv-python',
    'fitz': 'PyMuPDF',  # el módulo se importa como fitz pero el paquete PyPI es PyMuPDF
    'yaml': 'PyYAML',
    'sklearn': 'scikit-learn',
    'Crypto': 'pycryptodome',
    'setuptools': 'setuptools',
    'uno': 'uno',  # LibreOffice UNO no siempre está en PyPI; mapear manualmente si hace falta
}

SKIP_DIRS = {'__pycache__', '.git', '.github', 'venv', '.venv', 'env', 'build', 'dist', '.eggs'}

# Tratar de importar importlib.metadata o su backport
try:
    import importlib.metadata as importlib_metadata
except Exception:
    try:
        import importlib_metadata
    except Exception:
        importlib_metadata = None


def is_hidden(path, root):
    rel = os.path.relpath(path, root)
    parts = rel.split(os.sep)
    return any(p.startswith('.') for p in parts if p)


def find_py_files(root):
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for f in filenames:
            if f.endswith('.py'):
                py_files.append(os.path.join(dirpath, f))
    return py_files


def extract_imports_from_file(path):
    try:
        src = open(path, 'r', encoding='utf-8').read()
    except Exception:
        return set()
    try:
        tree = ast.parse(src, filename=path)
    except SyntaxError:
        return set()
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name:
                    mods.add(n.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            # saltar imports relativos
            if node.level and node.module is None:
                continue
            if node.module:
                mods.add(node.module.split('.')[0])
    return mods


def build_stdlib_set():
    stdlib = set()
    stdlib_names = getattr(sys, 'stdlib_module_names', None)
    if stdlib_names is not None:
        stdlib.update(stdlib_names)
    else:
        stdlib.update(sys.builtin_module_names)
        common = ['os','sys','re','subprocess','math','json','collections','itertools','functools','pathlib','typing','datetime','logging','threading','multiprocessing','http','urllib','email','xml','sqlite3','argparse','shutil','tempfile','statistics','inspect','importlib','pkgutil']
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
            if part and part != '__pycache__':
                names.add(part)
    return names


def build_env_package_map():
    """Devuelve un dict top_level_module -> list(distribution_names) si importlib.metadata está disponible."""
    if importlib_metadata is None:
        return {}
    try:
        pack_map = importlib_metadata.packages_distributions()
        return pack_map
    except Exception:
        return {}


def map_to_pypi(names, use_env_map=None):
    """Mapea una lista de top-level modules a nombres de paquete PyPI.

    Preferencias de mapeo:
      1. Si use_env_map proporciona una distribución instalada para el top-level module, usar la primera distribución.
      2. Si COMMON_PYPI_MAP tiene un mapeo heurístico, usarlo.
      3. Si no, usar el nombre del módulo tal cual.
    """
    out = []
    seen = set()
    for n in names:
        if not n or n in seen:
            continue
        pkg = None
        if use_env_map and n in use_env_map:
            dists = use_env_map.get(n)
            if dists:
                pkg = dists[0]
        if pkg is None:
            pkg = COMMON_PYPI_MAP.get(n)
        if pkg is None:
            pkg = n
        if pkg not in seen:
            out.append(pkg)
            seen.add(pkg)
    return out


def main():
    parser = argparse.ArgumentParser(description='Generar requirements.txt por análisis estático de imports')
    parser.add_argument('--root', default='.', help='Carpeta raíz del proyecto a escanear')
    parser.add_argument('--output', default='requirements.txt', help='Archivo de salida')
    parser.add_argument('--map-pypi', action='store_true', help='Mapear módulos comunes a nombres de paquetes PyPI')
    parser.add_argument('--use-env-mapping', action='store_true', help='Usar importlib.metadata del entorno para mapear módulos a distribuciones')
    parser.add_argument('--include-local', action='store_true', help='Incluir módulos locales en la salida')
    parser.add_argument('--verbose', action='store_true', help='Mostrar salida detallada')
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    if args.verbose:
        print('Escaneando:', root)

    py_files = find_py_files(root)
    if args.verbose:
        print(f'Archivos .py encontrados: {len(py_files)}')

    all_imports = set()
    for p in py_files:
        mods = extract_imports_from_file(p)
        all_imports.update(mods)

    stdlib = build_stdlib_set()
    local_names = build_local_names(py_files, root)

    candidates = []
    for m in sorted(all_imports):
        if not m or m.startswith('_'):
            continue
        if (m in stdlib) or (m in local_names):
            if args.include_local and (m in local_names):
                candidates.append(m)
            continue
        candidates.append(m)

    env_map = None
    if args.use_env_mapping:
        env_map = build_env_package_map()
        if args.verbose:
            if importlib_metadata is None:
                print('importlib.metadata / importlib_metadata no disponible en este entorno; --use-env-mapping ignorado')
            else:
                print(f'Env mapping available for {len(env_map)} top-level packages')

    if args.map_pypi or args.use_env_mapping:
        final = map_to_pypi(candidates, use_env_map=env_map)
    else:
        # mantener orden único
        final = []
        for c in candidates:
            if c not in final:
                final.append(c)

    out_path = os.path.abspath(args.output)
    with open(out_path, 'w', encoding='utf-8') as fh:
        for pkg in final:
            fh.write(pkg + '\n')

    print(f'Escrito {len(final)} entradas en {out_path}')
    if args.verbose:
        print('\nMódulos detectados (únicos):')
        for m in sorted(all_imports):
            print('  ', m)
        print('\nLocal names (excluidos):')
        for l in sorted(local_names):
            print('  ', l)


if __name__ == '__main__':
    main()
