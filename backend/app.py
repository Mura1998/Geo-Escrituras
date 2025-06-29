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
    app.run(debug=True)