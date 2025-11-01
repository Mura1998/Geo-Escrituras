# app.py
# Flask app para extraer y comparar rumbos y distancias entre escritura y plano.
# Requisitos (ejemplo): Flask, pytesseract, opencv-python, PyMuPDF (fitz), Pillow, numpy
# Instalar:
# pip install Flask pytesseract opencv-python pymupdf Pillow numpy

import re
import io
import json
import math
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import numpy as np
import cv2

app = Flask(__name__)

# Configurables
DISTANCE_TOLERANCE = 0.5  # metros tolerados para considerar coincidente
BEARING_TOLERANCE_DEG = 0.05  # grados tolerados (~3 arcmin)
ALLOWED_EXT = {'pdf', 'png', 'jpg', 'jpeg', 'tiff'}

# --- Utilities: manejo básico de uploads ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# --- Utilities: texto desde PDF/imagen ---
def extract_text_from_pdf_bytes(pdf_bytes):
    """Intenta extraer texto con PyMuPDF; si no hay texto, rasteriza y aplica OCR."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page_no in range(len(doc)):
        page = doc.load_page(page_no)
        txt = page.get_text("text")
        full_text += "\n" + txt
    # si el resultado es muy corto, rasterizamos y aplicamos OCR por seguridad
    if len(re.sub(r'\s','', full_text)) < 10:
        # rasterizar primera página a imagen a alta resolución
        pix = doc.load_page(0).get_pixmap(dpi=300)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr_text = pytesseract.image_to_string(img, lang='spa')
        full_text += "\n[OCR]\n" + ocr_text
    doc.close()
    return full_text

def image_bytes_to_text(img_bytes):
    img = Image.open(io.BytesIO(img_bytes))
    # convert to RGB for tesseract
    img = img.convert("RGB")
    txt = pytesseract.image_to_string(img, lang='spa')
    return txt

# --- Utilities: convertidor simple de palabras a número (español) ---
# Cubre casos comunes (uno..novecientos noventa y nueve mil)
SPANISH_UNITS = {
    "cero":0,"uno":1,"un":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,
    "diez":10,"once":11,"doce":12,"trece":13,"catorce":14,"quince":15,"dieciseis":16,"dieciséis":16,
    "diecisiete":17,"dieciocho":18,"diecinueve":19,"veinte":20,"veintiuno":21,"veintidos":22,"veintidós":22,
    "veintitres":23,"veintitrés":23,"treinta":30,"cuarenta":40,"cincuenta":50,"sesenta":60,"setenta":70,"ochenta":80,"noventa":90,
    "cien":100,"ciento":100,"doscientos":200,"trescientos":300,"cuatrocientos":400,"quinientos":500,"seiscientos":600,"setecientos":700,"ochocientos":800,"novecientos":900,
    "mil":1000
}

def words_to_number(text):
    """Intento básico de convertir secuencia de palabras que representan un número en su valor entero/float."""
    # Normalizar
    s = text.lower().replace('-', ' ').replace(' y ', ' ').replace(',', ' ')
    parts = s.split()
    total = 0
    current = 0
    for p in parts:
        if p in SPANISH_UNITS:
            val = SPANISH_UNITS[p]
            if val == 1000:
                if current == 0:
                    current = 1
                total += current * 1000
                current = 0
            elif val >= 100:
                current += val
            else:
                current += val
        else:
            # intentar parse float directo
            try:
                return float(text.replace(',', '.'))
            except:
                pass
    total += current
    return float(total)

# --- Parser de rumbos y distancias desde texto ---
def parse_rumbos_distancias(text):
    """
    Devuelve lista de dicts: [{'bearing_deg': float, 'distance_m': float, 'raw': '...'}, ...]
    Intenta detectar patrones con grados/minutos/segundos y distancias en metros.
    """
    results = []

    # Normalizar texto
    t = text.replace('\n', ' ').replace('\r',' ')
    t = re.sub(r'\s+', ' ', t)

    # Regex 1: patrón con grados/minutos/segundos y distancia numérica
    # Ej: "Norte ochenta y tres grados veintiocho minutos cuarenta y cuatro segundos Este, con una distancia de veintidós punto ochenta y dos metros"
    # Buscaremos combinaciones de: (palabras o dígitos) grados (palabras o dígitos) minutos (palabras o dígitos) segundos (palabras o dígitos) ... distancia ... metros
    pattern_gms = re.compile(
        r'(?P<pre_dir>(Norte|Sur|Este|Poniente|Oriente|Occidente|Norponiente|Nororiente|Surponiente|Suroriente|Noreste|Noroeste|Suroeste|Sureste)?)\s*'
        r'(?P<deg>[\d]{1,3}|[a-záéíóúñ\s\-]+?)\s*grados?\s*'
        r'(?P<min>[\d]{1,2}|[a-záéíóúñ\s\-]+?)\s*minutos?\s*'
        r'(?P<sec>[\d]{1,2}|[a-záéíóúñ\s\-]+?)\s*segundos?\s*'
        r'(?P<post_dir>(Norte|Sur|Este|Poniente|Oriente|Occidente|Norponiente|Nororiente|Surponiente|Suroriente|Noreste|Noroeste|Suroeste|Sureste)?)',
        flags=re.IGNORECASE
    )

    # Regex 2: distancia en metros: "distancia de 22.82 metros" o "distancia de veinte dos punto ochenta y dos metros"
    pattern_dist = re.compile(
        r'distancia[s]?\s*(?:de|:)?\s*(?P<dist>[\d\.,]+|[a-záéíóúñ\s\-\.\,]+?)\s*(metros|m)\b',
        flags=re.IGNORECASE
    )

    # Primero, buscar todos los bloques GMS y a su alrededor buscar la distancia más cercana
    for m in pattern_gms.finditer(t):
        deg_raw = m.group('deg').strip()
        min_raw = m.group('min').strip()
        sec_raw = m.group('sec').strip()
        pre_dir = (m.group('pre_dir') or '').strip()
        post_dir = (m.group('post_dir') or '').strip()

        # convertir cada componente a número
        def parse_component(s):
            s = s.strip()
            # si hay dígitos
            if re.search(r'\d', s):
                s2 = s.replace(',', '.')
                try:
                    return float(re.sub(r'[^\d\.]', '', s2))
                except:
                    pass
            # si no, intentar palabras
            return words_to_number(s)

        deg = parse_component(deg_raw)
        minu = parse_component(min_raw)
        sec = parse_component(sec_raw)

        # convertir a grados decimales
        bearing = deg + (minu / 60.0) + (sec / 3600.0)

        # determinar cuadrante: si aparece "Norte ... Este" significa desde Norte hacia Este => azimuth = 90 - bearing? 
        # (En escrituras latinas lo usual: "Norte 83°28'44'' Este" => azimuth = 90 - 83.4789 = 6.5211°
        # Para transformar: si formato es "Norte X Este" => az = 90 - X
        # "Sur X Este" => az = 90 + X
        # "Sur X Poniente" => az = 270 - X? There are variations; implement las más comunes:
        q1 = pre_dir.lower()
        q2 = post_dir.lower()
        az = None
        if q1.startswith('norte') or q1.startswith('nor'):
            if q2.startswith('este') or q2.startswith('or'):
                az = 90.0 - bearing
            elif q2.startswith('pon') or q2.startswith('occ') or q2.startswith('o'):
                az = 270.0 + bearing if (270.0 + bearing) < 360 else (270.0 + bearing - 360)
            else:
                # solo "Norte X" asumimos az = 0 +/- bearing?
                az = 0.0 + bearing if q1 == 'norte' else bearing
        elif q1.startswith('sur'):
            if q2.startswith('este') or q2.startswith('or'):
                az = 90.0 + bearing
            elif q2.startswith('pon') or q2.startswith('occ') or q2.startswith('o'):
                az = 270.0 - bearing
            else:
                az = 180.0 + bearing
        else:
            # fallback: usar bearing directamente
            az = bearing % 360.0

        # buscar distancia más cercana después de esta coincidencia (en los próximos 120 caracteres)
        start = m.end()
        nearby = t[start:start+200]
        dist_m = None
        md = pattern_dist.search(nearby)
        if md:
            dist_raw = md.group('dist').strip()
            # si contiene dígitos
            if re.search(r'\d', dist_raw):
                try:
                    dist_m = float(dist_raw.replace(',', '.'))
                except:
                    dist_m = None
            else:
                dist_m = words_to_number(dist_raw)
        # si no se encontró en el nearby, buscar globalmente siguiente distancia
        if dist_m is None:
            mg = pattern_dist.search(t[m.end():m.end()+1000])
            if mg:
                dr = mg.group('dist').strip()
                if re.search(r'\d', dr):
                    try:
                        dist_m = float(dr.replace(',', '.'))
                    except:
                        dist_m = None
                else:
                    dist_m = words_to_number(dr)

        results.append({
            'bearing_deg': float(az) if az is not None else None,
            'distance_m': float(dist_m) if dist_m is not None else None,
            'raw': m.group(0)
        })

    # Regex fallback: si no encontramos GMS, tratar de extraer pares "XXX° YY' ZZ''" o distancias sueltas
    if not results:
        # patrón grados en formato dígitos (ej: 83°28'44")
        dms_pat = re.compile(r'(?P<deg>\d{1,3})\s*°\s*(?P<min>\d{1,2})\s*[\'’]\s*(?P<sec>\d{1,2})\s*(?:["”])?')
        for m in dms_pat.finditer(t):
            deg = int(m.group('deg')); minu = int(m.group('min')); sec = int(m.group('sec'))
            az = deg + minu/60.0 + sec/3600.0
            # buscar distancia cerca
            start = m.end()
            md = pattern_dist.search(t[start:start+200]) or pattern_dist.search(t)
            dist_m = None
            if md:
                dr = md.group('dist').strip()
                try:
                    dist_m = float(dr.replace(',', '.'))
                except:
                    dist_m = words_to_number(dr)
            results.append({'bearing_deg': az, 'distance_m': dist_m, 'raw': m.group(0)})

    # finalmente, si no hay resultados, tratar de obtener todas las distancias aisladas (como último recurso)
    if not results:
        for md in pattern_dist.finditer(t):
            dr = md.group('dist').strip()
            try:
                dist_m = float(dr.replace(',', '.'))
            except:
                dist_m = words_to_number(dr)
            results.append({'bearing_deg': None, 'distance_m': dist_m, 'raw': md.group(0)})

    return results

# --- Comparador simple entre dos listas ---
def compare_lists(escritura_list, plano_list, distance_tol=DISTANCE_TOLERANCE, bearing_tol=BEARING_TOLERANCE_DEG):
    """
    Compara por índice (posición) y por búsqueda del mejor match. Devuelve coincidencias y discrepancias.
    """
    report = {'matches': [], 'distance_errors': [], 'bearing_errors': [], 'unmatched_plano': [], 'unmatched_escritura': []}

    used_plano = set()

    # Intent: emparejar por índice si longitudes iguales
    if len(escritura_list) == len(plano_list) and len(escritura_list) > 0:
        for i, (e, p) in enumerate(zip(escritura_list, plano_list)):
            d_e = e.get('distance_m'); d_p = p.get('distance_m')
            b_e = e.get('bearing_deg'); b_p = p.get('bearing_deg')
            dist_diff = None; bearing_diff = None
            status = 'match'
            if d_e is not None and d_p is not None:
                dist_diff = abs(d_e - d_p)
                if dist_diff > distance_tol:
                    status = 'distance_mismatch'
            if b_e is not None and b_p is not None:
                bearing_diff = abs(((b_e - b_p + 180) % 360) - 180)  # angular difference smallest
                if bearing_diff > bearing_tol:
                    status = 'bearing_mismatch' if status=='match' else status + ';bearing_mismatch'
            report['matches' if status=='match' else ('distance_errors' if 'distance_mismatch' in status and 'bearing_mismatch' not in status else 'bearing_errors')].append({
                'index': i,
                'escritura': e,
                'plano': p,
                'status': status,
                'distance_diff': dist_diff,
                'bearing_diff': bearing_diff
            })
            used_plano.add(i)
    else:
        # Emparejar por búsqueda del mejor match (por distancia y/o bearing)
        for ie, e in enumerate(escritura_list):
            best_j = None
            best_score = 1e9
            for jp, p in enumerate(plano_list):
                if jp in used_plano:
                    continue
                score = 0.0
                # si hay distancias, usar diferencia normalizada
                if e.get('distance_m') is not None and p.get('distance_m') is not None:
                    score += abs(e['distance_m'] - p['distance_m'])
                # si hay bearings, añadir diferencia angular
                if e.get('bearing_deg') is not None and p.get('bearing_deg') is not None:
                    ang = abs(((e['bearing_deg'] - p['bearing_deg'] + 180) % 360) - 180)
                    score += ang  # ponderación simple
                if score < best_score:
                    best_score = score
                    best_j = jp
            if best_j is not None:
                used_plano.add(best_j)
                p = plano_list[best_j]
                d_diff = None; b_diff = None
                if e.get('distance_m') is not None and p.get('distance_m') is not None:
                    d_diff = abs(e['distance_m'] - p['distance_m'])
                    if d_diff > distance_tol:
                        report['distance_errors'].append({'escritura_index': ie, 'plano_index': best_j, 'distance_diff': d_diff, 'escritura': e, 'plano': p})
                    else:
                        # check bearing
                        if e.get('bearing_deg') is not None and p.get('bearing_deg') is not None:
                            b_diff = abs(((e['bearing_deg'] - p['bearing_deg'] + 180) % 360) - 180)
                            if b_diff > bearing_tol:
                                report['bearing_errors'].append({'escritura_index': ie, 'plano_index': best_j, 'bearing_diff': b_diff, 'escritura': e, 'plano': p})
                            else:
                                report['matches'].append({'escritura_index': ie, 'plano_index': best_j, 'distance_diff': d_diff, 'bearing_diff': b_diff, 'escritura': e, 'plano': p})
                        else:
                            # only distance matched
                            report['matches'].append({'escritura_index': ie, 'plano_index': best_j, 'distance_diff': d_diff, 'bearing_diff': b_diff, 'escritura': e, 'plano': p})
            else:
                report['unmatched_escritura'].append({'index': ie, 'escritura': e})

        # any plano not used:
        for j, p in enumerate(plano_list):
            if j not in used_plano:
                report['unmatched_plano'].append({'index': j, 'plano': p})

    return report

# --- Endpoints ---

@app.route('/extraer-escritura', methods=['POST'])
def extraer_escritura():
    """
    Espera archivo (image/pdf) con la escritura.
    Devuelve el texto extraído y la lista de rumbos/distancias detectadas.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(f.filename)
    data = f.read()
    try:
        if filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf_bytes(data)
        else:
            text = image_bytes_to_text(data)
    except Exception as e:
        return jsonify({'error': 'Error processing file', 'detail': str(e)}), 500

    parsed = parse_rumbos_distancias(text)
    return jsonify({'text': text, 'parsed': parsed})

