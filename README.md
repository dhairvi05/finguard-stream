<h1 align="center">🌀 Ledgify - Distributed Systems and GenAI Compliance Pipeline</h1>

A distributed, edge-native financial fraud monitoring pipeline that **ingests high-throughput transactions in real-time** and provides an **asynchronous, air-gapped forensic audit trail using localized GenAI**.

This project blends **high-performance backend infrastructure, advanced database design, and local retrieval-augmented generation (RAG)** to secure financial transactions against real-time threats.

---

## ✨ Features

* **High-Throughput Ingestion & Queuing**
  * Captures incoming transaction payloads instantly via Redis Streams using Consumer Groups
  * Decouples the primary API ingestion layer to maintain sub-second response times and prevent choking during traffic spikes

* **Polyglot Persistence Ledgering**
  * Enforces strict ACID compliance by committing transactional data to PostgreSQL
  * Uses database row-level locking to completely mitigate double-spending and race conditions
  * Offloads bloated metadata, system logs, and full JSON audit profiles into MongoDB for cold, scalable historical archiving

* **In-Memory Contextual RAG & Air-Gapped AI Auditing**
  * Queries historical transaction velocity profiles from PostgreSQL to build active user baselines on the fly
  * Injects specific user behavior metrics directly into a localized Ollama (Llama3) LLM context window
  * Generates instant forensic risk evaluation reports (Risk Rating, Threat Typology, Narrative Rationale) entirely within internal system memory—ensuring sensitive financial data never leaves localhost

---

## 🛠 Tech Stack

* Client (Monitoring Interface)  
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
  * Pandas

* Message Broker & Caching  
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)

* Server & AI Engine  
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![FastAPI](https://img.shields.io/badge/FastAPI-05998b?style=for-the-badge&logo=fastapi&logoColor=white)
![Ollama (Llama3)](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)

* Polyglot Databases  
![PostgreSQL](https://img.shields.io/badge/postgresql-%23336791.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-%234aa657.svg?style=for-the-badge&logo=mongodb&logoColor=white)

* Containerization  
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)

---

## 📌 Project Workflow

1. **Ingest:** Transaction payloads are written directly to the primary Redis Stream topic.
2. **Route:** Ingestion workers consume messages, committing entries below a $5,000 threshold straight to PostgreSQL as `SETTLED`.
3. **Flag:** Transactions exceeding threshold limits or failing geographical velocity rules are marked as `FLAGGED` and cloned onto a secondary compliance stream.
4. **Retrieve (RAG):** The AI worker fetches the user's last 10 transactions from PostgreSQL to build a localized context baseline.
5. **Audit:** The context window is fed to a local Ollama model to generate structured forensic audit profiles.
6. **Archive:** The final combined JSON analysis is permanently persisted in MongoDB and updated in real-time on the monitoring interface.

---

## 🛠 Project Setup

1. Clone the repository:
```bash
https://github.com/dhairvi05/ledgify.git
```

2. To start Docker:
```bash
docker compose up -d
```

3. To install Python deps:
```bash
pip install -r requirements.txt  
```

4. To start API server:
```bash
uvicorn backend.main:app --reload --port 8000
```

5. To start ingestion worker (terminal 2):
```bash
python workers/ingestion_worker.py
```

6. To start AI compliance worker (terminal 3) – requires Ollama + llama3:
```bash
python workers/compliance_ai_worker.py
```

7. To start stream generator (terminal 4):
```bash
python scripts/stream_generator.py
```

8. To launch dashboard (terminal 5):
```bash
streamlit run backend/dashboard.py
```

---

## 📱 Screenshots

* A glimpse at my project: 

<img src="assets/clean.png" width="600" />

<img src="assets/not-clean.png" width="600" />

<img src="assets/second-half.png" width="600">