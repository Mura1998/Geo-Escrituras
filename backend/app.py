from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from PIL import Image
import io
import fitz
import re

app = Flask(__name__)
CORS(app)

palabras_a_numeros = {
    "cuarenta y cinco": 45,
    "cincuenta": 50,
    "setenta": 70,
}

def convertir_palabra_a_numero(frase):
    return palabras_a_numeros.get(frase.strip().lower(), 0)

def extraer_datos_tecnicos(texto):
    texto = texto.replace('\n', ' ')
    patrones = re.findall(
        r"rumbo (norte|sur) ([a-z\s]+) grados (este|oeste).*?distancia de ([a-z\s]+) metros",
        texto, flags=re.IGNORECASE
    )
    resultado = []
    for dir1, grados_txt, dir2, dist_txt in patrones:
        grados = convertir_palabra_a_numero(grados_txt)
        distancia = convertir_palabra_a_numero(dist_txt)
        resultado.append({
            "rumbo": f"{dir1[0].upper()}{grados}°{dir2[0].upper()}",
            "grados": grados,
            "dir1": dir1[0].upper(),
            "dir2": dir2[0].upper(),
            "distancia": distancia
        })
    return resultado

@app.route('/extraer-escritura', methods=['POST'])
def procesar_escritura():
    archivo = request.files['archivo']
    if archivo.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        imagen = Image.open(archivo.stream)
        texto = pytesseract.image_to_string(imagen, lang='spa')
    elif archivo.filename.lower().endswith('.pdf'):
        pdf = fitz.open(stream=archivo.read(), filetype="pdf")
        pagina = pdf.load_page(0)
        pix = pagina.get_pixmap(dpi=300)
        imagen = Image.open(io.BytesIO(pix.tobytes("png")))
        texto = pytesseract.image_to_string(imagen, lang='spa')
    else:
        return jsonify({"error": "Tipo de archivo no soportado"}), 400

    datos = extraer_datos_tecnicos(texto)
    return jsonify({"texto_extraido": texto, "datos_tecnicos": datos})

if __name__ == '__main__':
    import os
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
@app.route('/comparar-escritura-plano', methods=['POST'])
def comparar_escritura_con_plano():
    import math
    data = request.get_json()
    escritura = data.get("escritura", [])
    plano = data.get("plano", [])

    def calcular_rumbo_y_longitud(x1, y1, x2, y2):
        dx = x2 - x1
        dy = y1 - y2  # invertimos Y por convención gráfica
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

