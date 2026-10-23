# Campus Knowledge Assistant using RAG 🎓

A Retrieval-Augmented Generation (RAG) assistant specifically designed to help students, faculty, and visitors query campus notices, handbooks, syllabi, timetables, and academic policies with verified page citations.

---

## 🌟 Key Features

- 📑 **PDF Extraction with OCR Fallback**: Automatically extracts digital PDF text, falling back to Tesseract OCR for scanned physical circulars and notices.
- 🧩 **Structure-Aware Chunking**: Intelligently chunks text by paragraphs and sentences, carrying overlapping context windows to preserve semantic meaning.
- 🛡️ **Document Fingerprinting & Deduplication**: Computes SHA-256 fingerprints to automatically supersede outdated revisions when revised campus notices are uploaded.
- ⚡ **Hybrid Retrieval (70% Semantic + 30% Keyword)**: Combines dense vector search (`all-MiniLM-L6-v2` via ChromaDB) with keyword matching to ensure accurate retrieval of both concepts and exact course codes/names.
- 🤖 **Grounded Gemini Answers**: Synthesizes verified answers with explicit source file and page citations using `gemini-2.5-flash` / `gemini-3.8-flash` with built-in retry handling.

---

## 📁 Repository Architecture

```
campusknowledgeassistantusingrag/
├── data/
│   └── chroma_db/            # Local persistent Chroma vector database
├── src/
│   ├── config.py             # App configurations, model hyperparameters, weights
│   ├── extractor.py          # PyMuPDF text & Tesseract OCR fallback extractor
│   ├── chunker.py            # Structure-aware paragraph/sentence chunker
│   ├── embeddings.py         # Sentence-transformers embedding wrapper
│   ├── vector_db.py          # ChromaDB interface with versioning & deduplication
│   ├── retriever.py          # 70/30 Hybrid retrieval engine
│   ├── generator.py          # Grounded Gemini prompt assembly & retry logic
│   ├── assistant.py          # CampusKnowledgeAssistant coordinator API
│   └── cli.py                # Command-line interface for ingesting & querying
├── Minor_RAG.ipynb           # Original Google Colab research notebook
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md
```

---

## 🚀 Getting Started

### 1. Environment Setup

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create `.env` from the template:

```powershell
Copy-Item .env.example .env
```

Open `.env` and insert your Gemini API Key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Ingest Campus PDFs

Add notices, academic calendars, or syllabi into the database:

```powershell
python -m src.cli ingest path/to/campus_notice.pdf
```

Or ingest an entire folder of PDFs:
```powershell
python -m src.cli ingest path/to/pdf_folder/
```

Check database stats:
```powershell
python -m src.cli stats
```

### 4. Query the Assistant

Ask any question about your campus documents:

```powershell
python -m src.cli query "What is the attendance criteria for midterm exams?"
```

---

## 🎨 Next Step: User Interface
The core RAG engine is exposed as a clean Python API in `src.assistant.CampusKnowledgeAssistant`, ready to be connected to a modern Web UI (Streamlit, React, or FastAPI).
