import os
import subprocess
from pathlib import Path

SOURCE_ROOT = Path(r"C:\Ruta\Origen")  # o "/ruta/origen"
TARGET_ROOT = Path(r"C:\Ruta\Destino")  # o "/ruta/destino"

# Si necesitas una ruta específica de soffice en Windows, ponla aquí; si no, deja "soffice"
SOFFICE = (
    r"C:\Program Files\LibreOffice\program\soffice.exe"
    if os.name == "nt"
    else "soffice"
)

EXTS = {".doc", ".dot", ".rtf"}  # añade o quita si te interesa

errors = []

for root, _, files in os.walk(SOURCE_ROOT):
    for fname in files:
        src = Path(root) / fname
        ext = src.suffix.lower()
        if ext not in EXTS:
            continue
        if ext == ".doc" and src.name.lower().endswith(".docx"):
            # Evita falsos positivos .docx
            continue

        rel = src.relative_to(SOURCE_ROOT)
        outdir = TARGET_ROOT / rel.parent
        outdir.mkdir(parents=True, exist_ok=True)

        out = outdir / (src.stem + ".docx")
        if out.exists():
            print(f"Ya existe: {out}")
            continue

        cmd = [
            SOFFICE,
            "--headless",
            "--convert-to",
            "docx:Office Open XML Text",
            "--outdir",
            str(outdir),
            str(src),
        ]
        print("Convirtiendo:", src)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0 or not out.exists():
                print("FALLO:", src, res.stdout, res.stderr)
                errors.append((str(src), res.stdout, res.stderr))
            else:
                print("OK   →", out)
        except Exception as e:
            print("EXC  →", src, e)
            errors.append((str(src), str(e), ""))

print("\nResumen:")
print("Errores:", len(errors))
if errors:
    for e in errors[:20]:
        print(" -", e[0])
