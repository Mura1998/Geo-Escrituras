import re
import io
import json
import math
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import numpy as np
import cv2

# --- Configuración base ---
app = Flask(__name__)
CORS(app)

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

DISTANCE_TOLERANCE = 0.5  # metros tolerados
BEARING_TOLERANCE_DEG = 0.05  # grados tolerados (~3 arcmin)
ALLOWED_EXT = {'pdf', 'png', 'jpg', 'jpeg', 'tiff'}

# --- Utilidades de archivos ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# --- OCR desde PDF o imagen ---
def extract_text_from_pdf_bytes(pdf_bytes):
    """Extrae texto de un PDF; si no tiene texto, aplica OCR."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page_no in range(len(doc)):
        page = doc.load_page(page_no)
        txt = page.get_text("text")
        full_text += "\n" + txt
    if len(re.sub(r'\s', '', full_text)) < 10:
        pix = doc.load_page(0).get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr_text = pytesseract.image_to_string(img, lang='spa')
        full_text += "\n[OCR]\n" + ocr_text
    doc.close()
    return full_text

def image_bytes_to_text(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    img = img.convert("RGB")
    txt = pytesseract.image_to_string(img, lang='spa')
    return txt

# --- Parser de rumbos y distancias ---
def parse_rumbos_distancias(text):
    def clean_text(t):
        t = t.replace('\n', ' ').replace('\r', ' ')
        t = re.sub(r'\s+', ' ', t)
        t = t.replace('”', '"').replace('“', '"').replace('º', '°').replace('?', '°')
        return t

    def words_to_number(texto):
        mapa = {
            'uno': 1, 'una': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
            'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10, 'once': 11,
            'doce': 12, 'trece': 13, 'catorce': 14, 'quince': 15, 'dieciséis': 16,
            'diecisiete': 17, 'dieciocho': 18, 'diecinueve': 19, 'veinte': 20,
            'treinta': 30, 'cuarenta': 40, 'cincuenta': 50, 'sesenta': 60,
            'setenta': 70, 'ochenta': 80, 'noventa': 90, 'cien': 100
        }
        texto = texto.lower()
        total = 0
        for palabra, valor in mapa.items():
            if palabra in texto:
                total += valor
        return total

    def texto_a_numero(txt):
        """Convierte 'veintidós punto ochenta y dos metros' a 22.82."""
        if not txt:
            return 0.0
        txt = txt.lower()
        numeros = {
            "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
            "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12,
            "trece": 13, "catorce": 14, "quince": 15, "dieciséis": 16, "diecisiete": 17,
            "dieciocho": 18, "diecinueve": 19, "veinte": 20, "veintiuno": 21, "veintidós": 22,
            "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26,
            "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30,
            "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70,
            "ochenta": 80, "noventa": 90, "cien": 100
        }
        m = re.search(r"([a-záéíóú\s]+?)\s+punto\s+([a-záéíóú\s]+?)", txt)
        if m:
            parte_entera = sum(numeros.get(w.strip(), 0) for w in m.group(1).split())
            parte_decimal = sum(numeros.get(w.strip(), 0)/100 for w in m.group(2).split())
            return round(parte_entera + parte_decimal, 2)
        for palabra, valor in numeros.items():
            if re.search(rf"\b{palabra}\b", txt):
                return float(valor)
        return 0.0

    t = clean_text(text)
    results = []

    # --- Formato tipo "N83°28'44\"E 22.82" ---
    pattern_compacto = re.compile(
        r'([NS])\s*([0-9]{1,3})[°º"”]?\s*([0-9]{1,2})[\'’]?\s*([0-9]{1,2})["”]?\s*([EW])\s*([0-9]+(?:[\.,][0-9]+)?)',
        flags=re.IGNORECASE
    )
    for m in pattern_compacto.finditer(t):
        n_s, deg, minu, sec, e_w, dist = m.groups()
        bearing = float(deg) + float(minu)/60 + float(sec)/3600
        dist_m = float(dist.replace(',', '.'))
        if n_s.upper() == 'N' and e_w.upper() == 'E': az = 90 - bearing
        elif n_s.upper() == 'S' and e_w.upper() == 'E': az = 90 + bearing
        elif n_s.upper() == 'S' and e_w.upper() == 'W': az = 270 - bearing
        else: az = 270 + bearing
        results.append({
            'bearing_deg': round(az % 360, 6),
            'distance_m': round(dist_m, 2),
            'raw': m.group(0)
        })

    # --- Formato tipo escritura ---
    pattern_texto = re.compile(
        r'(Norte|Sur)\s+([a-z\d\s]+?)\s+grados\s+([a-z\d\s]+?)\s+minutos\s+([a-z\d\s]+?)\s+segundos\s+(Este|Oeste)[^\.]{0,80}?(?:distancia\s+(?:de\s+)?([a-záéíóú0-9\s\.]+?)\s+metro)?',
        flags=re.IGNORECASE
    )
    for m in pattern_texto.finditer(t):
        n_s, deg_raw, min_raw, sec_raw, e_w, dist_raw = m.groups()
        def num(x): return float(re.sub(r'[^\d\.]', '', x)) if re.search(r'\d', x) else words_to_number(x)
        deg, minu, sec = num(deg_raw), num(min_raw), num(sec_raw)
        bearing = deg + minu/60 + sec/3600
        if n_s.lower().startswith('n'):
            az = 90 - bearing if e_w.lower().startswith('e') else 270 + bearing
        else:
            az = 90 + bearing if e_w.lower().startswith('e') else 270 - bearing
        dist_val = texto_a_numero(dist_raw) if dist_raw else 0.0
        results.append({
            'bearing_deg': round(az % 360, 6),
            'distance_m': round(dist_val, 2),
            'raw': m.group(0)
        })

    return results

# --- Comparador de listas ---
def compare_lists(escritura_list, plano_list, distance_tol=DISTANCE_TOLERANCE, bearing_tol=BEARING_TOLERANCE_DEG):
    report = {'matches': [], 'distance_errors': [], 'bearing_errors': [], 'unmatched_plano': [], 'unmatched_escritura': []}
    used_plano = set()
    for ie, e in enumerate(escritura_list):
        best_j = None
        best_score = 1e9
        for jp, p in enumerate(plano_list):
            if jp in used_plano:
                continue
            score = abs(e['bearing_deg'] - p['bearing_deg']) + abs(e['distance_m'] - p['distance_m'])
            if score < best_score:
                best_score = score
                best_j = jp
        if best_j is not None:
            used_plano.add(best_j)
            p = plano_list[best_j]
            d_diff = abs(e['distance_m'] - p['distance_m'])
            b_diff = abs(((e['bearing_deg'] - p['bearing_deg'] + 180) % 360) - 180)
            if d_diff > distance_tol:
                report['distance_errors'].append({'escritura_index': ie, 'plano_index': best_j, 'distance_diff': d_diff, 'escritura': e, 'plano': p})
            elif b_diff > bearing_tol:
                report['bearing_errors'].append({'escritura_index': ie, 'plano_index': best_j, 'bearing_diff': b_diff, 'escritura': e, 'plano': p})
            else:
                report['matches'].append({'escritura_index': ie, 'plano_index': best_j, 'distance_diff': d_diff, 'bearing_diff': b_diff, 'escritura': e, 'plano': p})
        else:
            report['unmatched_escritura'].append({'index': ie, 'escritura': e})
    for j, p in enumerate(plano_list):
        if j not in used_plano:
            report['unmatched_plano'].append({'index': j, 'plano': p})
    return report

# --- Endpoints Flask ---
@app.route('/extraer-escritura', methods=['POST'])
def extraer_escritura():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    f = request.files['file']
    filename = secure_filename(f.filename)
    data = f.read()
    text = extract_text_from_pdf_bytes(data) if filename.lower().endswith('.pdf') else image_bytes_to_text(data)
    parsed = parse_rumbos_distancias(text)
    return jsonify({'text': text, 'parsed': parsed})

@app.route('/extraer-plano', methods=['POST'])
def extraer_plano():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    f = request.files['file']
    filename = secure_filename(f.filename)
    data = f.read()
    text = extract_text_from_pdf_bytes(data) if filename.lower().endswith('.pdf') else image_bytes_to_text(data)
    parsed = parse_rumbos_distancias(text)
    return jsonify({'text': text, 'parsed': parsed})

@app.route('/comparar-escritura-plano', methods=['POST'])
def comparar_escritura_plano():
    if 'escritura' not in request.files or 'plano' not in request.files:
        return jsonify({'error': 'Se requieren ambos archivos: escritura y plano'}), 400
    f_e = request.files['escritura']
    f_p = request.files['plano']
    data_e = f_e.read()
    data_p = f_p.read()
    text_e = extract_text_from_pdf_bytes(data_e) if f_e.filename.lower().endswith('.pdf') else image_bytes_to_text(data_e)
    text_p = extract_text_from_pdf_bytes(data_p) if f_p.filename.lower().endswith('.pdf') else image_bytes_to_text(data_p)
    parsed_e = parse_rumbos_distancias(text_e)
    parsed_p = parse_rumbos_distancias(text_p)
    report = compare_lists(parsed_e, parsed_p)
    report['text_escritura'] = text_e[:10000]
    report['text_plano'] = text_p[:10000]
    report['parsed_escritura'] = parsed_e
    report['parsed_plano'] = parsed_p
    return jsonify(report)

@app.route('/generar-reporte', methods=['POST'])
def generar_reporte():
    payload = request.get_json()
    if not payload:
        return jsonify({'error': 'JSON vacío'}), 400
    return jsonify(payload)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
