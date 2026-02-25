# KeplerLab AI Notebook 🚀

> Transform educational materials into interactive learning experiences with AI-powered content generation, intelligent chat, and adaptive study tools.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.2.0-blue.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## ✨ Features

### 📚 Smart Material Management
- **Multi-format Support**: PDF, DOCX, PPTX, images, audio, video, web pages, YouTube
- **Automatic Processing**: Extract text, OCR images, transcribe audio/video
- **Organized Notebooks**: Group related materials by subject or topic

### 💬 Intelligent RAG Chat
- **Context-Aware Responses**: Ask questions about your uploaded materials
- **Multi-Source Queries**: Query across multiple documents simultaneously
- **Conversation Memory**: Maintains context throughout the chat session
- **Semantic Search**: Vector-based retrieval for accurate answers

### 🎨 AI Content Generation
- **Quizzes**: Auto-generated multiple-choice questions with varying difficulty
- **Flashcards**: Spaced-repetition ready cards for effective memorization
- **Podcasts**: Host-guest dialogue audio with synchronized transcripts

### ⚡ Advanced Capabilities
- **Background Processing**: Async material upload and processing
- **Multiple LLM Support**: Ollama, Google Gemini, NVIDIA AI, Custom APIs
- **Vector Search**: ChromaDB for fast semantic retrieval
- **Type-Safe Database**: PostgreSQL with Prisma ORM
- **Export Options**: Download audio files and more

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend                        │
│            (Vite + Tailwind CSS + Router)               │
└───────────────────┬─────────────────────────────────────┘
                    │ REST API
┌───────────────────▼─────────────────────────────────────┐
│                 FastAPI Backend                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Routes  │  Services  │  RAG  │  LLM  │  TTS    │  │
│  └──────────────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────────────┘
                    │
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│PostgreSQL│  │ ChromaDB │  │   File   │
│ (Prisma) │  │ (Vectors)│  │ Storage  │
└──────────┘  └──────────┘  └──────────┘
```

### Tech Stack

**Backend:**
- FastAPI 0.115.6 (Python 3.11+)
- PostgreSQL + Prisma ORM
- ChromaDB (vector database)
- LangChain (LLM orchestration)
- Sentence Transformers (embeddings)
- OpenAI Whisper (audio transcription)


**Frontend:**
- React 19.2.0
- React Router 7.11.0
- Tailwind CSS 3.4.19
- Vite 7.2.4

**Infrastructure:**
- Docker & Docker Compose
- Redis (caching)
- NGINX (web server)

---

## 🚀 Quick Start

### Prerequisites

```bash
# Required
Python 3.11+
Node.js 18+
PostgreSQL 15+
Docker (optional)

# Optional
LibreOffice (for slide image export)
Tesseract (for OCR)
```

### Installation

#### 1. Clone Repository
```bash
git clone <repository-url>
cd KeplerLab-AI-Notebook
```

#### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Setup database
prisma generate
prisma db push

# Create .env file
cp .env.example .env
# Edit .env and set:
#   - DATABASE_URL
#   - JWT_SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(64))")
#   - LLM_PROVIDER and API keys

# Run server
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

#### 4. Access Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) | Complete project overview, features, architecture |
| [ARCHITECTURE_FLOW.md](ARCHITECTURE_FLOW.md) | Detailed data flows, system diagrams, security |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | API reference, code examples, troubleshooting |

---

## 🎯 Usage Guide

### 1. Register & Login
```bash
# Navigate to http://localhost:5173/auth
# Create account or login
```

### 2. Create Notebook
```bash
# Click "New Notebook"
# Name: "Machine Learning Course"
# Description: "Study materials for ML"
```

### 3. Upload Materials
```bash
# Click "Upload" button
# Choose source:
#   - File (PDF, DOCX, PPTX, etc.)
#   - URL (web page)
#   - YouTube (video transcription)
#   - Text (paste directly)
```

### 4. Chat with Your Materials
```bash
# Select materials in sidebar
# Type question: "What is supervised learning?"
# Get AI-powered answer with citations
```

### 5. Generate Study Content
```bash
# Open "Studio" panel
# Choose content type:
#   - Quiz: Set difficulty, number of questions
#   - Flashcards: Choose number of cards
#   - Podcast: Generate audio dialogue
# Download or save to notebook
```

---

## 🔧 Configuration

### Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/keplerlab
JWT_SECRET_KEY=<generate-secure-key>
JWT_ALGORITHM=HS256

# LLM Provider (choose one)
LLM_PROVIDER=OLLAMA  # or GOOGLE, NVIDIA, MYOPENLM
OLLAMA_MODEL=llama3
GOOGLE_API_KEY=your-key
NVIDIA_API_KEY=your-key

# Paths
CHROMA_DIR=./data/chroma
UPLOAD_DIR=./data/uploads
MODELS_DIR=./data/models

# CORS
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### LLM Provider Setup

**Option 1: Ollama (Local, Free)**
```bash
# Install: https://ollama.ai
ollama pull llama3
ollama serve

