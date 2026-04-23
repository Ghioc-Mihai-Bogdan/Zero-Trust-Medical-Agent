import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

def ask_gemma(prompt, system_instruction):
    url = "http://10.42.0.1:11434/api/generate"
    payload = {"model": "gemma4:e4b", "prompt": prompt, "system": system_instruction, "stream": False}
    try:
        return requests.post(url, json=payload, timeout=300).json().get('response', '')
    except Exception as e:
        return f"[Ollama Error: {str(e)}]"

@app.route('/diagnose', methods=['POST'])
def diagnose():
    try:
        data = request.get_json(force=True, silent=True) or {}
        return jsonify({"diagnoses": ask_gemma(f"Symptoms: {data.get('text', '')}\n\nList top 3 differential diagnoses.", "You are a strict diagnostic machine. Output exactly 3 diagnoses.")})
    except Exception as e:
        return jsonify({"diagnoses": f"[Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
