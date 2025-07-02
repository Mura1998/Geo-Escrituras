from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pytesseract
from PIL import Image
import io
import fitz
import re
import pdfkit
import os

app = Flask(__name__)
CORS(app)

# Diccionario ampliado de palabras a números
palabras_a_numeros = {
    "cero": 0,
    "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintidós": 22, "veintitrés": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiséis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29,
    "treinta": 30, "treinta y uno": 31, "treinta y dos": 32, "treinta y tres": 33,
    "cuarenta": 40, "cuarenta y cinco": 45, "cuarenta y ocho": 48,
    "cincuenta": 50, "cincuenta y cinco": 55,
    "sesenta": 60, "sesenta y cinco": 65,
    "setenta": 70, "setenta y cinco": 75,
    "ochenta": 80, "ochenta y cinco": 85,
    "noventa": 90, "noventa y cinco": 95,
    "cien": 100, "ciento cinco": 105, "ciento diez": 110, "ciento veinte": 120,
    "ciento treinta": 130, "ciento cincuenta": 150, "ciento ochenta": 180,
    "doscientos": 200, "doscientos veinte": 220, "doscientos setenta": 270,
    "trescientos": 300, "trescientos sesenta": 360
}

def convertir_palabra_a_numero(frase):
    return palabras_a_numeros.get(frase.strip().lower(), 0)

def extraer_datos_tecnicos(texto):
    texto = texto.replace('\n', ' ').lower()
    
    patrones = re.findall(
        r"rumbo\s+(norte|sur)\s+([a-záéíóú\s]+?)\s+grados(?:\s+([a-záéíóú\s]+?)\s+minutos)?(?:\s+([a-záéíóú\s]+?)\s+segundos)?\s+(este|oeste)[^a-z0-9]+distancia\s+(?:de\s+)?([a-záéíóú\s]+?)\s+metros",
        texto, flags=re.IGNORECASE)

    resultado = []
    for dir1, grados_txt, min_txt, seg_txt, dir2, dist_txt in patrones:
        grados = convertir_palabra_a_numero(grados_txt)
        minutos = convertir_palabra_a_numero(min_txt or "cero")
        segundos = convertir_palabra_a_numero(seg_txt or "cero")
        distancia = convertir_palabra_a_numero(dist_txt)

        grados_decimal = grados + minutos / 60 + segundos / 3600

        resultado.append({
            "rumbo": f"{dir1[0].upper()}{round(grados_decimal, 2)}°{dir2[0].upper()}",
            "grados": round(grados_decimal, 2),
            "dir1": dir1[0].upper(),
            "dir2": dir2[0].upper(),
            "distancia": distancia
        })
    return resultado

@app.route('/extraer-escritura', methods=['POST'])
def procesar_escritura():
    try:
        archivo = request.files['archivo']
        texto = ""

        if archivo.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            imagen = Image.open(archivo.stream).convert('L')
            imagen = imagen.point(lambda x: 0 if x < 150 else 255)
            texto = pytesseract.image_to_string(imagen, lang='spa')

        elif archivo.filename.lower().endswith('.pdf'):
            pdf = fitz.open(stream=archivo.read(), filetype="pdf")
            for pagina in pdf:
                pix = pagina.get_pixmap(dpi=300)
                imagen = Image.open(io.BytesIO(pix.tobytes("png"))).convert('L')
                imagen = imagen.point(lambda x: 0 if x < 150 else 255)
                texto += pytesseract.image_to_string(imagen, lang='spa') + "\n"
        else:
            return jsonify({"error": "Tipo de archivo no soportado"}), 400

        print("Texto extraído del OCR:\n", texto)

        if not texto.strip():
            return jsonify({"error": "No se pudo extraer texto del archivo."}), 400

        datos = extraer_datos_tecnicos(texto)

        print("Datos técnicos extraídos:", datos)

        if not datos:
            return jsonify({
                "error": "No se detectaron datos técnicos en el texto extraído.",
                "texto_extraido": texto
            }), 400

        return jsonify({
            "texto_extraido": texto,
            "datos_tecnicos": datos
        })

    except Exception as e:
        print("ERROR FATAL:", str(e))
        return jsonify({"error": f"Error inesperado: {str(e)}"}), 500

