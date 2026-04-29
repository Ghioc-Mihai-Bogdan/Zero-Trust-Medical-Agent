import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/diagnose', methods=['POST'])
def diagnose():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url = "http://10.42.0.1:11434/api/generate"
        payload = {
            "model": "gemma4:31b", 
            "prompt": f"Symptoms: {data.get('text', '')}\n\nList top 3 differential diagnoses.", 
            "system": "You are a strict diagnostic machine. Output exactly 3 diagnoses.", 
            "stream": False,
            "options": {
            "num_gpu": 99,
            "num_ctx": 8192
            }
        }
        res = requests.post(url, json=payload, timeout=300).json().get('response', '')
        return jsonify({"diagnoses": res})
    except Exception as e:
        return jsonify({"diagnoses": f"[Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
