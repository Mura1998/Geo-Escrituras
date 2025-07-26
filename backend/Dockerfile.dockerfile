# Imagen base
FROM python:3.10-slim

# Instala Tesseract y dependencias necesarias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Establece el directorio de trabajo
WORKDIR /app

# Copia primero los requirements
COPY requirements.txt ./

# Instala dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Luego copia el resto del código
COPY . .

# Expone el puerto
EXPOSE 5000

# Usa gunicorn para producción
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
