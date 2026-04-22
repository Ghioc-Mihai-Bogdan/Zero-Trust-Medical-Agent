import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

def ask_gemma(prompt, system_instruction):
    url = "http://10.42.0.1:11434/api/generate"
    payload = {"model": "gemma2:2b", "prompt": prompt, "system": system_instruction, "stream": False}
    try:
        return requests.post(url, json=payload, timeout=60).json().get('response', '')
    except Exception as e:
        return f"[Ollama Error: {str(e)}]"

@app.route('/code', methods=['POST'])
def code():
    try:
        data = request.get_json(force=True, silent=True) or {}
        transcript = data.get('text', '')
        sys_prompt = "You are an expert Medical Coder. Be extremely concise."
        task = f"Extract only the primary ICD-10 codes from this history:\n{transcript}"
        return jsonify({"icd10_codes": ask_gemma(task, sys_prompt)})
    except Exception as e:
        return jsonify({"icd10_codes": f"[Flask Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
