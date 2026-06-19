from flask import Flask, request, jsonify
import zipfile
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Silnik Black Spark Corel-Parser działa!</h1><p>Wyślij plik .cdr metodą POST na /parse</p>"

@app.route('/parse', methods=['POST'])
def parse_cdr():
    if 'file' not in request.files:
        return jsonify({"error": "Brak pliku w żądaniu"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nie wybrano pliku"}), 400

    # ZASADA ULOTNOŚCI: Zapisujemy plik tylko tymczasowo
    temp_path = "temp_file.cdr"
    file.save(temp_path)

    if not zipfile.is_zipfile(temp_path):
        os.remove(temp_path)
        return jsonify({"error": "To nie jest prawidłowy plik Corel (starszy niż X4 lub uszkodzony)"}), 400

    try:
        with zipfile.ZipFile(temp_path, 'r') as archive:
            
            # --- ZMODYFIKOWANY RENTGEN ---
            # Jeśli nie ma pliku root.xml, pokaż dokładnie co jest w środku
            if 'content/root.xml' not in archive.namelist():
                znalezione_pliki = archive.namelist()
                os.remove(temp_path)
                return jsonify({
                    "error": "Brak standardowego pliku content/root.xml",
                    "ale_znalazlem_to": znalezione_pliki
                }), 400
            # -----------------------------
            
            extracted_texts = []
            with archive.open('content/root.xml') as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_content = elem.text.strip()
                        if len(text_content) > 1 and not text_content.startswith('{'):
                            extracted_texts.append(text_content)
            
            # AUTODESTRUKCJA: Usuwamy plik z dysku serwera natychmiast po przetworzeniu
            os.remove(temp_path)
            
            return jsonify({
                "status": "success",
                "message": "Dane zabezpieczone i wyczyszczone z serwera (NDA Safe)",
                "found_texts": extracted_texts
            })

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Blad serwera: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
