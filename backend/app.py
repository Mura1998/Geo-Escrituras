from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import cv2
import numpy as np
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/extraer-escritura', methods=['POST'])
def extraer_escritura():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    filename = secure_filename('escritura_' + file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    texto = extraer_texto(filepath)
    return jsonify({'texto': texto})

@app.route('/extraer-plano', methods=['POST'])
def extraer_plano():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    filename = secure_filename('plano_' + file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    segmentos = detectar_segmentos(filepath)
    return jsonify({'segmentos': segmentos})

@app.route('/test-upload', methods=['POST'])
def test_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No se recibió archivo'}), 400
    archivo = request.files['file']
    return jsonify({'mensaje': f'Archivo {archivo.filename} recibido correctamente'}), 200

@app.route('/test-upload/<tipo>', methods=['GET'])
def test_upload_tipo(tipo):
    for filename in os.listdir(UPLOAD_FOLDER):
        if tipo in filename:
            return jsonify({'estado': 'ok'})
    return jsonify({'estado': 'no_encontrado'})

def extraer_texto(filepath):
    if filepath.lower().endswith('.pdf'):
        texto_completo = ""
        with fitz.open(filepath) as doc:
            for page in doc:
                texto_completo += page.get_text()
        return texto_completo
    else:
        imagen = Image.open(filepath)
        return pytesseract.image_to_string(imagen)

def detectar_segmentos(filepath):
    imagen = None
    if filepath.lower().endswith('.pdf'):
        doc = fitz.open(filepath)
        pix = doc.load_page(0).get_pixmap()
        imagen = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    else:
        imagen = cv2.imread(filepath)

    if imagen is None:
        return []

    gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
    bordes = cv2.Canny(gris, 50, 150)
    lineas = cv2.HoughLinesP(bordes, 1, np.pi / 180, threshold=80, minLineLength=50, maxLineGap=10)
    segmentos = []
    if lineas is not None:
        for linea in lineas:
            x1, y1, x2, y2 = linea[0]
            distancia = np.hypot(x2 - x1, y2 - y1)
            segmentos.append({
                'x1': int(x1), 'y1': int(y1),
                'x2': int(x2), 'y2': int(y2),
                'longitud': round(distancia, 2)
            })
    return segmentos

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
