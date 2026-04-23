import os
import json
import requests
import redis
import concurrent.futures
from flask import Flask, request, jsonify

app = Flask(__name__)

# Connect to Redis
try:
    redis_client = redis.Redis(host='redis-service', port=6379, db=0, decode_responses=True)
except Exception as e:
    redis_client = None

def ask_gemma_local(prompt, system_instruction):
    url = "http://10.42.0.1:11434/api/generate"
    payload = {"model": "gemma4:e4b", "prompt": prompt, "system": system_instruction, "stream": False}
    try:
        res = requests.post(url, json=payload, timeout=300)
        return res.json().get('response', '')
    except Exception as e:
        return f"[Local AI Error: {str(e)}]"

def safe_agent_call(url, payload, fallback_key):
    try:
        # Try both port 8080 and port 80 routing depending on cluster config
        try_urls = [url, url.replace(":8080", "")] 
        last_error = "Unknown Error"
        
        for u in try_urls:
            try:
                response = requests.post(u, json=payload, timeout=300)
                if response.ok:
                    return response.json()
                last_error = f"HTTP {response.status_code}"
            except Exception:
                continue
                
        return {fallback_key: f"[Agent Offline: {last_error}]"}
    except Exception as e:
        return {fallback_key: f"[Connection failed: {str(e)}]"}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "Orchestrator is online"})

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = request.args.get('session_id')
    try:
        if redis_client:
            raw = redis_client.get(f"session:{session_id}")
            if raw: return jsonify({"history": json.loads(raw)})
    except: pass
    return jsonify({"history": []})

@app.route('/api/process', methods=['POST'])
def process():
    session_id = request.form.get('session_id')
    user_text = request.form.get('prompt', '')
    doctor_name = request.form.get('doctor_name', 'Attending Physician')

    history = []
    if redis_client:
        try:
            raw = redis_client.get(f"session:{session_id}")
            if raw: history = json.loads(raw)
        except: pass

    history.append({"role": "Attending Physician", "content": user_text})
    
    transcript = ""
    for msg in history[-4:]:
        transcript += f"\n{msg['role']}: {msg['content']}"

    try:
        # 1. Routing
        intent = ask_gemma_local(f"Analyze this text: '{user_text}'. Is it a CLINICAL note or GENERAL chat? Reply exactly one word: CLINICAL or GENERAL.", "You are a routing bot.").strip().upper()

        if "CLINICAL" in intent:
            # 2. Parallel Swarm Execution
            with concurrent.futures.ThreadPoolExecutor() as executor:
                coder_future = executor.submit(safe_agent_call, "http://medical-coder:8080/code", {"text": transcript}, "icd10_codes")
                acuity_future = executor.submit(safe_agent_call, "http://acuity-analyzer:8080/analyze", {"text": transcript}, "acuity_level")
                diag_future = executor.submit(safe_agent_call, "http://diagnostician:8080/diagnose", {"text": transcript}, "diagnoses")
                ed_future = executor.submit(safe_agent_call, "http://patient-educator:8080/educate", {"text": transcript}, "patient_explanation")

                coder_res = coder_future.result()
                acuity_res = acuity_future.result()
                diag_res = diag_future.result()
                ed_res = ed_future.result()

            # 3. Final Synthesis (Strict Anti-Refusal)
            synthesis_prompt = f"""
            You are a medical scribe. Your ONLY job is to format the following data into a final report. Do NOT ask for more data. Do NOT say you are waiting for data.

            DATA RECEIVED:
            - Codes: {coder_res.get('icd10_codes', 'No codes provided')}
            - Acuity: {acuity_res.get('acuity_level', 'No acuity provided')}
            - Diagnoses: {diag_res.get('diagnoses', 'No diagnoses provided')}
            - Patient Ed: {ed_res.get('patient_explanation', 'No explanation provided')}
            
            OUTPUT THE FINAL REPORT NOW:
            """
            ai_text = ask_gemma_local(synthesis_prompt, "You are a strict data formatter. Do not converse.")
        else:
            ai_text = ask_gemma_local(f"Respond politely and naturally to this text. Do not diagnose.\n\n{transcript}", "You are a helpful AI assistant.")
        
        history.append({"role": "Clinical AI", "content": ai_text})
        if redis_client:
            try: redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400) 
            except: pass

        return jsonify({"natural_response": ai_text})
        
    except Exception as e:
        return jsonify({"error": f"API failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)