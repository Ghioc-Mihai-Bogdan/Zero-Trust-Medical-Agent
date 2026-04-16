import os
import json
import requests
import redis
import google.generativeai as genai
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure Gemini & Redis
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
synth_model = genai.GenerativeModel('gemini-2.5-flash')

try:
    redis_client = redis.Redis(host='redis-service', port=6379, db=0, decode_responses=True)
except Exception as e:
    redis_client = None

def safe_agent_call(url, payload, fallback_key):
    try:
        response = requests.post(url, json=payload, timeout=8)
        if not response.ok:
            return {fallback_key: f"[Agent Offline]"}
        return response.json()
    except Exception as e:
        return {fallback_key: f"[Connection failed]"}

# Health check for Kubernetes
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "API is online"})

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = request.args.get('session_id')
    try:
        if redis_client:
            raw_history = redis_client.get(f"session:{session_id}")
            if raw_history:
                return jsonify({"history": json.loads(raw_history)})
    except Exception as e:
        print(f"Redis error: {e}") 
    return jsonify({"history": []})

@app.route('/api/process', methods=['POST'])
def process():
    session_id = request.form.get('session_id')
    user_text = request.form.get('prompt', '')
    doctor_name = request.form.get('doctor_name', 'Attending Physician')
    uploaded_file = request.files.get('file')

    file_context = ""
    if uploaded_file and uploaded_file.filename != '':
        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join('/tmp', filename)
        uploaded_file.save(filepath)
        try:
            gemini_file = genai.upload_file(filepath)
            doc_summary = synth_model.generate_content(["Extract clinical details.", gemini_file])
            file_context = f"\n[Attached file '{filename}']: {doc_summary.text}"
        except Exception as e:
            file_context = f"\n[Failed to process file: {str(e)}]"

    history = []
    try:
        if redis_client:
            raw_history = redis_client.get(f"session:{session_id}")
            if raw_history:
                history = json.loads(raw_history)
    except Exception as e:
        pass

    combined_input = user_text + file_context
    history.append({"role": "Attending Physician", "content": combined_input})

    transcript = ""
    for msg in history[-6:]: 
        transcript += f"\n{msg['role']}: {msg['content']}"

    try:
        router_prompt = f"Analyze: '{combined_input}'. Is this CLINICAL or GENERAL? Reply one word."
        intent = synth_model.generate_content(router_prompt).text.strip().upper()

        if "CLINICAL" in intent:
            coder_res = safe_agent_call("http://medical-coder:8080/code", {"text": transcript}, "icd10_codes")
            acuity_res = safe_agent_call("http://acuity-analyzer:8080/analyze", {"text": transcript}, "acuity_level")
            diag_res = safe_agent_call("http://diagnostician:8080/diagnose", {"text": transcript}, "diagnoses")
            ed_res = safe_agent_call("http://patient-educator:8080/educate", {"text": transcript}, "patient_explanation")

            synthesis_prompt = f"""
            Act as Chief Attending AI assisting {doctor_name}.
            History: {transcript}
            Data: ICD-10: {coder_res.get('icd10_codes')}, Acuity: {acuity_res.get('acuity_level')}, Diag: {diag_res.get('diagnoses')}, Ed: {ed_res.get('patient_explanation')}
            Respond naturally.
            """
            ai_text = synth_model.generate_content(synthesis_prompt).text
        else:
            general_prompt = f"Act as Chief Attending AI assisting {doctor_name}. Do NOT diagnose. History: {transcript}. Respond directly."
            ai_text = synth_model.generate_content(general_prompt).text
        
        history.append({"role": "Clinical AI", "content": ai_text})
        try:
            if redis_client:
                redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400) 
        except Exception as e:
            pass

        return jsonify({"natural_response": ai_text})
    except Exception as e:
        history.append({"role": "Clinical AI", "content": ai_text})
        try:
            if redis_client:
                redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400) 
        except Exception as e:
            pass

        return jsonify({"natural_response": ai_text})
        
    except Exception as e:
        error_msg = str(e)
        # Catch the rate limit and return a natural response instead of a crash!
        if "429" in error_msg or "ResourceExhausted" in error_msg or "Quota" in error_msg:
            friendly_msg = f"Dr. {doctor_name}, the mesh is currently experiencing maximum capacity due to high traffic. Please give me about 60 seconds to process the backlog before submitting your next note."
            return jsonify({"natural_response": friendly_msg})
            
        return jsonify({"error": f"API failed: {error_msg}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
