import os
import json
import requests
import redis
import concurrent.futures
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# Initialize Redis
try:
    redis_client = redis.Redis(host='redis-service', port=6379, db=0, decode_responses=True)
except:
    redis_client = None

def ask_gemma_local(prompt, system_instruction):
    url = "http://10.42.0.1:11434/api/generate"
    payload = {"model": "gemma4:e4b", "prompt": prompt, "system": system_instruction, "stream": False}
    try:
        return requests.post(url, json=payload, timeout=300).json().get('response', '')
    except Exception as e:
        return f"[Local AI Error: {str(e)}]"

def safe_agent_call(url, payload, fallback_key):
    try:
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
def health_check():
    return jsonify({"status": "Orchestrator is online"}), 200

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
    # --- FIX 1: Safely handle both Angular's FormData and standard JSON ---
    if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
        try:
            data = request.get_json(force=True)
        except Exception as e:
            return jsonify({"error": f"Failed to parse JSON: {str(e)}"}), 400
    else:
        # Fallback to reading FormData (What Angular sends via chat.service.ts)
        data = request.form

    session_id = data.get('session_id', 'test-session')
    user_text = data.get('prompt', '')

    if not user_text:
        return jsonify({"error": "No prompt was provided."}), 400

    # --- AI NAMED ENTITY EXTRACTION ---
    name_prompt = f"Extract the doctor's name from this text. Format it as 'Dr. [Name]'. If no doctor is mentioned, reply EXACTLY with 'Dr. Validation'. Reply ONLY with the name and no other text.\n\nText: '{user_text}'"
    doctor_name = ask_gemma_local(name_prompt, "You are a strict data extraction bot.").strip()
    
    # Failsafe cleanup just in case the AI uses markdown
    doctor_name = doctor_name.replace("*", "").replace('"', '').split('\n')[0]
    # ----------------------------------

    history = []
    if redis_client:
        try:
            raw = redis_client.get(f"session:{session_id}")
            if raw: history = json.loads(raw)
        except: pass

    history.append({"role": "Attending Physician", "content": user_text})
    
    physician_notes = [msg['content'] for msg in history if msg['role'] == 'Attending Physician']
    clean_symptoms = "\n".join(physician_notes[-3:])

    try:
        intent = "CLINICAL" if "PATIENT" in user_text.upper() or "SYMPTOM" in user_text.upper() else "GENERAL"
        if intent == "GENERAL":
            intent_check = ask_gemma_local(f"Is this medical (CLINICAL) or normal chat (GENERAL)? Reply exactly one word.\nText: {user_text}", "You are a router.").strip().upper()
            if "CLINICAL" in intent_check: intent = "CLINICAL"

        if intent == "CLINICAL":
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                coder_future = executor.submit(safe_agent_call, "http://medical-coder:8080/code", {"text": clean_symptoms}, "icd10_codes")
                acuity_future = executor.submit(safe_agent_call, "http://acuity-analyzer:8080/analyze", {"text": clean_symptoms}, "acuity_level")
                diag_future = executor.submit(safe_agent_call, "http://diagnostician:8080/diagnose", {"text": clean_symptoms}, "diagnoses")
                ed_future = executor.submit(safe_agent_call, "http://patient-educator:8080/educate", {"text": clean_symptoms}, "patient_explanation")

                coder_res = coder_future.result()
                acuity_res = acuity_future.result()
                diag_res = diag_future.result()
                ed_res = ed_future.result()

            current_date = datetime.now().strftime("%B %d, %Y")
            
            synthesis_prompt = f"""
            You are a professional medical scribe. Output a highly detailed, comprehensive clinical report based on the provided data.
            
            CRITICAL INSTRUCTIONS:
            1. DO NOT include any AI safety disclaimers.
            2. Do not use any markdown formatting whatsoever (No asterisks). 
            3. Greet the attending physician: {doctor_name}
            4. Include today's date: {current_date}
            5. Write full, descriptive sentences for the Diagnoses and Patient Education sections. Do not just list terms; explain them thoroughly.

            DATA TO FORMAT:
            - Codes: {coder_res.get('icd10_codes', 'No codes provided')}
            - Acuity: {acuity_res.get('acuity_level', 'No acuity provided')}
            - Diagnoses: {diag_res.get('diagnoses', 'No diagnoses provided')}
            - Patient Ed: {ed_res.get('patient_explanation', 'No explanation provided')}
            """
            ai_text = ask_gemma_local(synthesis_prompt, "You are a highly detailed medical scribe. Do not converse.")
            ai_text = ai_text.replace("*", "").replace("#", "")

        else:
            chat_context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history[-4:]])
            ai_text = ask_gemma_local(f"Respond naturally and comprehensively to this text:\n\n{chat_context}", "You are a helpful and highly detailed assistant.")
        
        history.append({"role": "Clinical AI", "content": ai_text})
        if redis_client:
            try: redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400) 
            except: pass

        # --- FIX 2: Return 'natural_response' as Angular expects it ---
        return jsonify({"natural_response": ai_text})
        
    except Exception as e:
        # --- FIX 3: Return 'error' so Angular's catch block can read res.error ---
        return jsonify({"error": f"API failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)