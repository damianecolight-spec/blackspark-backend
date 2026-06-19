from flask import Flask, request, jsonify, send_file
import zipfile
import os
import struct
import io

app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parse_full_geometry():
    file = request.files['file']
    temp_path = "full_layout.cdr"
    file.save(temp_path)

    try:
        with zipfile.ZipFile(temp_path, 'r') as archive:
            dat_file = 'content/data/page1.dat'
            if dat_file not in archive.namelist():
                return jsonify({"error": "Brak pliku danych"}), 400
            
            with archive.open(dat_file) as f:
                data = f.read()
                
            # SZUKAMY WZORCA: 
            # Binarne dane Corela to często pary floatów (X, Y)
            # Przeskakujemy bajty i próbujemy odczytać grupy po 8 bajtów (2x 32-bit float)
            points = []
            for i in range(0, len(data) - 8, 4):
                try:
                    # Rozpakowujemy 4 bajty jako float
                    val = struct.unpack('<f', data[i:i+4])[0]
                    # Filtrujemy dane - szukamy liczb w zakresie współrzędnych opakowania (np. 0-2000)
                    if 0 < val < 2000:
                        points.append(val)
                except:
                    continue
            
            # Generujemy SVG z odzyskanych punktów jako ścieżka
            svg_content = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">'
            svg_content += '<path d="M '
            for i in range(0, len(points)-1, 2):
                svg_content += f"{points[i]} {points[i+1]} L "
            svg_content += 'Z" fill="none" stroke="black" stroke-width="2"/>'
            svg_content += '</svg>'
            
            os.remove(temp_path)
            
            mem = io.BytesIO(svg_content.encode('utf-8'))
            mem.seek(0)
            return send_file(mem, as_attachment=True, download_name="BlackSpark_Full.svg", mimetype='image/svg+xml')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
