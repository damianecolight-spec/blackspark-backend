from flask import Flask, request, jsonify, send_file
import zipfile
import xml.etree.ElementTree as ET
import os
import io

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Black Spark: Geometry Extractor (V1.0)</h1><p>Ekstraktor samych konturów (bez tekstów).</p>"

@app.route('/parse', methods=['POST'])
def parse_geometry():
    if 'file' not in request.files:
        return jsonify({"error": "Brak pliku"}), 400
    
    file = request.files['file']
    temp_path = "temp_geometry.cdr"
    file.save(temp_path)

    if not zipfile.is_zipfile(temp_path):
        os.remove(temp_path)
        return jsonify({"error": "Nieprawidłowy plik"}), 400

    try:
        with zipfile.ZipFile(temp_path, 'r') as archive:
            # Szukamy głównych plików XML z definicjami krzywych
            xml_files = [f for f in archive.namelist() if f.endswith('.xml')]
            
            all_paths = []
            
            for xml_name in xml_files:
                with archive.open(xml_name) as xml_file:
                    try:
                        tree = ET.parse(xml_file)
                        root = tree.getroot()
                        
                        # Szukamy wszystkich elementów typu path
                        # W XML-ach Corela często są w tagach <path> lub mają atrybut 'd'
                        for elem in root.iter():
                            # Pomijamy teksty, szukamy ścieżek
                            if 'path' in elem.tag.lower() or 'd' in elem.attrib:
                                path_data = elem.attrib.get('d', '')
                                if path_data:
                                    all_paths.append({
                                        "d": path_data,
                                        "fill": elem.attrib.get('fill', 'none'),
                                        "stroke": elem.attrib.get('stroke', '#000000')
                                    })
                    except:
                        continue # Ignorujemy pliki, które nie są poprawnym XML-em

            os.remove(temp_path)

            # Generujemy "szkielet" SVG
            svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000">
  <g id="Szkielet_Geometrii">
'''
            for p in all_paths:
                svg_content += f'    <path d="{p["d"]}" fill="{p["fill"]}" stroke="{p["stroke"]}" stroke-width="1" />\n'

            svg_content += '''  </g>\n</svg>'''

            mem = io.BytesIO()
            mem.write(svg_content.encode('utf-8'))
            mem.seek(0)

            return send_file(
                mem, 
                as_attachment=True, 
                download_name="BlackSpark_Szkielet.svg", 
                mimetype='image/svg+xml'
            )

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Błąd: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
