# Imagen base: Python ya instalado
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor
WORKDIR /app

# Primero las librerías (así Docker las guarda en caché)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Luego el código de la app
COPY . .

EXPOSE 5000

# Comprueba que la app responde dentro del contenedor
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/', timeout=3)"

# Comando que arranca la app
CMD ["python", "app.py"]
