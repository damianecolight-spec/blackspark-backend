from flask import Flask, request, jsonify
import zipfile
import os
import binascii

app = Flask(__name__)

@app.route('/parse', methods=['POST'])
def parse_binary():
    file = request.files['file']
    temp_path = "raw_data.cdr"
    file.save(temp_path)

    try:
        with zipfile.ZipFile(temp_path, 'r') as archive:
            # Szukamy głównych plików danych binarnych
            dat_file = 'content/data/page1.dat'
            if dat_file not in archive.namelist():
                return jsonify({"error": "Nie znaleziono pliku page1.dat"}), 400
            
            with archive.open(dat_file) as f:
                raw_bytes = f.read(500) # Czytamy pierwsze 500 bajtów dla testu
                hex_data = binascii.hexlify(raw_bytes).decode('utf-8')
            
            os.remove(temp_path)
            return jsonify({
                "hex_structure": hex_data[:200] + "...",
                "note": "Jeśli widzisz tu regularne wzorce, to są nasze współrzędne."
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
