# Deploy de Convertidor Lapacho

## 1. Archivos que deben quedar en el proyecto

- `app.py`
- `templates/`
- `static/`
- `data/excel.xlsx`
- `requirements.txt`
- `Procfile`

## 2. Variables de entorno recomendadas

- `APP_USERNAME`
- `APP_PASSWORD`
- `SECRET_KEY`
- `EXCEL_PATH`

En Render o Railway podés usar:

- `APP_USERNAME=lapacho`
- `APP_PASSWORD=lapacho123`
- `SECRET_KEY=una-clave-larga-y-segura`
- `EXCEL_PATH=data/excel.xlsx`

## 3. Deploy en Render

1. Subí este proyecto a GitHub.
2. En Render creá un `Web Service`.
3. Conectá el repositorio.
4. Configurá:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. Cargá las variables de entorno.
6. Deployá y compartí la URL pública.

## 4. Deploy en Railway

1. Subí este proyecto a GitHub.
2. Creá un proyecto nuevo en Railway.
3. Elegí `Deploy from GitHub repo`.
4. Cargá las variables de entorno.
5. Railway debería levantarlo con `gunicorn app:app` usando el `Procfile`.

## 5. Prueba local

```powershell
pip install -r requirements.txt
python app.py
```
