import os
import re
from pathlib import Path

import pandas as pd
from flask import Flask, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = Path(os.getenv("EXCEL_PATH", BASE_DIR / "data" / "excel.xlsx"))
BASE_COLUMNS = ["Producto", "Precio", "Precio texto", "Fuente", "Categoria", "Unidad", "Origen"]
APP_USERNAME = os.getenv("APP_USERNAME", "lapacho")
APP_PASSWORD = os.getenv("APP_PASSWORD", "lapacho123")
SECRET_KEY = os.getenv("SECRET_KEY", "convertidor-lapacho-seguro")

app = Flask(__name__)
app.secret_key = SECRET_KEY


def limpiar_precio(texto: str) -> float | None:
    if texto is None:
        return None

    texto = str(texto).upper().replace("+IVA", "").strip()
    if not texto:
        return None

    numeros = re.sub(r"[^0-9,.\-]", "", texto)
    if not numeros:
        return None

    if "," in numeros and "." in numeros:
        numeros = numeros.replace(".", "").replace(",", ".")
    elif "," in numeros:
        numeros = numeros.replace(".", "").replace(",", ".")
    else:
        partes = numeros.split(".")
        if len(partes) > 2:
            numeros = "".join(partes[:-1]) + "." + partes[-1]

    try:
        return float(numeros)
    except ValueError:
        return None


def formatear_moneda(valor: float) -> str:
    return f"$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def limpiar_texto(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto)).strip(" :-")


def normalizar_texto_columna(texto: str) -> str:
    texto = str(texto).strip().upper()
    reemplazos = str.maketrans(
        {
            "Á": "A",
            "É": "E",
            "Í": "I",
            "Ó": "O",
            "Ú": "U",
            "Ü": "U",
        }
    )
    return texto.translate(reemplazos)


def encontrar_columna(columnas: list[str], candidatos: list[str]) -> str | None:
    columnas_normalizadas = {normalizar_texto_columna(col): col for col in columnas}
    for candidato in candidatos:
        normalizado = normalizar_texto_columna(candidato)
        if normalizado in columnas_normalizadas:
            return columnas_normalizadas[normalizado]
    return None


def fila_base(
    nombre: str,
    precio: float,
    precio_texto: str,
    fuente: str,
    categoria: str = "",
    unidad: str = "",
    origen: str = "Excel",
) -> dict:
    return {
        "Producto": limpiar_texto(nombre),
        "Precio": precio,
        "Precio texto": str(precio_texto).strip(),
        "Fuente": str(fuente).strip(),
        "Categoria": limpiar_texto(categoria),
        "Unidad": str(unidad).strip(),
        "Origen": origen,
    }


def leer_productos_excel(ruta_excel: Path) -> pd.DataFrame:
    if not ruta_excel.exists():
        return pd.DataFrame(columns=BASE_COLUMNS)

    xls = pd.ExcelFile(ruta_excel)
    registros: list[dict] = []

    for hoja in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=hoja)
        if df.empty:
            continue

        producto_col = encontrar_columna(
            list(df.columns),
            [
                "MATERIAL / PRODUCTO",
                "MATERIAL",
                "MATERIAL PLASTICO / POLIMERO",
                "PRODUCTO ELECTRONICO",
                "GRANO",
                "CATEGORIA",
                "CATEGORÍA",
            ],
        )
        precio_col = encontrar_columna(
            list(df.columns),
            [
                "PRECIO PROMEDIO ARS",
                "PRECIO PROMEDIO",
                "PRECIO ESTIMADO ARS",
                "PRECIO TONELADA ARS",
                "PRECIO KG ARS",
            ],
        )
        categoria_col = encontrar_columna(list(df.columns), ["CATEGORIA", "CATEGORÍA", "TIPO", "CLASIFICACIÓN"])
        unidad_col = encontrar_columna(list(df.columns), ["UNIDAD", "CANTIDAD / UNIDAD", "PRESENTACIÓN"])
        fuente_col = encontrar_columna(
            list(df.columns),
            [
                "FUENTE",
                "FUENTE REFERENCIA",
                "FUENTE VERIFICACION",
                "REFERENCIA / ACTUALIZACIÓN",
                "LINK VERIFICACIÓN",
            ],
        )

        if not producto_col or not precio_col:
            continue

        for _, fila in df.iterrows():
            nombre = fila.get(producto_col)
            precio_texto = fila.get(precio_col)

            if pd.isna(nombre) or pd.isna(precio_texto):
                continue

            precio_numero = limpiar_precio(precio_texto)
            if precio_numero is None:
                continue

            categoria = hoja
            if categoria_col and not pd.isna(fila.get(categoria_col)):
                categoria = str(fila.get(categoria_col)).strip()

            unidad = ""
            if unidad_col and not pd.isna(fila.get(unidad_col)):
                unidad = str(fila.get(unidad_col)).strip()

            fuente = f"Excel: {hoja}"
            if fuente_col and not pd.isna(fila.get(fuente_col)):
                fuente = str(fila.get(fuente_col)).strip()

            registros.append(
                fila_base(
                    nombre=nombre,
                    precio=precio_numero,
                    precio_texto=str(precio_texto),
                    fuente=fuente,
                    categoria=categoria,
                    unidad=unidad,
                    origen=f"Excel - {hoja}",
                )
            )

    if not registros:
        return pd.DataFrame(columns=BASE_COLUMNS)

    return pd.DataFrame(registros, columns=BASE_COLUMNS)


def obtener_todo() -> pd.DataFrame:
    df_excel = leer_productos_excel(EXCEL_PATH)
    if df_excel.empty:
        return pd.DataFrame(columns=BASE_COLUMNS)

    df_excel = df_excel.drop_duplicates(subset=["Producto", "Precio", "Fuente", "Categoria", "Unidad"])
    df_excel = df_excel.sort_values(by=["Categoria", "Producto", "Precio"]).reset_index(drop=True)
    return df_excel


def usuario_autenticado() -> bool:
    return session.get("authenticated") is True


@app.route("/login", methods=["GET", "POST"])
def login():
    if usuario_autenticado():
        return redirect(url_for("index"))

    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == APP_USERNAME and password == APP_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("index"))

        error = "Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    if not usuario_autenticado():
        return redirect(url_for("login"))

    df = obtener_todo()
    productos = []

    for idx, fila in df.iterrows():
        categoria = fila.get("Categoria", "")
        producto = fila.get("Producto", "")
        unidad = fila.get("Unidad", "")
        etiqueta = " | ".join(parte for parte in (categoria, producto, unidad) if str(parte).strip())

        productos.append(
            {
                "id": int(idx),
                "etiqueta": etiqueta,
                "categoria": categoria,
                "producto": producto,
                "unidad": unidad,
                "precio": float(fila["Precio"]),
                "precio_formateado": formatear_moneda(float(fila["Precio"])),
                "fuente": fila.get("Fuente", ""),
                "origen": fila.get("Origen", ""),
            }
        )

    return render_template(
        "index.html",
        productos=productos,
        total_productos=len(productos),
        excel_path=str(EXCEL_PATH.relative_to(BASE_DIR)) if EXCEL_PATH.is_relative_to(BASE_DIR) else str(EXCEL_PATH),
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
