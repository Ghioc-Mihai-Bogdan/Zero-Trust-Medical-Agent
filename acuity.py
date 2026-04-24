import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url = "http://10.42.0.1:11434/api/generate"
        prompt_text = f"Based on this history, what is the Emergency Severity Index (ESI 1-5)? Give exactly one ESI level and a 1-sentence reason.\nHistory:\n{data.get('text', '')}"
        payload = {"model": "gemma4:e4b", "prompt": prompt_text, "system": "You are a precise Triage Nurse AI.", "stream": False}
        res = requests.post(url, json=payload, timeout=300).json().get('response', '')
        return jsonify({"acuity_level": res})
    except Exception as e:
        return jsonify({"acuity_level": f"[Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