@app.route('/comparar-escritura-plano', methods=['POST'])
def comparar_escritura_con_plano():
    import math
    data = request.get_json()
    escritura = data.get("escritura", [])
    plano = data.get("plano", [])

    def calcular_rumbo_y_longitud(x1, y1, x2, y2):
        dx = x2 - x1
        dy = y1 - y2
        longitud = round((dx**2 + dy**2) ** 0.5, 2)
        angulo = (math.degrees(math.atan2(abs(dx), abs(dy))) if dy != 0 else 90)

        if dx >= 0 and dy >= 0:
            rumbo = f"N{round(angulo)}°E"
        elif dx >= 0 and dy < 0:
            rumbo = f"S{round(angulo)}°E"
        elif dx < 0 and dy < 0:
            rumbo = f"S{round(angulo)}°W"
        else:
            rumbo = f"N{round(angulo)}°W"

        return rumbo, angulo, longitud

    resultados = []
    for idx, dato in enumerate(escritura):
        if idx >= len(plano):
            resultados.append({
                "escritura": dato["rumbo"],
                "plano": "No hay línea",
                "coincide": False
            })
            continue

        seg = plano[idx]
        rumbo_plano, angulo, distancia = calcular_rumbo_y_longitud(seg["x1"], seg["y1"], seg["x2"], seg["y2"])

        coincide_rumbo = abs(angulo - dato["grados"]) <= 5
        coincide_dist = abs(distancia - dato["distancia"]) <= 5

        resultados.append({
            "escritura": f'{dato["rumbo"]}, {dato["distancia"]} m',
            "plano": f'{rumbo_plano}, {round(distancia, 1)} px',
            "coincide": coincide_rumbo and coincide_dist,
            "detalles": {
                "rumbo_aprox": rumbo_plano,
                "angulo": round(angulo, 1),
                "distancia_px": distancia,
                "coincide_rumbo": coincide_rumbo,
                "coincide_distancia": coincide_dist
            }
        })

    return jsonify({"comparacion": resultados})

@app.route('/generar-reporte', methods=['POST'])
def generar_reporte_pdf():
    data = request.get_json()
    comparacion = data.get('comparacion', [])

    html = """
    <h1>Informe de Confrontación de Escritura y Plano</h1>
    <table border='1' cellpadding='5' cellspacing='0'>
        <tr>
            <th>#</th>
            <th>Rumbo Escritura</th>
            <th>Rumbo Plano</th>
            <th>Coincide</th>
        </tr>
    """
    for i, item in enumerate(comparacion):
        coincide = "✅" if item["coincide"] else "❌"
        html += f"<tr><td>{i+1}</td><td>{item['escritura']}</td><td>{item['plano']}</td><td>{coincide}</td></tr>"

    html += "</table>"
    output_path = "reporte_confrontacion.pdf"
    pdfkit.from_string(html, output_path)
    return send_file(output_path, as_attachment=True)

@app.route('/test-upload', methods=['POST'])
def test_upload():
    try:
        archivo = request.files['archivo']
        nombre = archivo.filename
        size = len(archivo.read())

        print("---- TEST DE SUBIDA ----")
        print(f"Archivo recibido: {nombre}, tamaño: {size} bytes")

        return jsonify({"mensaje": f"Archivo recibido correctamente: {nombre}, tamaño: {size} bytes"})
    except Exception as e:
        print("Error en /test-upload:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    import cv2
import numpy as np

@app.route('/extraer-plano', methods=['POST'])
def extraer_plano():
    archivo = request.files['archivo']

    if not archivo or not archivo.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Se requiere un archivo PDF"}), 400

    try:
        pdf = fitz.open(stream=archivo.read(), filetype="pdf")
        pagina = pdf[0]  # Solo procesamos la primera página
        pix = pagina.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")

        # Convertimos imagen a OpenCV (matriz numpy)
        img_pil = Image.open(io.BytesIO(img_bytes)).convert("L")
        img_np = np.array(img_pil)

        # Procesamos con OpenCV
        _, img_bin = cv2.threshold(img_np, 150, 255, cv2.THRESH_BINARY_INV)
        edges = cv2.Canny(img_bin, 50, 150, apertureSize=3)

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=80,
            minLineLength=50,
            maxLineGap=10
        )

        segmentos = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                longitud_px = round(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 2)
                segmentos.append({
                    "x1": x1, "y1": y1,
                    "x2": x2, "y2": y2,
                    "longitud_px": longitud_px
                })

        if not segmentos:
            return jsonify({"error": "No se detectaron líneas en el plano"}), 400

        return jsonify({"segmentos_detectados": segmentos})

    except Exception as e:
        return jsonify({"error": f"Error procesando el plano: {str(e)}"}), 500
