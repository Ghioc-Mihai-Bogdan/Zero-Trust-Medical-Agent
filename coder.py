import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

def ask_gemma(prompt, system_instruction):
    url = "http://10.42.0.1:11434/api/generate"
    payload = {
        "model": "gemma4:e4b", 
        "prompt": prompt, 
        "system": system_instruction, 
        "stream": False
    }
    try:
        return requests.post(url, json=payload, timeout=300).json().get('response', '')
    except Exception as e:
        return f"[Ollama Error: {str(e)}]"

@app.route('/code', methods=['POST'])
def code():
    try:
        data = request.get_json(force=True, silent=True) or {}

        system_instruction = """
        You are an expert medical coding AI. Map the clinical text to the most accurate ICD-10-CM codes. Be concise. 
        CRITICAL ESCAPE HATCH: If the text indicates a healthy patient, a routine check-up, or no active illness, DO NOT force disease codes. Instead, utilize appropriate preventative Z-codes (e.g., Z00.00 for general medical exam) and explicitly state that no pathological ICD-10 codes are warranted.
        """

        user_task = f"Extract primary ICD-10 codes from:\n{data.get('text', '')}"
        
        return jsonify({"icd10_codes": ask_gemma(user_task, system_instruction.strip())})
        
    except Exception as e:
        return jsonify({"icd10_codes": f"[Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)