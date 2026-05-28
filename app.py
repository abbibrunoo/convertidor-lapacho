import os
import re
import unicodedata
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = Path(os.getenv("EXCEL_PATH", BASE_DIR / "data" / "excel.xlsx"))
BASE_COLUMNS = ["Producto", "Precio", "Precio texto", "Fuente", "Categoria", "Unidad", "Origen"]
APP_USERNAME = os.getenv("APP_USERNAME", "lapacho")
APP_PASSWORD = os.getenv("APP_PASSWORD", "lapacho123")
SECRET_KEY = os.getenv("SECRET_KEY", "convertidor-lapacho-seguro")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True


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
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(caracter for caracter in texto if not unicodedata.combining(caracter))


def encontrar_columna(columnas: list[str], candidatos: list[str]) -> str | None:
    columnas_normalizadas = {normalizar_texto_columna(col): col for col in columnas}
    for candidato in candidatos:
        normalizado = normalizar_texto_columna(candidato)
        if normalizado in columnas_normalizadas:
            return columnas_normalizadas[normalizado]
    return None


def encontrar_columnas(columnas: list[str], candidatos: list[str]) -> list[str]:
    columnas_normalizadas = {normalizar_texto_columna(col): col for col in columnas}
    encontradas = []
    for candidato in candidatos:
        normalizado = normalizar_texto_columna(candidato)
        columna = columnas_normalizadas.get(normalizado)
        if columna and columna not in encontradas:
            encontradas.append(columna)
    return encontradas


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

    registros: list[dict] = []

    with pd.ExcelFile(ruta_excel) as xls:
        hojas = xls.sheet_names
        for hoja in hojas:
            df = pd.read_excel(xls, sheet_name=hoja)
            registros.extend(leer_filas_hoja_excel(df, hoja))

    if not registros:
        return pd.DataFrame(columns=BASE_COLUMNS)

    return pd.DataFrame(registros, columns=BASE_COLUMNS)


def leer_filas_hoja_excel(df: pd.DataFrame, hoja: str) -> list[dict]:
    registros: list[dict] = []

    if df.empty:
        return registros

    producto_col = encontrar_columna(
        list(df.columns),
        [
            "MATERIAL / PRODUCTO",
            "MATERIAL",
            "MATERIAL PLASTICO / POLIMERO",
            "PRODUCTO ELECTRONICO",
            "PRODUCTO",
            "GRANO",
            "CATEGORIA",
            "CATEGORÍA",
        ],
    )
    precio_cols = encontrar_columnas(
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

    if not producto_col or not precio_cols:
        return registros

    for _, fila in df.iterrows():
        nombre = fila.get(producto_col)
        precio_texto = None
        precio_numero = None
        for precio_col in precio_cols:
            valor_precio = fila.get(precio_col)
            if pd.isna(valor_precio):
                continue
            precio_parseado = limpiar_precio(valor_precio)
            if precio_parseado is not None:
                precio_texto = valor_precio
                precio_numero = precio_parseado
                break

        if pd.isna(nombre) or precio_texto is None:
            continue

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

    return registros


def obtener_todo() -> pd.DataFrame:
    df_excel = leer_productos_excel(EXCEL_PATH)
    if df_excel.empty:
        return pd.DataFrame(columns=BASE_COLUMNS)

    df_excel = df_excel.drop_duplicates(subset=["Producto", "Precio", "Fuente", "Categoria", "Unidad"])
    df_excel = df_excel.sort_values(by=["Categoria", "Producto", "Precio"]).reset_index(drop=True)
    return df_excel


def estado_excel() -> dict:
    if not EXCEL_PATH.exists():
        return {
            "excel_path": str(EXCEL_PATH),
            "excel_actualizado": "",
            "excel_mtime": 0,
        }

    modificado = EXCEL_PATH.stat().st_mtime
    return {
        "excel_path": str(EXCEL_PATH.relative_to(BASE_DIR)) if EXCEL_PATH.is_relative_to(BASE_DIR) else str(EXCEL_PATH),
        "excel_actualizado": pd.Timestamp.fromtimestamp(modificado).strftime("%d/%m/%Y %H:%M:%S"),
        "excel_mtime": modificado,
    }


def productos_para_web() -> list[dict]:
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

    return productos


def usuario_autenticado() -> bool:
    return session.get("authenticated") is True


@app.after_request
def agregar_headers_no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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


@app.route("/api/productos")
def api_productos():
    if not usuario_autenticado():
        return jsonify({"error": "No autenticado"}), 401

    productos = productos_para_web()
    return jsonify(
        {
            "productos": productos,
            "total_productos": len(productos),
            **estado_excel(),
        }
    )


@app.route("/")
def index():
    if not usuario_autenticado():
        return redirect(url_for("login"))

    productos = productos_para_web()
    excel = estado_excel()

    return render_template(
        "index.html",
        productos=productos,
        total_productos=len(productos),
        excel_path=excel["excel_path"],
        excel_actualizado=excel["excel_actualizado"],
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
