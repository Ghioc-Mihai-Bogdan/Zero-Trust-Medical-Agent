import requests
import json
import time
import os
from datasets import load_dataset
from tqdm import tqdm

DATASET_NAME = "gretelai/symptom_to_diagnosis"
API_URL = "http://127.0.0.1:8088/diagnose"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
JUDGE_MODEL = "gemma4:31b"
SAVE_FILE = "test_results_raw.json"

def evaluate_with_31b(expected, ai_output):
    """Uses the 31B model to read the verbose notes and check for the correct diagnosis."""
    if not ai_output or "[crash" in ai_output.lower():
        return False
    
    judge_prompt = f"""
    You are an expert Chief of Medicine grading a medical resident's notes.
    
    EXPECTED TRUE DIAGNOSIS: {expected}
    RESIDENT'S CLINICAL NOTES: {ai_output}
    
    Did the resident successfully identify the expected true diagnosis (or a perfectly valid clinical synonym) somewhere within their notes?
    Respond STRICTLY with the word YES or NO. Do not explain.
    """
    
    payload = {
        "model": JUDGE_MODEL,
        "prompt": judge_prompt,
        "stream": False,
        "options": {
            "temperature": 0.0, # Zero creativity, strictly grading
            "num_ctx": 8192
        }
    }
    
    try:
        res = requests.post(OLLAMA_URL, json=payload, timeout=120).json()
        verdict = res.get('response', '').strip().upper()
        return "YES" in verdict
    except Exception as e:
        print(f" [Judge Error: {e}] ", end="")
        return False

# ==========================================
# SETUP
# ==========================================
print(f"Loading dataset: {DATASET_NAME}...")
dataset = load_dataset(DATASET_NAME, split="train")

sample_size = int(len(dataset) * 0.10)
print(f"Selecting a random 10% ({sample_size} cases) for testing...")
dataset = dataset.shuffle(seed=42).select(range(sample_size))

# ==========================================
# PHASE 1: GENERATION & STORAGE
# ==========================================
print("\n=== PHASE 1: Collecting Diagnostician Answers ===")
collected_data = []

for row in tqdm(dataset, desc="Generating Notes"):
    symptoms = row['input_text']
    true_diagnosis = row['output_text'].lower()
    
    try:
        response = requests.post(API_URL, json={"text": symptoms}, timeout=120)
        ai_output = response.json().get('diagnoses', '')
        
        collected_data.append({
            "symptoms": symptoms,
            "expected": true_diagnosis,
            "ai_output": ai_output
        })
        time.sleep(1) # Protect Kubernetes from DDOS
    except Exception as e:
        print(f"API Error on case: {str(e)}")

# Save to disk just in case!
with open(SAVE_FILE, "w") as f:
    json.dump(collected_data, f, indent=4)
print(f"Saved {len(collected_data)} raw cases to {SAVE_FILE}.")

# ==========================================
# PHASE 2: 31B GRADING
# ==========================================
print("\n=== PHASE 2: 31B Model Grading ===")
correct = 0
failed_cases = []
successful_cases = []

for item in tqdm(collected_data, desc="Grading Notes"):
    if evaluate_with_31b(item["expected"], item["ai_output"]):
        correct += 1
        successful_cases.append(item)
    else:
        failed_cases.append(item)

accuracy = (correct / len(collected_data)) * 100

# ==========================================
# RESULTS
# ==========================================
print("\n" + "="*50)
print(" 📊 FINAL EVALUATION REPORT (31B Graded)")
print("="*50)
print(f"Tested Model: Gemma 4:31b (Verbose Notes)")
print(f"Judge Model:  Gemma 4:31b (Zero Temp)")
print(f"Cases Eval'd: {len(collected_data)}")
print(f"Successful:   {correct}")
print(f"Missed:       {len(failed_cases)}")
print(f"Accuracy:     {accuracy:.2f}%\n")

if len(successful_cases) > 0:
    print("✅ TOP 3 SUCCESSFUL CASES FOR REVIEW:")
    for idx, success in enumerate(successful_cases[:3]):
        print(f"\n[{idx+1}] Symptoms: {success['symptoms'][:100]}...")
        print(f"   Expected: {success['expected'].upper()}")
        print(f"   AI Output: {success['ai_output'][:200].strip()}...")
        
    print("\n" + "-"*50 + "\n")

if len(failed_cases) > 0:
    print("❌ TOP 3 FAILED CASES FOR REVIEW:")
    for idx, fail in enumerate(failed_cases[:3]):
        print(f"\n[{idx+1}] Symptoms: {fail['symptoms'][:100]}...")
        print(f"   Expected: {fail['expected'].upper()}")
        print(f"   AI Output: {fail['ai_output'][:200].strip()}...")