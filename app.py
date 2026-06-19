from flask import Flask, request, jsonify, send_file
import zipfile
import xml.etree.ElementTree as ET
import os
import io

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Silnik Black Spark Corel-Parser (Wersja 3.0: Generator SVG) działa!</h1><p>Wyślij plik .cdr metodą POST na /parse</p>"

@app.route('/parse', methods=['POST'])
def parse_cdr():
    if 'file' not in request.files:
        return jsonify({"error": "Brak pliku w żądaniu"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nie wybrano pliku"}), 400

    temp_path = "temp_file.cdr"
    file.save(temp_path)

    if not zipfile.is_zipfile(temp_path):
        os.remove(temp_path)
        return jsonify({"error": "To nie jest prawidłowy plik Corel (starszy niż X4 lub uszkodzony)"}), 400

    try:
        with zipfile.ZipFile(temp_path, 'r') as archive:
            zawartosc = archive.namelist()
            
            # Namierzanie odpowiedniego pliku z tekstami
            cel_xml = None
            if 'content/root.xml' in zawartosc:
                cel_xml = 'content/root.xml'
            elif 'metadata/textinfo.xml' in zawartosc:
                cel_xml = 'metadata/textinfo.xml'
            
            if not cel_xml:
                os.remove(temp_path)
                return jsonify({
                    "error": "Brak danych wektorowych w tym pliku. Prawdopodobnie czysta bitmapa.",
                }), 400

            extracted_texts = []
            with archive.open(cel_xml) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_content = elem.text.strip()
                        if len(text_content) > 1 and not text_content.startswith('{'):
                            # Zabezpieczamy znaki specjalne dla formatu XML/SVG
                            safe_text = text_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            extracted_texts.append(safe_text)
            
            os.remove(temp_path)

            # --- GENERATOR NATYWNEGO SVG ---
            # Obliczamy dynamiczną wysokość pliku, żeby żaden tekst nie ucięło
            svg_height = max(800, len(extracted_texts) * 35 + 100)
            
            svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {svg_height}" width="1000" height="{svg_height}">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#111116" />
      <stop offset="100%" stop-color="#1f2136" />
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGradient)" rx="10" ry="10" />
  
  <g id="Warstwa_Naglowek">
    <text x="50" y="60" font-family="Arial" font-size="24" font-weight="bold" fill="#ff3e6c">BLACK SPARK DTP: ODZYSKANE DANE</text>
    <line x1="50" y1="80" x2="950" y2="80" stroke="#ffb142" stroke-width="2" />
  </g>

  <g id="Warstwa_Teksty_Z_Corela">
'''
            # Układamy wyciągnięte bloki tekstu w równych odstępach pionowych
            y_pos = 130
            for text in extracted_texts:
                svg_content += f'    <text x="50" y="{y_pos}" font-family="Arial" font-size="14" fill="#ffffff">{text}</text>\n'
                y_pos += 30

            svg_content += '''  </g>\n</svg>'''

            # Pakujemy kod SVG do wirtualnego pliku w pamięci RAM
            mem = io.BytesIO()
            mem.write(svg_content.encode('utf-8'))
            mem.seek(0)

            # Wysyłamy fizyczny plik z powrotem do przeglądarki użytkownika
            return send_file(
                mem, 
                as_attachment=True, 
                download_name="BlackSpark_Odzysk.svg", 
                mimetype='image/svg+xml'
            )

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Blad krytyczny serwera: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
