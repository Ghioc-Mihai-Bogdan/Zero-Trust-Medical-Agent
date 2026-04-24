import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/educate', methods=['POST'])
def educate():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url = "http://10.42.0.1:11434/api/generate"
        prompt_text = f"Write exactly ONE short, natural conversational paragraph explaining this to the patient. DO NOT use lists or bullet points.\nHistory:\n{data.get('text', '')}"
        payload = {"model": "gemma4:e4b", "prompt": prompt_text, "system": "You are an empathetic Patient Educator.", "stream": False}
        res = requests.post(url, json=payload, timeout=300).json().get('response', '')
        return jsonify({"patient_explanation": res})
    except Exception as e:
        return jsonify({"patient_explanation": f"[Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
