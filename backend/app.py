from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import fitz  # PyMuPDF
import pytesseract
import cv2
import numpy as np
from PIL import Image
import io
import base64
import tempfile
import pdfkit

app = Flask(__name__)
CORS(app)

# Configuración general
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB máximo
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return "Geo Escrituras API funcionando"

@app.route('/extraer-escritura', methods=['POST'])
def extraer_escritura():
    try:
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400

        archivo = request.files['archivo']

        if archivo.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400

        if not allowed_file(archivo.filename):
            return jsonify({'error': 'Formato de archivo no permitido'}), 400

        filename = 'escritura.pdf'
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        archivo.save(ruta)

        texto_extraido = extraer_texto_pdf(ruta)

        return jsonify({'texto': texto_extraido})
    except Exception as e:
        print(f"[ERROR] extraer_escritura: {e}")
        return jsonify({'error': 'Error procesando el archivo de escritura'}), 500

@app.route('/extraer-plano', methods=['POST'])
def extraer_plano():
    try:
        if 'archivo' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400

        archivo = request.files['archivo']

        if archivo.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400

        if not allowed_file(archivo.filename):
            return jsonify({'error': 'Formato de archivo no permitido'}), 400

        filename = 'plano.pdf'
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        archivo.save(ruta)

        segmentos = detectar_segmentos_plano(ruta)

        return jsonify({'segmentos': segmentos})
    except Exception as e:
        print(f"[ERROR] extraer_plano: {e}")
        return jsonify({'error': 'Error procesando el plano'}), 500

@app.route('/comparar-escritura-plano', methods=['POST'])
def comparar_escritura_plano():
    try:
        data = request.get_json()
        escritura = data.get('escritura', [])
        plano = data.get('plano', [])

        comparacion = []
        for i in range(min(len(escritura), len(plano))):
            item_esc = escritura[i]
            item_pla = plano[i]
            resultado = {
                'escritura': item_esc,
                'plano': item_pla,
                'coincide': item_esc == item_pla
            }
            comparacion.append(resultado)

        return jsonify({'comparacion': comparacion})
    except Exception as e:
        print(f"[ERROR] comparar_escritura_plano: {e}")
        return jsonify({'error': 'Error al comparar datos'}), 500

@app.route('/generar-reporte', methods=['POST'])
def generar_reporte():
    try:
        data = request.get_json()
        comparacion = data.get('comparacion', [])

        html = "<h1>Reporte de Comparación</h1><table border='1'><tr><th>Escritura</th><th>Plano</th><th>Coincide</th></tr>"
        for item in comparacion:
            html += f"<tr><td>{item['escritura']}</td><td>{item['plano']}</td><td>{'✔️' if item['coincide'] else '❌'}</td></tr>"
        html += "</table>"

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            pdfkit.from_string(html, tmp.name)
            return send_file(tmp.name, as_attachment=True, download_name="reporte.pdf")
    except Exception as e:
        print(f"[ERROR] generar_reporte: {e}")
        return jsonify({'error': 'Error al generar el reporte'}), 500

def extraer_texto_pdf(path):
    texto_total = ""
    try:
        with fitz.open(path) as doc:
            for pagina in doc:
                texto_total += pagina.get_text()
        return texto_total
    except Exception as e:
        print(f"[ERROR] extraer_texto_pdf: {e}")
        return ""

def detectar_segmentos_plano(path):
    try:
        doc = fitz.open(path)
        pix = doc.load_page(0).get_pixmap(dpi=300)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            image.save(tmp_img.name)
            img = cv2.imread(tmp_img.name)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)

        segmentos = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                segmentos.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})

        return segmentos
    except Exception as e:
        print(f"[ERROR] detectar_segmentos_plano: {e}")
        return []

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
