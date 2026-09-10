# Módulos

Este repositorio contiene mis archivos con código reutilizable

## convertir_docs.py

Script para convertir fácil y rápidamente los antiguos archivos de texto .doc,
.dot y .rtf (u otras extensiones de procesadores de texto como .wps,.wpd) al
formato de Word moderno .docx o a .pdf

## escribir_encabezados_scripts.py

Script que itera sobre todos los archivos de una extensión específica en un
directorio y les añade un encabezado de licencia y metadatos con el formato
estándar. Permite elegir entre un modo 'Genérico' (relleno automático con
valores por defecto) y un modo 'Interactivo' (pedir detalles por cada script).

## extraer_tabla_excel.py

Script para extraer las tablas de un archivo pdf y exportarlas a un archivo
Excel.

## funciones_utiles_python_libroffice.py

Guía de Python: funciones útiles para LibreOffice - The Document Foundation Wiki
Este módulo contiene una colección de funciones útiles para trabajar con
LibreOffice utilizando Python. Estas funciones están diseñadas para facilitar la
automatización y manipulación de documentos en LibreOffice, permitiendo a los
usuarios realizar tareas comunes de manera más eficiente.

## generate_requirements.py

Script para escanear los scripts \*.py de un proyecto y generar un archivo
requirements.txt. El archivo incluirá opciones CLI para especificar la carpeta a
escanear, la ruta de salida y una opción para mapear nombres de módulos a
paquetes PyPI comunes.

## instalar_paquetes_faltantes.py

Script que verifica si los paquetes necesarios para ejecutar un proyecto de
Python están instalados en el entorno actual. Si encuentra paquetes faltantes,
los instala automáticamente utilizando pip. Este script es útil para garantizar
que todas las dependencias estén satisfechas antes de ejecutar un proyecto,
evitando errores relacionados con módulos no encontrados.

## limpiar_textos_excel.py

Limpia en un Excel las columnas 'First Name' y 'Last Name' en las N primeras
hojas (por defecto 4) **sin recrear hojas** (edición IN-PLACE con openpyxl),
para **preservar** objetos de Excel como tablas dinámicas en otras hojas (p.
ej., tu hoja 5). Convierte a MAYÚSCULAS, elimina acentos y caracteres no
imprimibles, **respetando la Ñ** (que queda como Ñ mayúscula).

## logging_utils.py

Módulo para implementar facilmente logs en los scripts.

## marcadores_pdf.py

Script para localizar los titulos susceptibles de ser marcadores de un pdf y
crearlos.

## modulo_factorial.py

Módulo que contiene una función para calcular el factorial de un número entero.

## ocr_pdf.py

Este script procesa documentos PDF escaneados con baja calidad de tinta, fondos
sucios o descoloridos (como escalafones antiguos). Aplica técnicas de
preprocesamiento de imagen con OpenCV (umbral adaptativo y reducción de ruido)
para maximizar el contraste, ejecuta OCR con Tesseract, y genera un nuevo PDF
searchable que conserva la imagen original pero con una capa de texto
transparente seleccionable y buscable.

## python_plantilla_encabezado.py

Plantilla de inicio para archivos Python, con un encabezado de licencia y
metadatos.
