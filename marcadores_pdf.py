import csv
import logging
import os
import re
from typing import Dict, List, cast

import fitz  # PyMuPDF

# --- Configuración del Log ---
# Esto escribirá en un archivo y mostrará en consola simultáneamente
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("procesamiento.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def limpiar_linea_titulo(linea: str) -> str:
    """Limpia ruidos de numeración inicial, códigos y espacios."""
    limpia = linea.strip()
    # Eliminar líneas que son puramente códigos ID o referencias
    if re.search(r"\bREF[\s:]", limpia, re.IGNORECASE) or re.search(
        r"\bID\.\d", limpia, re.IGNORECASE
    ):
        return ""
    # Quitar numeraciones del tipo "1. ", "12. ", "• " al inicio
    limpia = re.sub(r"^[•\d\.\s\-\)]+", "", limpia)
    return limpia.strip()


def descubrir_titulos_visuales(texto_visual_ordenado: str) -> List[str]:
    """
    Escanea el texto visual ordenado. Encuentra TODOS los emisores de una página,
    busca hacia arriba y une líneas contiguas. Se detiene ante saltos de párrafo.
    """
    lineas = [linea.strip() for linea in texto_visual_ordenado.split("\n")]
    titulos_encontrados = []

    # Textos corporativos fijos de cabecera que hay que ignorar
    filtros_basura = [
        "NORMATIVA IBERCAJA",
        "USO INTERNO",
        "INFORMACIÓN DIARIA",
        "CONSULTAS:",
        "DIFUSIÓN:",
        "DIFUSION:",
        "FECHA",
        "PÁGINA",
        "REF:",
        "HTTP",
        "TELÉFONO",
        "IBERCAJA S.A.",
        "PÁG.",
        "VOLVER",
        "INDICE",
    ]

    # 1. Encontrar TODOS los índices donde empiece un artículo
    indices_emisores = []
    for idx, linea in enumerate(lineas):
        linea_up = linea.upper()
        # Flexibilizado para casos (2011-2013) donde el OCR omite los dos puntos o recorta la palabra
        if (
            re.match(r"^(?:EMISOR|EMITE|EMISO)\b", linea_up)
            or "EMISOR:" in linea_up
            or "EMITE:" in linea_up
        ):
            indices_emisores.append(idx)

    # 2. Por cada artículo en la página, buscar su título hacia arriba
    for indice_emisor in indices_emisores:
        fragmentos_titulo = []

        for i in range(indice_emisor - 1, -1, -1):
            linea_actual = lineas[i].strip()

            # CONTROL DE SALTO FÍSICO: Si la línea está vacía, es que hay un hueco/separador real.
            if not linea_actual:
                if fragmentos_titulo:
                    break  # Si ya teníamos texto del título y chocamos con un hueco, el título ha terminado.
                continue

            linea_upper = linea_actual.upper()

            # Filtro A: Saltamos cabeceras globales o palabras de control
            if any(f in linea_upper for f in filtros_basura) or re.match(
                r"^(?:EMISOR|EMITE|EMISO)\b", linea_upper
            ):
                if fragmentos_titulo:
                    break
                continue

            # Filtro B: Saltamos si la línea es EXCLUSIVAMENTE la fecha del boletín
            # (Corregido para que no borre títulos reales que contengan un año como "DE 2011")
            if re.search(r"\b\d{1,2}\s+DE\s+[A-Z]+\s+DE\s+20\d\d\b", linea_upper):
                if fragmentos_titulo:
                    break
                continue

            # CONDICIÓN SOBERANA VISUAL: Tiene que ser MAYÚSCULAS y tener letras.
            if (
                linea_actual.isupper()
                and any(c.isalpha() for c in linea_actual)
                and len(linea_actual) >= 3
            ):
                linea_limpia = limpiar_linea_titulo(linea_actual)
                if linea_limpia:
                    # Insertamos al principio porque estamos leyendo de abajo hacia arriba
                    fragmentos_titulo.insert(0, linea_limpia)
            else:
                # Si nos topamos con una línea en minúsculas (ej: descripción de sección "Comercial")
                if fragmentos_titulo:
                    break

        if fragmentos_titulo:
            titulo_completo = " ".join(fragmentos_titulo).strip()
            if titulo_completo not in titulos_encontrados:
                titulos_encontrados.append(titulo_completo)

    return titulos_encontrados


def obtener_texto_visual(
    pagina: fitz.Page, numero_pagina: int, nombre_fichero: str
) -> str:
    """
    Extrae los bloques de texto y los ordena por su coordenada Y (Altura visual).
    Inyecta líneas vacías ("") si detecta grandes saltos verticales para aislar párrafos.
    """
    texto_raw = cast(str, pagina.get_text("text"))

    if len(texto_raw.strip()) < 60:
        logging.info(
            f"   [OCR] Ejecutando Tesseract en pág. {numero_pagina + 1} de '{nombre_fichero}'..."
        )
        try:
            tp = pagina.get_textpage_ocr(flags=fitz.TEXTFLAGS_SEARCH, language="spa")
            bloques = tp.extractBLOCKS()
        except Exception as e:
            logging.info(
                f"   [ERROR OCR] Falló Tesseract en pág. {numero_pagina + 1}: {e}"
            )
            bloques = pagina.get_text("blocks")
    else:
        bloques = pagina.get_text("blocks")

    bloques_texto = [b for b in bloques if b[6] == 0]

    # ORDENACIÓN: Agrupamos alturas en franjas de 5px para alinear columnas, luego por X
    # Convertimos b[1] explícitamente a float o int
    bloques_texto.sort(key=lambda b: (round(float(b[1]) / 5) * 5, b[0]))

    lineas_visuales = []
    y_bottom_previo = -1

    for b in bloques_texto:
        y0 = b[1]
        y1 = b[3]

        # INYECCIÓN DE GAP: Si el bloque actual está a más de 8 píxeles por debajo del final del último bloque visto
        # Aseguramos que tanto y0 como y_bottom_previo sean tratados como números
        if y_bottom_previo != -1 and float(y0) > float(y_bottom_previo) + 8:
            lineas_visuales.append("")  # Separador físico de párrafo

        texto_bloque = b[4].strip()
        if texto_bloque:
            for linea in texto_bloque.split("\n"):
                linea_str = linea.strip()
                if linea_str:
                    lineas_visuales.append(linea_str)

        y_bottom_previo = y1 if y_bottom_previo == -1 else max(y_bottom_previo, y1)

    return "\n".join(lineas_visuales)


def extraer_toc_existente(ruta_archivo: str) -> List[Dict]:
    """Lee el TOC de un PDF y lo devuelve en formato lista de diccionarios."""
    nombre_fichero = os.path.basename(ruta_archivo)
    registros = []

    try:
        doc = fitz.open(ruta_archivo)
        toc = doc.get_toc()

        for item in toc:
            # item es: [nivel, título, página_destino]
            # Solo guardamos los de nivel 1 para mantener la coherencia
            if item[0] == 1:
                registros.append(
                    {"archivo": nombre_fichero, "pagina": item[2], "titulo": item[1]}
                )
        doc.close()
    except Exception as e:
        logging.error(f"Error leyendo TOC de {nombre_fichero}: {e}")

    return registros


def procesar_archivo_ibercaja(ruta_archivo: str, carpeta_destino: str) -> List[Dict]:
    """
    Procesa cada archivo que se lee, detecta los títulos de los artículos, genera marcadores y guarda el PDF marcado.
    Devuelve una lista de diccionarios con los registros de títulos encontrados para crear índices posteriormente
    """
    nombre_fichero = os.path.basename(ruta_archivo)
    # 1. Abrimos el documento para inspeccionarlo
    documento_pdf = fitz.open(ruta_archivo)

    # 2. Comprobación maestra: ¿Ya tiene marcadores (TOC)?
    if documento_pdf.get_toc():
        logging.info(f"Saltando: {nombre_fichero} (ya tiene marcadores).")
        documento_pdf.close()
        return []

    logging.info(f"Procesando: {nombre_fichero}")

    registros_archivo: List[Dict] = []
    lista_marcadores_final: List[List] = []

    try:
        documento_pdf = fitz.open(ruta_archivo)

        if len(documento_pdf) < 1:
            documento_pdf.close()
            return registros_archivo

        for num_pag in range(len(documento_pdf)):
            texto_visual = obtener_texto_visual(
                documento_pdf[num_pag], num_pag, nombre_fichero
            )
            texto_upper = texto_visual.upper()

            tiene_bloque_consultas = (
                "CONSULTAS" in texto_upper
                or "DIFUSIÓN" in texto_upper
                or "DIFUSION" in texto_upper
            )

            if tiene_bloque_consultas:
                titulos_pagina = descubrir_titulos_visuales(texto_visual)
                for titulo in titulos_pagina:
                    lista_marcadores_final.append([1, titulo, num_pag + 1])
                    registros_archivo.append(
                        {
                            "archivo": nombre_fichero,
                            "pagina": num_pag + 1,
                            "titulo": titulo,
                        }
                    )

        if lista_marcadores_final:
            lista_marcadores_final.sort(key=lambda x: x[2])
            documento_pdf.set_toc(lista_marcadores_final)

            nombre_base = (
                os.path.splitext(nombre_fichero)[0]
                .replace("_MARCADO", "")
                .replace("_marcado", "")
            )
            ruta_final = os.path.join(carpeta_destino, f"{nombre_base}_MARCADO.pdf")

            documento_pdf.save(ruta_final)
            logging.info(
                f"  -> ÉXITO: {len(lista_marcadores_final)} marcadores guardados."
            )
        else:
            logging.warning(f"  -> AVISO: No se detectaron bloques en {nombre_fichero}")

        documento_pdf.close()
    except Exception as e:
        logging.error(f"  -> CRÍTICO: No se pudo procesar {nombre_fichero}: {e}")

    return registros_archivo


def recorrer_y_procesar(directorio_raiz: str):
    """Recorre recursivamente el directorio raíz, procesa cada PDF encontrado y genera índices locales."""
    # Lista global que acumulará los registros de todos los archivos
    historico_global = []

    for root, dirs, files in os.walk(directorio_raiz):
        # Evitamos entrar en carpetas de salida ya creadas
        if "Marcados" in root:
            continue

        pdf_files = [f for f in files if f.lower().endswith(".pdf")]

        if not pdf_files:
            continue

        logging.info(f"\n--- Procesando carpeta: {root} ---")
        carpeta_salida = os.path.join(root, "Marcados")
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)

    for archivo in pdf_files:
        ruta_completa = os.path.join(root, archivo)

        # PROTECCIÓN: Cada archivo es una unidad independiente
        try:
            # 1. Verificar TOC (si ya está marcado, extraemos info)
            doc_tmp = fitz.open(ruta_completa)
            tiene_marcadores = len(doc_tmp.get_toc()) > 0
            doc_tmp.close()

            if tiene_marcadores:
                logging.info(f"Saltando y extrayendo TOC: {archivo}")
                datos = extraer_toc_existente(ruta_completa)
                historico_global.extend(datos)
            else:
                # 2. Si no tiene, procesamos desde cero
                datos = procesar_archivo_ibercaja(ruta_completa, carpeta_salida)
                historico_global.extend(datos)

        except Exception as e:
            # Si un archivo falla, lo anotamos pero el bucle NO se detiene
            logging.error(
                f"FALLO CRÍTICO en el archivo {archivo}: {e}. Continuando con el siguiente..."
            )
            continue  # Esta línea es la clave: salta al siguiente archivo sin detener el proceso global

    # Una vez terminados todos los directorios, generamos el CSV único en la raíz
    if historico_global:
        ruta_indice_unico = os.path.join(directorio_raiz, "Indice_Global_Normativa.csv")

        # Comprobamos si el archivo ya existe para saber si debemos escribir cabecera
        archivo_existe = os.path.isfile(ruta_indice_unico)

        # Abrimos en modo 'a' (append) para añadir al final
        with open(ruta_indice_unico, mode="a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["archivo", "pagina", "titulo"], delimiter=";"
            )

            # Solo escribimos la cabecera si el archivo es nuevo
            if not archivo_existe:
                writer.writeheader()

            writer.writerows(historico_global)

        logging.info(f"\n>> ÍNDICE GLOBAL ACTUALIZADO: {ruta_indice_unico}")
    else:
        logging.warning(
            "\nNo se encontraron datos nuevos para añadir al índice global."
        )


if __name__ == "__main__":
    # Cambia esto por tu directorio de archivos original
    directorio_base = "./"

    if os.path.exists(directorio_base):
        recorrer_y_procesar(directorio_base)
        logging.info("\n¡PROCESO FINALIZADO CON ÉXITO!")
    else:
        logging.error(f"El directorio {directorio_base} no existe.")
