import os
import subprocess
import sys


# --- Función para leer los paquetes de requirements.txt ---
def read_requirements(filename="requirements.txt"):
    """Lee y devuelve una lista de paquetes del archivo requirements.txt."""
    if not os.path.exists(filename):
        print(
            f"❌ Error: El archivo '{filename}' no se encontró en el directorio actual."
        )
        return []

    print(f"📖 Leyendo paquetes de '{filename}'...")
    try:
        with open(filename, "r") as f:
            # Filtra líneas vacías y comentarios, y elimina espacios en blanco/saltos de línea
            packages = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        return packages
    except Exception as e:
        print(f"❌ Error al leer el archivo '{filename}': {e}")
        return []


# --- Función para verificar e instalar los paquetes que falten ---
def install_missing_packages(packages):
    """Verifica si cada paquete en la lista está instalado y lo instala si falta."""
    if not packages:
        print("ℹ️ No hay paquetes para verificar/instalar.")
        return

    print("\n--- Verificación e Instalación de Paquetes ---")
    for package_line in packages:
        # Intenta obtener solo el nombre del paquete si hay información de versión (ej: 'numpy==1.26.1')
        package_name = (
            package_line.split("==")[0]
            .split(">")[0]
            .split("<")[0]
            .split("~")[0]
            .split("!")[0]
        )

        try:
            # Intenta importar el paquete por su nombre simple
            __import__(package_name)
            print(f"✅ {package_name} (de '{package_line}') ya está instalado.")
        except ImportError:
            # Si falla la importación, procede a instalar la línea completa del requirement
            print(f"📦 Instalando {package_line}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package_line]
                )
                print(f"✨ Éxito: {package_line} instalado.")
            except subprocess.CalledProcessError as e:
                print(f"❌ Error al instalar {package_line}: {e}")
            except Exception as e:
                print(f"❌ Ocurrió un error inesperado al instalar {package_line}: {e}")


# --- Ejecución principal ---
if __name__ == "__main__":
    # read_requirements() usa parámetro por defecto: requirementes.txt
    # Puedes usar otro archivo, ejem: read_requirements("paquetes.txt")
    required_packages = read_requirements()
    install_missing_packages(required_packages)
