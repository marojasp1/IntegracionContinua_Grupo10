# Imagen base: Python ya instalado
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Primero las librerías (así Docker las guarda en caché)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Luego el código de la app
COPY . .

# Comando que arranca la app
CMD ["python", "app.py"]