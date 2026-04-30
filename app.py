import os
import json
import requests
import concurrent.futures
from flask import Flask, request, jsonify
import redis
from datetime import datetime

app = Flask(__name__)

# Redis Connection
redis_host = os.environ.get('REDIS_HOST', 'redis-service')
try:
    redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
except:
    redis_client = None

# Orchestrator configuration
def ask_gemma_local(prompt, system_instruction):
    url = "http://10.42.0.1:11434/api/generate"
    payload = {
        "model": "gemma4:31b",
        "prompt": prompt, 
        "system": system_instruction, 
        "stream": False,
        "keep_alive": "5m",
        "options": {
            "num_gpu": 99,
            "num_ctx": 8192
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=300)
        
        # Catch strict HTTP errors (e.g., 404 Model Not Found) before they break the JSON parser
        if response.status_code != 200:
            try:
                err_data = response.json()
                return f"[OLLAMA ENGINE ERROR - HTTP {response.status_code}]: {err_data.get('error', 'Unknown Error')}"
            except:
                return f"[OLLAMA RAW ERROR - HTTP {response.status_code}]: {response.text}"
                
        data = response.json()
        
        # Catch internal JSON errors
        if 'error' in data:
            return f"[OLLAMA INTERNAL ERROR]: {data['error']}"
            
        return data.get('response', '')
    except Exception as e:
        return f"[PYTHON REQUEST ERROR]: {str(e)}"

def safe_agent_call(url, json_data, fallback_key):
    try:
        res = requests.post(url, json=json_data, timeout=120)
        if res.status_code == 200:
            return res.json()
        return {fallback_key: f"Service Error: HTTP {res.status_code}"}
    except Exception as e:
        return {fallback_key: f"Service Offline: {str(e)}"}

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = request.args.get('session_id', 'test-session')
    if redis_client:
        try:
            raw = redis_client.get(f"session:{session_id}")
            if raw: return jsonify({"history": json.loads(raw)})
        except: pass
    return jsonify({"history": []})

@app.route('/api/process', methods=['POST'])
def process():
    if request.is_json or 'application/json' in request.headers.get('Content-Type', ''):
        try: data = request.get_json(force=True)
        except Exception as e: return jsonify({"error": f"Failed to parse JSON: {str(e)}"}), 400
    else:
        data = request.form

    session_id = data.get('session_id', 'test-session')
    original_prompt = data.get('prompt', '')
    user_text = original_prompt
    file_name = None
    file_content = None

    # --- NEW: Extract the Base64 image sent from Angular ---
    base64_image = data.get('base64_image')
    patient_images = [base64_image] if base64_image else []

    if 'file' in request.files:
        uploaded_file = request.files['file']
        if uploaded_file.filename != '':
            try:
                file_content = uploaded_file.read().decode('utf-8')
                file_name = uploaded_file.filename
                user_text += f"\n\n--- ATTACHED CLINICAL FILE: {file_name} ---\n{file_content}\n-------------------"
            except Exception as e:
                return jsonify({"error": f"Could not read the attached text file: {str(e)}"}), 400

    if not user_text.strip() and not patient_images: 
        return jsonify({"error": "No prompt or file data was provided."}), 400

    history = []
    if redis_client:
        try:
            raw = redis_client.get(f"session:{session_id}")
            if raw: history = json.loads(raw)
        except: pass

    all_user_text = "\n".join([msg.get('content', '') for msg in history if msg.get('role') == 'Attending Physician'])
    all_user_text += f"\n{user_text}"
    
    name_prompt = f"Extract the doctor's name from this text. Format it as 'Dr. [Name]'. If no doctor is mentioned, reply EXACTLY with 'Dr. Validation'. Reply ONLY with the name and no other text.\n\nText: '{all_user_text}'"
    doctor_name = ask_gemma_local(name_prompt, "You are a strict data extraction bot.").strip()
    doctor_name = doctor_name.replace("*", "").replace('"', '').split('\n')[0]

    is_first_message = len(history) == 0
    session_title = None

    if is_first_message:
        title_prompt = f"Write a 3-5 word clinical title for this patient case based on this text. Reply ONLY with the title, no quotes.\n\nText: {user_text}"
        session_title = ask_gemma_local(title_prompt, "You are a concise medical titler.").strip().replace('"', '').replace('*', '')

    history.append({
        "role": "Attending Physician", 
        "content": original_prompt,
        "file_name": file_name,
        "file_content": file_content
    })
    
    if redis_client:
        try: redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400) 
        except: pass
    
    physician_notes = []
    for msg in history:
        if msg['role'] == 'Attending Physician':
            text = msg.get('content', '')
            if msg.get('file_content'):
                text += f"\n\n--- ATTACHED CLINICAL FILE: {msg.get('file_name')} ---\n{msg.get('file_content')}\n-------------------"
            physician_notes.append(text)
            
    clean_symptoms = "\n".join(physician_notes[-3:])

    try:
        intent = "CLINICAL" if "PATIENT" in user_text.upper() or "SYMPTOM" in user_text.upper() else "GENERAL"
        if intent == "GENERAL":
            intent_check = ask_gemma_local(f"Is this medical (CLINICAL) or normal chat (GENERAL)? Reply exactly one word.\nText: {user_text}", "You are a router.").strip().upper()
            if "CLINICAL" in intent_check: intent = "CLINICAL"

        if intent == "CLINICAL":
            
            # --- NEW: Build the Multimodal Payload for the Diagnostician ---
            diag_payload = {"text": clean_symptoms}
            if patient_images:
                diag_payload["images"] = patient_images
                
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                coder_future = executor.submit(safe_agent_call, "http://medical-coder:8080/code", {"text": clean_symptoms}, "icd10_codes")
                acuity_future = executor.submit(safe_agent_call, "http://acuity-analyzer:8080/analyze", {"text": clean_symptoms}, "acuity_level")
                
                # --- Send to the Multimodal Diagnostician! ---
                diag_future = executor.submit(safe_agent_call, "http://diagnostician:8080/diagnose", diag_payload, "diagnoses")
                
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
            chat_context_lines = []
            for msg in history[-4:]:
                text = msg.get('content', '')
                if msg.get('file_content'): text += f"\n[File attached: {msg.get('file_name')}]\n{msg.get('file_content')}"
                chat_context_lines.append(f"{msg['role']}: {text}")
            chat_context = "\n".join(chat_context_lines)
            
            ai_text = ask_gemma_local(f"Respond naturally and comprehensively to this text:\n\n{chat_context}", "You are a helpful and highly detailed assistant.")
        
        history.append({"role": "Clinical AI", "content": ai_text})
        if redis_client:
            try: redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400) 
            except: pass

        return jsonify({"natural_response": ai_text, "session_title": session_title})
        
    except Exception as e:
        return jsonify({"error": f"API failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)