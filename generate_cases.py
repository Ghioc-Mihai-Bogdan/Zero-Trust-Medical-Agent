import requests
import csv
import time
from datasets import load_dataset
from tqdm import tqdm

DATASET_NAME = "gretelai/symptom_to_diagnosis"
API_URL = "http://127.0.0.1:8088/diagnose"
SAVE_FILE = "medical_cases_output.csv"

# ==========================================
# SETUP
# ==========================================
print(f"Loading dataset: {DATASET_NAME}...")
dataset = load_dataset(DATASET_NAME, split="train")

sample_size = int(len(dataset) * 0.10)
print(f"Selecting a random 10% ({sample_size} cases) for testing...")
dataset = dataset.shuffle(seed=42).select(range(sample_size))

# ==========================================
# PHASE 1: GENERATION & STORAGE (CSV)
# ==========================================
print("\n=== PHASE 1: Collecting Diagnostician Answers ===")

# Open CSV file for writing
with open(SAVE_FILE, mode='w', newline='', encoding='utf-8') as file:
    # Define columns
    fieldnames = ["symptoms", "expected", "ai_output"]
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

    for row in tqdm(dataset, desc="Generating Notes"):
        symptoms = row['input_text']
        true_diagnosis = row['output_text'].lower()
        
        try:
            response = requests.post(API_URL, json={"text": symptoms}, timeout=120)
            ai_output = response.json().get('diagnoses', '')
            
            # Write immediately to CSV so data isn't lost if the script crashes
            writer.writerow({
                "symptoms": symptoms,
                "expected": true_diagnosis,
                "ai_output": ai_output
            })
            time.sleep(1)  # Protect Kubernetes from DDOS
        except Exception as e:
            print(f"API Error on case: {str(e)}")

print(f"\n✅ Generation complete! Saved cases to {SAVE_FILE}.")