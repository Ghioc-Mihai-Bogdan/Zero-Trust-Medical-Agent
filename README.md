# 🛡️ Zero-Trust Medical Agent

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Angular](https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)
![Istio](https://img.shields.io/badge/Istio-466BB0?style=for-the-badge&logo=istio&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)

A Secure, Multimodal Clinical AI Mesh designed for highly sensitive pediatric care environments (e.g., European Reference Networks). This project leverages a cloud-native microservice architecture with strict Zero-Trust security to provide powerful AI diagnostics without compromising patient data privacy.

## 🎥 Project Demo: EOSC Deployment & Instantiation

*(Watch the video above to see how we seamlessly provision the VM on the European Open Science Cloud and deploy the mesh!)*

---

## 🌟 Key Features

* **Zero-Trust Security (Istio & mTLS):** No pod trusts another by default. All internal mesh traffic is cryptographically authenticated and encrypted via Mutual TLS.
* **Multimodal Inference:** Uses `gemma4:31b` to analyze high-resolution medical imaging (X-rays) alongside clinical text.
* **Edge-Computed Payload Optimization:** Client-side HTML5 canvas intercepts and downscales massive 15MB+ DICOM/PNG images into lightweight ~150KB payloads, preventing network bottlenecking and 413 Payload errors.
* **"Escape Hatch" Safety Protocol:** Explicit system-level prompt engineering prevents forced AI hallucinations, seamlessly pivoting to preventative Z-codes and routine wellness reports for healthy patients.
* **Bare-Metal AI Engine:** AI inference runs directly on the Host VM via Ollama, bypassing Kubernetes virtualization overhead to maximize GPU/CPU thread utilization.

---

## 🏗️ Architecture & The AI Swarm

The system is built on **K3s (Lightweight Kubernetes)** and operates via a "Hub and Spoke" orchestrator pattern. 

1. **The Orchestrator (Python/Flask):** The central nervous system. Manages asynchronous parallelism (using `ThreadPoolExecutor`), stores session state in **Redis**, and synthesizes the final clinical report using `gemma4:31b`.
2. **Diagnostician (Stateless):** Multimodal agent for differential diagnoses.
3. **Medical Coder (Stateless):** Maps clinical text to ICD-10 and Z-codes using the lightning-fast `gemma4:e4b` model.
4. **Acuity Analyzer (Stateful):** Reads historical session state from Redis to assign an accurate Emergency Severity Index (ESI) Level (1-5).
5. **Patient Educator (Stateless):** Translates complex jargon into a 6th-grade reading level.

---

## 🚀 Quick Start / Deployment Guide

These instructions assume a fresh Ubuntu VM (e.g., on EOSC, Azure, or WSL) and will build the infrastructure from scratch.

### 1. Prerequisites & Host Setup
```bash
# Update OS and install prerequisites
sudo apt update && sudo apt upgrade -y
sudo apt install docker.io git curl unzip -y
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

 ```
##Demo on EOSC
[![EOSC VM Instantiation Demo](https://youtu.be/sYSketeMuwE/maxresdefault.jpg)](https://youtu.be/sYSketeMuwE)