@app.route('/extraer-plano', methods=['POST'])
def extraer_plano():
    """
    Espera archivo (pdf/image) con el plano.
    Se intenta extraer los números presentes (rumbos y distancias).
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filename = secure_filename(f.filename)
    data = f.read()
    try:
        if filename.lower().endswith('.pdf'):
            text = extract_text_from_pdf_bytes(data)
        else:
            text = image_bytes_to_text(data)
    except Exception as e:
        return jsonify({'error': 'Error processing file', 'detail': str(e)}), 500

    parsed = parse_rumbos_distancias(text)
    return jsonify({'text': text, 'parsed': parsed})

@app.route('/comparar-escritura-plano', methods=['POST'])
def comparar_escritura_plano():
    """
    Recibe dos archivos: 'escritura' y 'plano' (multipart).
    Extrae y compara. Devuelve un reporte JSON.
    """
    if 'escritura' not in request.files or 'plano' not in request.files:
        return jsonify({'error': 'Se requieren ambos archivos: escritura y plano'}), 400
    f_e = request.files['escritura']
    f_p = request.files['plano']

    ne = secure_filename(f_e.filename)
    npf = secure_filename(f_p.filename)

    data_e = f_e.read()
    data_p = f_p.read()

    try:
        if ne.lower().endswith('.pdf'):
            text_e = extract_text_from_pdf_bytes(data_e)
        else:
            text_e = image_bytes_to_text(data_e)
        if npf.lower().endswith('.pdf'):
            text_p = extract_text_from_pdf_bytes(data_p)
        else:
            text_p = image_bytes_to_text(data_p)
    except Exception as e:
        return jsonify({'error': 'Error extrayendo textos', 'detail': str(e)}), 500

    parsed_e = parse_rumbos_distancias(text_e)
    parsed_p = parse_rumbos_distancias(text_p)

    report = compare_lists(parsed_e, parsed_p)

    # adjuntar textos y parseos para debug
    report['text_escritura'] = text_e[:10000]  # limitar tamaño
    report['text_plano'] = text_p[:10000]
    report['parsed_escritura'] = parsed_e
    report['parsed_plano'] = parsed_p

    return jsonify(report)

@app.route('/generar-reporte', methods=['POST'])
def generar_reporte():
    """
    Endpoint simple que recibe JSON con 'report' (como el generado por comparar)
    y devuelve un PDF resumen (o JSON si no se desea generar PDF).
    Aquí devolvemos JSON para simplicidad; puedes expandir a PDF con reportlab si quieres.
    """
    try:
        payload = request.get_json()
    except:
        return jsonify({'error': 'JSON inválido'}), 400
    if not payload:
        return jsonify({'error': 'JSON vacío'}), 400

    # Por ahora simplemente devolvemos el mismo objeto (podrías formatearlo a PDF)
    return jsonify(payload)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
