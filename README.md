# Proyecto Flask + TailwindCSS + Jinja

Aplicación web basada en **Flask (Python)** para el backend y **TailwindCSS + Jinja2** para el frontend.  
El proyecto usa una estructura modular, ideal para desarrollo colaborativo y extensible.

---

## Tecnologías utilizadas

- **Python 3.10+**
- **Flask** — Framework backend
- **Jinja2** — Motor de plantillas HTML
- **TailwindCSS** — Framework de estilos
- **Node.js + npm** — Para compilar Tailwind
- **Virtualenv** — Entorno virtual para dependencias de Python

## Requisitos

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js (v18+)](https://nodejs.org/)
- [npm](https://www.npmjs.com/) (instalado junto con Node)
- [Git](https://git-scm.com/)

---

## Crear migraciones

- Inicializar migraciones: `flask db init`
- Crear migracion: `flask db migrate -m "nombre_migracion"`
- Actualizar DB: `flask db upgrade`

## Instalación del proyecto

1. **Clonar el repositorio**
   ```bash
   git clone tu_repositorio
   cd tu_repositorio
   ```
2. **Crear entorno virtual**

   ```
   python -m venv env

   env\Scripts\Activate.ps1

   por si no funciona el de arriba: env\Scripts\Activate
   ```

3. **Instalar dependencias de python y node**

   ```
   pip install -r requirements.txt

   npm install
   ```

   **Para actualizar el requirements.txt**

   _Necesario para instalaciones de nuevas dependencias_

   ```
   pip freeze > requirements.txt
   ```

4. **Ejecucion (Dos terminales)**

   Ejecucion en modo watch de tailwindcss (estilos)

   ```
   npx tailwindcss -i ./app/static/css/input.css -o ./app/static/css/style.css --watch
   ```

   Ejecucion del entorno virtual (Flask)

   ```
    python app.py
   ```
