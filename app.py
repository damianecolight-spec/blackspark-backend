from flask import Flask, request, jsonify, send_file
import zipfile
import xml.etree.ElementTree as ET
import os
import io
import random

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Silnik Black Spark (V4.0: Analiza Przestrzenna) działa!</h1><p>Wyślij plik .cdr metodą POST na /parse</p>"

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
        return jsonify({"error": "To nie jest prawidłowy plik Corel"}), 400

    try:
        with zipfile.ZipFile(temp_path, 'r') as archive:
            zawartosc = archive.namelist()
            
            cel_xml = None
            if 'content/root.xml' in zawartosc:
                cel_xml = 'content/root.xml'
            elif 'metadata/textinfo.xml' in zawartosc:
                cel_xml = 'metadata/textinfo.xml'
            
            if not cel_xml:
                os.remove(temp_path)
                return jsonify({"error": "Brak danych wektorowych."}), 400

            # Zamiast prostej listy, tworzymy listę obiektów przestrzennych
            extracted_elements = []
            
            # Zmienne pomocnicze dla plików bez twardych koordynatów
            fallback_y = 100
            
            with archive.open(cel_xml) as xml_file:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                # Skanujemy cały plik XML w poszukiwaniu elementów i ich atrybutów
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        text_content = elem.text.strip()
                        
                        if len(text_content) > 1 and not text_content.startswith('{'):
                            safe_text = text_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            
                            # 1. SZUKANIE WSPÓŁRZĘDNYCH
                            # Corel często chowa pozycje w atrybutach x/y, transform, lub w tagach nadrzędnych
                            x_pos = elem.attrib.get('x') or elem.attrib.get('X')
                            y_pos = elem.attrib.get('y') or elem.attrib.get('Y')
                            
                            # Jeśli tag nie ma x/y, sprawdzamy jego rodzica (częsta praktyka w wektorach)
                            # W uproszczonym PoC symulujemy inteligentne pozycjonowanie dla plików metadanych
                            if not x_pos:
                                x_pos = "50" # Domyślny margines lewy
                            
                            if not y_pos:
                                y_pos = str(fallback_y)
                                fallback_y += 30 # Przesuwamy w dół dla kolejnego elementu bez koordynatów
                            
                            # 2. SZUKANIE FONTU I ROZMIARU
                            font_size = elem.attrib.get('font-size', '16')
                            fill_color = elem.attrib.get('fill', '#ffffff')
                            
                            # Dodajemy przechwycony element z jego pełną geometrią
                            extracted_elements.append({
                                "text": safe_text,
                                "x": x_pos,
                                "y": y_pos,
                                "size": font_size,
                                "color": fill_color
                            })
            
            os.remove(temp_path)

            # --- GENERATOR PRZESTRZENNEGO SVG ---
            # Skalujemy płótno na podstawie najbardziej wysuniętego elementu (lub używamy stałego 1200x800)
            svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1200" width="1200" height="1200">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#111116" />
      <stop offset="100%" stop-color="#2a2c45" />
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bgGradient)" />
  
  <g id="Warstwa_Danych_Odzyskanych">
'''
            # Wstrzykujemy każdy element dokładnie w jego wyliczone miejsce
            for el in extracted_elements:
                # Oczyszczamy wartości liczbowe z ewentualnych dopisków "px" czy "pt"
                clean_x = ''.join(filter(lambda c: c.isdigit() or c == '.', str(el['x'])))
                clean_y = ''.join(filter(lambda c: c.isdigit() or c == '.', str(el['y'])))
                clean_size = ''.join(filter(lambda c: c.isdigit() or c == '.', str(el['size'])))
                
                # Zabezpieczenie przed pustymi wartościami
                clean_x = clean_x if clean_x else "50"
                clean_y = clean_y if clean_y else "50"
                clean_size = clean_size if clean_size else "16"

                svg_content += f'    <text x="{clean_x}" y="{clean_y}" font-family="Arial" font-size="{clean_size}" fill="{el["color"]}">{el["text"]}</text>\n'

            svg_content += '''  </g>\n</svg>'''

            mem = io.BytesIO()
            mem.write(svg_content.encode('utf-8'))
            mem.seek(0)

            return send_file(
                mem, 
                as_attachment=True, 
                download_name="BlackSpark_Layout_Odzysk.svg", 
                mimetype='image/svg+xml'
            )

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Blad krytyczny serwera: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
