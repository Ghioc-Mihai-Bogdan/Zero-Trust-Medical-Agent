import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/diagnose', methods=['POST'])
def diagnose():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url = "http://10.42.0.1:11434/api/generate"
        
        prompt_text = f"Patient Symptoms: {data.get('text', '')}\n\nProvide your top 3 differential diagnoses. For each, include a brief sentence explaining why the symptoms (and image, if provided) match."
        
        payload = {
            "model": "gemma4:31b", 
            "prompt": prompt_text, 
            "system": "You are a helpful and thorough clinical AI. Do not be overly strict with formatting, but ensure you clearly state the names of the conditions. If an image is provided, incorporate your visual findings into your clinical reasoning.", 
            "stream": False,
            "options": {
                "num_gpu": 99,
                "num_ctx": 8192
            }
        }
        
        # MULTIMODAL INJECTION: If the request contains images, pass them to Ollama
        if 'images' in data and isinstance(data['images'], list) and len(data['images']) > 0:
            payload['images'] = data['images']
            
        res = requests.post(url, json=payload, timeout=300).json().get('response', '')
        return jsonify({"diagnoses": res})
    except Exception as e:
        return jsonify({"diagnoses": f"[Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)