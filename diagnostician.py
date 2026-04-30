import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/diagnose', methods=['POST'])
def diagnose():
    try:
        data = request.get_json(force=True, silent=True) or {}
        url = "http://10.42.0.1:11434/api/generate"

        system_instruction = """
        You are a thorough clinical diagnostic AI. Evaluate the patient's symptoms and visual data (if provided). 
        If the clinical picture suggests an illness, provide your top 3 differential diagnoses with brief reasoning. 
        
        CRITICAL ESCAPE HATCH: If the patient presents with no symptoms, is perfectly healthy, or is seeking routine reassurance, DO NOT fabricate a disease. Instead, explicitly state 'No active pathology identified' or 'Routine wellness presentation' and explain why the presentation is benign.
        """
        
        patient_text = data.get('text', '')
        user_task = f"Patient Symptoms: {patient_text}\n\nProvide your top 3 differential diagnoses. For each, include a brief sentence explaining why the symptoms (and image, if provided) match."
        
        payload = {
            "model": "gemma4:31b", 
            "system": system_instruction.strip(),
            "prompt": user_task, 
            "stream": False,
            "options": {
                "num_gpu": 99,
                "num_ctx": 8192
            }
        }
        
        if 'images' in data and isinstance(data['images'], list) and len(data['images']) > 0:
            payload['images'] = data['images']
            
        res = requests.post(url, json=payload, timeout=300).json().get('response', '')
        return jsonify({"diagnoses": res})
        
    except Exception as e:
        return jsonify({"diagnoses": f"[Crash: {str(e)}]"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)