# .env
LLM_PROVIDER=OLLAMA
OLLAMA_MODEL=llama3
```

**Option 2: Google Gemini (Cloud)**
```bash
# Get API key: https://makersuite.google.com/app/apikey
# .env
LLM_PROVIDER=GOOGLE
GOOGLE_API_KEY=your-api-key
GOOGLE_MODEL=models/gemini-2.5-flash
```

**Option 3: NVIDIA AI (Cloud)**
```bash
# Get API key: https://build.nvidia.com
# .env
LLM_PROVIDER=NVIDIA
NVIDIA_API_KEY=your-api-key
NVIDIA_MODEL=meta/llama3-70b-instruct
```

---

## 🔐 Security Features

- **JWT Authentication**: Access + refresh token rotation
- **HTTP-Only Cookies**: Secure refresh token storage
- **Multi-Tenant Isolation**: User data segregation via metadata filtering
- **File Access Tokens**: Time-limited signed URLs for downloads
- **Password Hashing**: bcrypt with salts
- **CORS Protection**: Configurable allowed origins
- **Input Validation**: Pydantic schemas for all API requests

---

## 🎓 How It Works

### Material Processing Pipeline

```
Upload → Extract Text → Chunk Text → Generate Embeddings → Store in ChromaDB → Mark Complete
```

1. **Upload**: User uploads file/URL/YouTube/text
2. **Extract**: PyPDF, python-docx, Whisper, web scraping
3. **Chunk**: Split into 1000-char chunks with 200-char overlap
4. **Embed**: Convert to 384-dim vectors using sentence-transformers
5. **Store**: Save in ChromaDB with metadata (user_id, material_id)
6. **Complete**: Mark material as processed in PostgreSQL

### RAG Chat Flow

```
Query → Embed Query → Semantic Search → Retrieve Chunks → Build Context → LLM → Response
```

1. **Query**: User asks "What is supervised learning?"
2. **Embed**: Convert query to vector
3. **Search**: Find top 7 similar chunks in ChromaDB
4. **Retrieve**: Get chunk text
5. **Context**: Combine chunks as context
6. **LLM**: Send to LLM with prompt template
7. **Response**: Return answer to user

### Content Generation

```
Material → Extract Text → Build Prompt → LLM → Parse Output → Post-Process → Save/Export
```

Example: Slide Generation
1. Fetch material text from database
2. Build prompt with theme, type, scope parameters
3. LLM generates JSON with slide content
4. Fetch images from Unsplash/Pexels
5. Render PPTX using python-pptx
6. Export to PNG images via LibreOffice
7. Return preview URLs to frontend

---

## 📊 Performance

- **Material Processing**: 10-30s for 100-page PDF
- **Embedding Generation**: 30-60s for 1000 chunks (batched)
- **RAG Chat Response**: 2-5s
- **Slide Generation**: 15-45s (including image export)
- **Podcast Generation**: 30-90s

**Optimization**: Batch processing improves embedding speed by 10-40x compared to sequential processing.

---

## 🔮 Roadmap

- [ ] Real-time streaming LLM responses
- [ ] Collaborative notebooks (multi-user)

- [ ] Advanced quiz analytics & progress tracking
- [ ] Export to Anki, Quizlet, Notion
- [ ] Mobile app (React Native)
- [ ] Multi-language support
- [ ] Citation tracking & plagiarism detection
- [ ] LMS integration (Canvas, Moodle)
- [ ] Advanced scheduling & spaced repetition

---

## 🐛 Troubleshooting

### Common Issues

**"ChromaDB quota exceeded"**
```bash
# Delete old vectors
rm -rf backend/data/chroma/*
```

**"LLM timeout"**
```bash
# Increase timeout in .env
LLM_TIMEOUT=300

# Or switch to faster model
LLM_PROVIDER=GOOGLE
```

**"CORS error in browser"
```bash
# Add your frontend URL to .env
CORS_ORIGINS=http://localhost:5173

# Restart backend
```

See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for more troubleshooting.

---

## 📝 API Documentation

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login (returns JWT)
- `POST /auth/refresh` - Refresh access token
- `GET /auth/me` - Get current user

### Notebooks
- `POST /notebooks` - Create notebook
- `GET /notebooks` - List notebooks
- `GET /notebooks/{id}` - Get notebook
- `PUT /notebooks/{id}` - Update notebook
- `DELETE /notebooks/{id}` - Delete notebook

### Materials
- `POST /upload` - Upload file
- `POST /upload/url` - Upload from URL/YouTube
- `POST /upload/text` - Upload text
- `GET /materials` - List materials
- `DELETE /materials/{id}` - Delete material

### Chat
- `POST /chat` - Send message (RAG)
- `GET /chat/history/{notebook_id}` - Get history

### Content Generation
- `POST /quiz` - Generate quiz
- `POST /flashcard` - Generate flashcards
- `POST /podcast` - Generate podcast

Full API docs: http://localhost:8000/docs

---

## 🤝 Contributing

This is a proprietary project. For internal development:

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and test thoroughly
3. Follow code style (PEP 8 for Python, ESLint for JS)
4. Update documentation
5. Submit pull request

---

## 📄 License

Proprietary software. All rights reserved.

---

## 👥 Team

**KeplerLab Development Team**

---

## 📞 Support

For questions, issues, or feature requests:
- Create an issue in the repository
- Contact the development team
- Check documentation files

---

## 🙏 Acknowledgments

- [LangChain](https://www.langchain.com/) - LLM orchestration
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Sentence Transformers](https://www.sbert.net/) - Embeddings
- [Prisma](https://www.prisma.io/) - ORM
- [Ollama](https://ollama.ai/) - Local LLM runtime

---

**Last Updated**: February 14, 2026  
**Version**: 2.0.0

---

### Quick Links

- 📚 [Complete Documentation](PROJECT_DOCUMENTATION.md)
- 🏗️ [Architecture Details](ARCHITECTURE_FLOW.md)
- 🛠️ [Developer Guide](DEVELOPER_GUIDE.md)
- 🚀 [API Reference](http://localhost:8000/docs)
