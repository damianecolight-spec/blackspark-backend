from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/compare', methods=['POST'])
def compare_files():
    # Pobieramy dwa pliki: baza i projekt
    file1 = request.files['base'] # pusty.cdr
    file2 = request.files['project'] # kwadrat.cdr
    
    data1 = file1.read()
    data2 = file2.read()
    
    # Znajdujemy różnice
    diffs = []
    # Sprawdzamy tylko fragmenty, gdzie pliki się różnią
    min_len = min(len(data1), len(data2))
    for i in range(min_len):
        if data1[i] != data2[i]:
            diffs.append((i, data2[i]))
            if len(diffs) > 100: break # Zatrzymujemy się po znalezieniu pierwszych 100 zmian
            
    return jsonify({"roznice_hex": diffs})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
