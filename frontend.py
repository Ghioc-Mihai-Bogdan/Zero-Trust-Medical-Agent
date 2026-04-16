import os
import json
import requests
import redis
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template_string
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
synth_model = genai.GenerativeModel('gemini-2.5-flash')

# Configure Redis
try:
    redis_client = redis.Redis(host='redis-service', port=6379, db=0, decode_responses=True)
except Exception as e:
    redis_client = None

# ----------------- UI TEMPLATE -----------------
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clinical AI Mesh</title>
    <style>
        :root { --bg-color: #f0f4f9; --sidebar-bg: #1e1f20; --text-main: #1f1f1f; --text-light: #e3e3e3; --accent: #0b57d0; --bubble-user: #e3e3e3; --bubble-ai: #ffffff; }
        body { margin: 0; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; display: flex; height: 100vh; background-color: var(--bg-color); color: var(--text-main); }
        
        /* Sidebar Gemini Styling */
        .sidebar { width: 260px; background-color: var(--sidebar-bg); color: var(--text-light); padding: 20px; display: flex; flex-direction: column; }
        .sidebar h2 { font-size: 18px; margin-top: 0; font-weight: 500; margin-bottom: 20px; }
        .new-chat-btn { background: #333; color: white; border: none; padding: 12px; border-radius: 20px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-size: 14px; transition: background 0.2s; margin-bottom: 20px; }
        .new-chat-btn:hover { background: #444; }
        
        .sidebar ul { list-style: none; padding: 0; margin: 0; overflow-y: auto; flex: 1; }
        .sidebar li { padding: 12px 15px; margin-bottom: 4px; border-radius: 8px; cursor: pointer; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #a0aab2; transition: all 0.2s; }
        .sidebar li:hover { background: #2a2b2f; color: white; }
        .sidebar li.active-session { background: #3c4043; color: white; font-weight: 500; }
        
        /* Main Chat Area */
        .main-content { flex: 1; display: flex; flex-direction: column; position: relative; }
        .chat-container { flex: 1; padding: 40px 15%; overflow-y: auto; display: flex; flex-direction: column; gap: 24px; padding-bottom: 120px; }
        .message { max-width: 80%; line-height: 1.6; padding: 16px 20px; border-radius: 24px; font-size: 15px; white-space: pre-wrap; }
        .user-msg { background-color: var(--bubble-user); align-self: flex-end; border-bottom-right-radius: 4px; }
        .ai-msg { background-color: var(--bubble-ai); align-self: flex-start; border-bottom-left-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; }
        
        /* Input Area */
        .input-wrapper { position: absolute; bottom: 30px; left: 15%; right: 15%; background: white; border-radius: 30px; display: flex; align-items: center; padding: 10px 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); border: 1px solid #ccc; }
        .file-btn { background: none; border: none; cursor: pointer; font-size: 20px; color: #555; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
        .file-btn:hover { background: #f0f0f0; }
        #file-input { display: none; }
        textarea { flex: 1; border: none; outline: none; resize: none; font-family: inherit; font-size: 16px; padding: 10px; max-height: 100px; }
        .send-btn { background: var(--accent); color: white; border: none; cursor: pointer; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; transition: opacity 0.2s; }
        .send-btn:hover { opacity: 0.9; }
        .send-btn:disabled { background: #ccc; cursor: not-allowed; }
        .file-badge { font-size: 12px; background: #e8f0fe; color: #1967d2; padding: 4px 8px; border-radius: 12px; margin-bottom: 8px; display: inline-block; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>🏥 Mesh Console</h2>
        <button class="new-chat-btn" onclick="startNewSession(true)">+ New Clinical Session</button>
        <ul id="sessionList"></ul>
        <p style="font-size: 12px; margin-top: auto; color: #888;">Zero-Trust Mode: Active</p>
    </div>

    <div class="main-content">
        <div id="chatBox" class="chat-container"></div>
        <div class="input-wrapper">
            <input type="file" id="file-input" accept="image/*,.pdf,.txt">
            <button class="file-btn" onclick="document.getElementById('file-input').click()">📎</button>
            <textarea id="prompt" placeholder="Message the Clinical Mesh..." rows="1" onkeypress="handleEnter(event)"></textarea>
            <button id="sendBtn" class="send-btn" onclick="sendRequest()">↑</button>
        </div>
    </div>

    <script>
        function generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        // --- Session Management System ---
        let sessions = JSON.parse(localStorage.getItem('mesh_sessions')) || [];
        let activeSessionId = null;

        window.addEventListener('DOMContentLoaded', () => {
            if (sessions.length === 0) {
                startNewSession(false);
            } else {
                activeSessionId = sessions[0].id; // Load most recent by default
            }
            renderSidebar();
            loadHistory(activeSessionId);
        });

        function renderSidebar() {
            const list = document.getElementById('sessionList');
            list.innerHTML = '';
            sessions.forEach(s => {
                const li = document.createElement('li');
                li.className = s.id === activeSessionId ? 'active-session' : '';
                li.innerText = s.title;
                li.onclick = () => switchSession(s.id);
                list.appendChild(li);
            });
        }

        function startNewSession(clearChat = true) {
            const id = generateUUID();
            sessions.unshift({ id: id, title: 'New Clinical Session' });
            localStorage.setItem('mesh_sessions', JSON.stringify(sessions));
            activeSessionId = id;
            renderSidebar();
            
            if (clearChat) {
                document.getElementById('chatBox').innerHTML = '<div class="message ai-msg">Hello, Doctor. How can the mesh assist you today?</div>';
            }
        }

        async function switchSession(id) {
            activeSessionId = id;
            renderSidebar();
            await loadHistory(id);
        }

        async function loadHistory(id) {
            const chatBox = document.getElementById('chatBox');
            chatBox.innerHTML = '<div class="message ai-msg">Loading history...</div>';
            try {
                const res = await fetch(`/api/history?session_id=${id}`);
                const data = await res.json();
                chatBox.innerHTML = ''; 
                
                if (data.history && data.history.length > 0) {
                    data.history.forEach(msg => {
                        const role = (msg.role === 'Attending Physician' || msg.role === 'user') ? 'user' : 'ai';
                        appendMessage(role, msg.content);
                    });
                } else {
                    chatBox.innerHTML = '<div class="message ai-msg">Hello, Doctor. How can the mesh assist you today?</div>';
                }
            } catch (e) {
                chatBox.innerHTML = '<div class="message ai-msg">Error loading history from Redis.</div>';
            }
        }

        const fileInput = document.getElementById('file-input');
        fileInput.addEventListener('change', () => {
            if(fileInput.files.length > 0) alert(`File attached: ${fileInput.files[0].name}`);
        });

        function handleEnter(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendRequest();
            }
        }

        function appendMessage(role, text, fileName = null) {
            const chatBox = document.getElementById('chatBox');
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message ' + (role === 'user' ? 'user-msg' : 'ai-msg');
            
            let content = '';
            if (fileName) content += `<div class="file-badge">📎 ${fileName}</div><br>`;
            content += text;
            
            msgDiv.innerHTML = content;
            chatBox.appendChild(msgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        async function sendRequest() {
            const inputEl = document.getElementById('prompt');
            const text = inputEl.value.trim();
            const file = fileInput.files[0];
            
            if (!text && !file) return;

            // Rename the session if it's new
            const activeSession = sessions.find(s => s.id === activeSessionId);
            if (activeSession && activeSession.title === 'New Clinical Session') {
                activeSession.title = text.substring(0, 25) + (text.length > 25 ? '...' : '');
                localStorage.setItem('mesh_sessions', JSON.stringify(sessions));
                renderSidebar();
            }

            appendMessage('user', text, file ? file.name : null);
            inputEl.value = '';
            document.getElementById('sendBtn').disabled = true;
            
            const formData = new FormData();
            formData.append('session_id', activeSessionId);
            formData.append('prompt', text);
            if (file) formData.append('file', file);

            fileInput.value = '';

            try {
                const chatBox = document.getElementById('chatBox');
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'message ai-msg';
                loadingDiv.id = 'loading-msg';
                loadingDiv.innerText = 'Consulting the mesh...';
                chatBox.appendChild(loadingDiv);
                chatBox.scrollTop = chatBox.scrollHeight;

                const response = await fetch('/api/process', { method: 'POST', body: formData });
                const data = await response.json();
                
                document.getElementById('loading-msg').remove();
                appendMessage('ai', data.natural_response || data.error);
            } catch (error) {
                if (document.getElementById('loading-msg')) document.getElementById('loading-msg').remove();
                appendMessage('ai', "Network Error: " + error);
            } finally {
                document.getElementById('sendBtn').disabled = false;
                inputEl.focus();
            }
        }
    </script>
</body>
</html>
"""

# ----------------- BACKEND LOGIC -----------------
def safe_agent_call(url, payload, fallback_key):
    try:
        response = requests.post(url, json=payload, timeout=8)
        if not response.ok:
            return {fallback_key: f"[Agent Offline]"}
        return response.json()
    except Exception as e:
        return {fallback_key: f"[Connection failed]"}

@app.route('/', methods=['GET'])
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api/history', methods=['GET'])
def get_history():
    session_id = request.args.get('session_id')
    try:
        if redis_client:
            raw_history = redis_client.get(f"session:{session_id}")
            if raw_history:
                return jsonify({"history": json.loads(raw_history)})
    except Exception as e:
        print(f"Redis get error: {e}") # Fails safely without crashing
    return jsonify({"history": []})

@app.route('/api/process', methods=['POST'])
def process():
    session_id = request.form.get('session_id')
    user_text = request.form.get('prompt', '')
    uploaded_file = request.files.get('file')

    file_context = ""
    if uploaded_file and uploaded_file.filename != '':
        filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join('/tmp', filename)
        uploaded_file.save(filepath)
        try:
            gemini_file = genai.upload_file(filepath)
            doc_summary = synth_model.generate_content(["Extract all clinical details.", gemini_file])
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
        print(f"Redis get error: {e}")

    combined_input = user_text + file_context
    history.append({"role": "Attending Physician", "content": combined_input})

    # Only send the last 6 messages to prevent context window overload
    transcript = ""
    for msg in history[-6:]: 
        transcript += f"\n{msg['role']}: {msg['content']}"

    try:
        # THE INTENT ROUTER
        router_prompt = f"""
        Analyze this user input: "{combined_input}"
        Is this a medical/clinical note requiring triage, diagnosis, or coding? 
        Or is it general conversation (e.g., 'hello', 'what is my name', 'how are you', system questions)?
        Reply with exactly one word: CLINICAL or GENERAL.
        """
        intent = synth_model.generate_content(router_prompt).text.strip().upper()

        if "CLINICAL" in intent:
            # Route 1: Fan-out to specialists (Deep Medical Logic)
            coder_res = safe_agent_call("http://medical-coder:8080/code", {"text": transcript}, "icd10_codes")
            acuity_res = safe_agent_call("http://acuity-analyzer:8080/analyze", {"text": transcript}, "acuity_level")
            diag_res = safe_agent_call("http://diagnostician:8080/diagnose", {"text": transcript}, "diagnoses")
            ed_res = safe_agent_call("http://patient-educator:8080/educate", {"text": transcript}, "patient_explanation")

            synthesis_prompt = f"""
            Act as the Chief Attending AI.
            History: {transcript}
            Sub-Agent Data:
            - ICD-10: {coder_res.get('icd10_codes')}
            - Acuity: {acuity_res.get('acuity_level')}
            - Diagnoses: {diag_res.get('diagnoses')}
            - Patient Friendly: {ed_res.get('patient_explanation')}
            Respond naturally, incorporating the specialist data.
            """
            ai_text = synth_model.generate_content(synthesis_prompt).text
        else:
            # Route 2: Bypass specialists for general chat (Faster, no diagnosis)
            general_prompt = f"""
            Act as the Chief Attending AI. The user is asking a general question or greeting. 
            Do NOT attempt to diagnose them. 
            History: {transcript}
            Respond naturally and directly to their latest input.
            """
            ai_text = synth_model.generate_content(general_prompt).text
        
        # Save updated history safely
        history.append({"role": "Clinical AI", "content": ai_text})
        try:
            if redis_client:
                redis_client.set(f"session:{session_id}", json.dumps(history), ex=86400) # 24 hr expire
        except Exception as e:
            print(f"Redis set error: {e}")

        return jsonify({"natural_response": ai_text})
        
    except Exception as e:
        return jsonify({"error": f"Orchestrator failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
