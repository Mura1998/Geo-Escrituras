import os
import re
import cv2
import pytesseract
import fitz  # PyMuPDF
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Config Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://geo-escrituras.vercel.app"}})

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

# -----------------------------
# Helpers
# -----------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extraer_texto(imagen_path):
    return pytesseract.image_to_string(imagen_path, lang="spa")

def parsear_datos_tecnicos(texto):
    """
    Extrae rumbos y distancias con regex tipo: N 30°E 15.20
    """
    lineas = texto.split("\n")
    datos = []
    for linea in lineas:
        match = re.search(r"([NS]\s?\d+°\s?[EO])\s+(\d+(\.\d+)?)", linea)
        if match:
            rumbo = match.group(1)
            distancia = match.group(2)
            datos.append({"rumbo": rumbo, "distancia": float(distancia)})
    return datos

# -----------------------------
# Rutas
# -----------------------------
@app.route("/extraer-escritura", methods=["POST"])
def extraer_escritura():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    filename = secure_filename("escritura_" + file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Si es PDF, convertimos a imagen
    if filename.lower().endswith(".pdf"):
        pdf = fitz.open(filepath)
        page = pdf[0]
        pix = page.get_pixmap()
        img_path = filepath.replace(".pdf", ".png")
        pix.save(img_path)
        filepath = img_path

    texto = extraer_texto(filepath)
    datos_tecnicos = parsear_datos_tecnicos(texto)

    return jsonify({
        "texto_extraido": texto,
        "datos_tecnicos": datos_tecnicos
    })

@app.route("/extraer-plano", methods=["POST"])
def extraer_plano():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    filename = secure_filename("plano_" + file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Si es PDF, convertir a imagen
    if filename.lower().endswith(".pdf"):
        pdf = fitz.open(filepath)
        page = pdf[0]
        pix = page.get_pixmap()
        img_path = filepath.replace(".pdf", ".png")
        pix.save(img_path)
        filepath = img_path

    # Cargar imagen
    img = cv2.imread(filepath)
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gris, 50, 150, apertureSize=3)
    lineas = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=80, minLineLength=50, maxLineGap=10)

    segmentos = []
    if lineas is not None:
        for linea in lineas:
            x1, y1, x2, y2 = linea[0]
            distancia = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            segmentos.append({
                "x1": int(x1), "y1": int(y1),
                "x2": int(x2), "y2": int(y2),
                "longitud_px": round(float(distancia), 2)
            })

    return jsonify({"segmentos_detectados": segmentos})

@app.route("/comparar-escritura-plano", methods=["POST"])
def comparar_escritura_plano():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No se enviaron datos"}), 400

    escritura = data.get("escritura", [])
    plano = data.get("plano", [])

    comparacion = []
    for e in escritura:
        for s in plano:
            coincide = False
            try:
                dist = float(e.get("distancia", 0))
                long_plano = float(s.get("longitud_px", 0))
                coincide = abs(dist - long_plano) < 5  # tolerancia
            except:
                pass

            comparacion.append({
                "escritura": e,
                "plano": s,
                "coincide": coincide
            })

    return jsonify({"comparacion": comparacion})

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
