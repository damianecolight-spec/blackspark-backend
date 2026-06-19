from flask import Flask, request, jsonify
import zipfile
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Silnik Black Spark Corel-Parser działa! (Wersja 2.0)</h1><p>Wyślij plik .cdr metodą POST na /parse</p>"

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
            
            # --- INTELIGENTNE WYSZUKIWANIE ---
            # Sprawdzamy kilka możliwych lokalizacji tekstów w zależności od wersji Corela
            cel_xml = None
            if 'content/root.xml' in zawartosc:
                cel_xml = 'content/root.xml'
            elif 'metadata/textinfo.xml' in zawartosc:
                cel_xml = 'metadata/textinfo.xml'
            
            # Jeśli plik to twardy binariusz (.dat) bez żadnego XML-a
            if not cel_xml:
                os.remove(temp_path)
                return jsonify({
                    "error": "Ten plik zapisano w formacie czysto binarnym. Spróbuj zapisać go w Corelu bez włączonej kompresji.",
                    "znalazlem_te_pliki": zawartosc
                }), 400

            print(f"🔓 Namierzono cel: {cel_xml}")
            
            extracted_texts = []
            with archive.open(cel_xml) as xml_file:
                # Omijamy błędy z przestrzeniami nazw (namespaces)
                tree = ET.parse(xml_file)
                root = tree.getroot()

                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_content = elem.text.strip()
                        if len(text_content) > 1 and not text_content.startswith('{'):
                            extracted_texts.append(text_content)
            
            os.remove(temp_path)
            
            return jsonify({
                "status": "success",
                "message": f"Przechwycono z pliku: {cel_xml}",
                "found_texts": extracted_texts
            })

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Blad serwera: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
