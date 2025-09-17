# Imagen base liviana con Python
FROM python:3.10-slim

# Instala Tesseract (incluyendo idioma español) y dependencias del sistema
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establece directorio de trabajo
WORKDIR /app

# Copia todos los archivos del backend
COPY . .

# Instala dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Render asigna el puerto en la variable de entorno PORT
EXPOSE 5000

# Comando para iniciar la app (Render pasará $PORT automáticamente)
CMD ["python", "app.py"]
