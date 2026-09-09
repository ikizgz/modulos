import pandas as pd
import pdfplumber

with pdfplumber.open("Escalafon.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        # Configuraciones personalizadas para tablas complejas
        table_settings = {
            "vertical_strategy": "lines",  # "lines" o "text" si no hay líneas dibujadas
            "horizontal_strategy": "lines",
            "intersection_tolerance": 5,
        }

        tables = page.extract_tables(table_settings)
        if tables:
            print(f"Página {i + 1}: Se encontraron {len(tables)} tablas.")
            # Puedes volcar la primera tabla a DataFrame para probar
            df = pd.DataFrame(tables[0][1:], columns=tables[0][0])
            print(df.head())
