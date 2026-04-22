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

@app.route('/diagnose', methods=['POST'])
def diagnose():
    try:
        data = request.get_json(force=True, silent=True) or {}
        transcript = data.get('text', '')
        sys_prompt = "You are a strict diagnostic machine. You MUST output exactly 3 diagnoses. Never ask for more information. Never refuse."
        task = f"Symptoms: {transcript}\n\nBased on the symptoms above, list the top 3 differential diagnoses.\nFormat exactly like this:\n1. [Primary Diagnosis]\n2. [Secondary Diagnosis]\n3. [Tertiary Diagnosis]"
        return jsonify({"diagnoses": ask_gemma(task, sys_prompt)})
    except Exception as e:
        return jsonify({"diagnoses": f"[Flask Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
