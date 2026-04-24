import requests
import random
import time
from datasets import load_dataset
from tqdm import tqdm

DATASET_NAME = "gretelai/symptom_to_diagnosis"
API_URL = "http://127.0.0.1:8088/diagnose"

print(f"Loading dataset: {DATASET_NAME}...")
dataset = load_dataset(DATASET_NAME, split="train")

total_rows = len(dataset)
sample_size = int(total_rows * 0.10)
print(f"Total cases: {total_rows}. Selecting a random 10% ({sample_size} cases) for testing...")

dataset = dataset.shuffle(seed=42).select(range(sample_size))

correct_diagnoses = 0
failed_cases = []

print("\nStarting automated baseline test against Diagnostician (Gemma 4:e4b)...\n")

for row in tqdm(dataset, desc="Evaluating"):
    symptoms = row['input_text']
    true_diagnosis = row['output_text'].lower()
    
    # 1. Update payload specifically for the Diagnostician agent
    payload = {
        "text": symptoms
    }
    
    try:
        # 2. Use json=payload to ensure correct header parsing, lowered timeout to 120s
        response = requests.post(API_URL, json=payload, timeout=120)
        
        # 3. Extract the 'diagnoses' key returned by the agent
        result_text = response.json().get('diagnoses', '').lower()
        
        if true_diagnosis in result_text:
            correct_diagnoses += 1
        else:
            failed_cases.append({
                "symptoms": symptoms,
                "expected": true_diagnosis,
                "ai_output": result_text
            })
            
        # 2-second cooldown to protect Kubernetes from DDOS
        time.sleep(2)
        
    except Exception as e:
        print(f"\nAPI Error on case: {str(e)}")

accuracy = (correct_diagnoses / sample_size) * 100

print("\n" + "="*50)
print(" 📊 BASELINE EVALUATION REPORT (Pre-Fine-Tuning)")
print("="*50)
print(f"Model: Gemma 4:e4b (Zero-Shot Unit Test)")
print(f"Cases Evaluated: {sample_size}")
print(f"Successful Diagnoses: {correct_diagnoses}")
print(f"Missed Diagnoses: {len(failed_cases)}")
print(f"Accuracy Rate: {accuracy:.2f}%\n")

if len(failed_cases) > 0:
    print("❌ TOP 3 FAILED CASES FOR REVIEW:")
    for idx, fail in enumerate(failed_cases[:3]):
        print(f"\n[{idx+1}] Symptoms: {fail['symptoms'][:100]}...")
        print(f"   Expected: {fail['expected'].upper()}")
        print(f"   AI Output: {fail['ai_output'][:150].strip()}...")