# ⚖️ Legal NER Project – AI Powered Legal Document Entity Extraction

## 📌 Overview

The Legal NER (Named Entity Recognition) Project is an AI-powered web application designed to extract and classify important entities from legal documents such as court cases, judgments, contracts, and legal notices.

The system uses **Python, FastAPI, spaCy, NLP, and Docker** to process uploaded documents and identify entities like:

* Person Names
* Courts
* Dates
* Legal Sections
* Organizations
* Locations
* Monetary Values

This project helps automate legal document analysis, reducing manual effort and improving document understanding.

---

# 🚀 Features

✅ Upload and process legal documents
✅ Extract entities using NLP-based Named Entity Recognition
✅ Supports PDF document processing using PyMuPDF
✅ FastAPI backend for high-performance APIs
✅ Interactive frontend for uploading and viewing results
✅ Docker support for easy deployment
✅ Entity filtering and structured JSON response
✅ Automatic legal entity annotation support for training datasets

---

# 🛠️ Tech Stack

## Backend

* Python
* FastAPI
* spaCy NLP
* PyMuPDF
* SQLite

## Frontend

* HTML
* CSS
* JavaScript

## Deployment & Tools

* Docker
* Docker Compose

---

# 📂 Project Structure

```bash
legal-ner-project/
│
├── backend/
│   ├── app.py
│   ├── inference.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── index.html
│   ├── script.js
│   ├── styles.css
│   └── Dockerfile
│
├── training/
│   ├── train_spacy.py
│   └── convert_doccano.py
│
├── docker-compose.yml
└── requirements.txt
```

---

# ⚙️ Installation & Setup

## 1️⃣ Clone Repository

```bash
git clone <repository-url>
cd legal-ner-project
```

---

## 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

#### Windows

```bash
venv\Scripts\activate
```

#### Linux/Mac

```bash
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

---

# ▶️ Running the Project

## Start Backend Server

```bash
cd backend
uvicorn app:app --reload
```

Backend runs on:

```bash
http://127.0.0.1:8000
```

---

## Run Frontend

Open `frontend/index.html` in browser.

Or use Live Server extension in VS Code.

---

# 🐳 Docker Setup

## Run Using Docker Compose

```bash
docker-compose up --build
```

---

# 📊 Example Output

## Input

```text
On 18 September 1982, the Supreme Court fined Mr. Sharma ₹5,00,000 in Delhi under Section 302.
```

## Extracted Entities

```json
[
  {
    "text": "18 September 1982",
    "label": "DATE"
  },
  {
    "text": "Supreme Court",
    "label": "ORG"
  },
  {
    "text": "Mr. Sharma",
    "label": "PERSON"
  },
  {
    "text": "Delhi",
    "label": "GPE"
  }
]
```

---

# 🧠 Model Training

The project also includes scripts for custom legal NER training.

## Train spaCy Model

```bash
cd training
python train_spacy.py
```

## Features of Training Module

* Automatic legal entity annotation
* PDF text extraction
* Dataset conversion support
* Custom entity labeling

---

# 📌 API Endpoints

## Upload & Process Document

```http
POST /upload
```

## Health Check

```http
GET /health
```

---

# 🎯 Use Cases

* Legal Document Analysis
* Court Judgment Processing
* Contract Intelligence
* Legal Research Automation
* Compliance Monitoring
* AI-based Document Understanding

---

# 🔮 Future Improvements

* Support for DOCX and image OCR
* Fine-tuned transformer-based legal NER model
* Multi-language legal document support
* Advanced analytics dashboard
* Role-based authentication
* Cloud deployment support

---


