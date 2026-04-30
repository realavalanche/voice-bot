## CLAUDE.md (Final - Concise Version)

```markdown
# Reid & Taylor Voice Chatbot

Bilingual (Hindi/English) voice bot for premium menswear e-commerce. Helps customers find products, get sizing guidance, and answer FAQs via voice.

## Tech Stack
- **Backend:** Python 3.11, FastAPI, Sarvam AI (ASR/TTS/LLM)
- **Vector DB:** ChromaDB (product search + FAQ)
- **Frontend:** React, TypeScript, Vite
- **Deploy:** Render (Web Service + Static Site)

## Structure
```
backend/
  app/main.py, routers/, services/, models/
  data/faq.pdf, products.json
  requirements.txt, runtime.txt
frontend/
  src/components/, hooks/, App.tsx
render.yaml
```

## Commands
```bash
# Backend dev
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend dev
cd frontend && npm install && npm run dev

# Test
pytest backend/tests/
npm test --prefix frontend

# Deploy (auto on push to main)
git push origin main
```

## Conventions
**Python:** PEP 8, type hints required, async for I/O, snake_case
**TypeScript:** Functional components, hooks, camelCase
**API:** RESTful `/api/products`, `/api/voice-chat`, JSON responses
**Git:** `feat:` `fix:` `docs:` commits, no force push

## Render Setup
**Backend (Web Service):**
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`
- Disk: 1GB at `/data` for ChromaDB
- Env: `SARVAM_API_KEY`, `CHROMA_PERSIST_DIR=/data/chroma`

**Frontend (Static Site):**
- Build: `cd frontend && npm install && npm run build`
- Publish: `frontend/dist`
- Env: `VITE_API_URL=https://your-backend.onrender.com`

**Required Files:**
- `backend/runtime.txt`: `python-3.11`
- `backend/requirements.txt`: Add `gunicorn`
- Health endpoint: `/health` returns status + disk check

## Sample Interactions
```
User: "Mujhe formal shirts dikhao under 3000"
Bot: [Searches] "Main aapko 5 shirts dikha rahi hoon..."

User: "What is your return policy?"
Bot: [FAQ retrieval] "We accept returns within 15 days..."
```

## Data
- FAQ: `/backend/data/faq.pdf`
- Products: Mock JSON (name, price, sizes, colors, category)
- Embeddings: Pre-compute on startup → ChromaDB

## Constraints
- Latency: <3s voice-to-voice
- Concurrency: 50 simultaneous chats
- Cache Sarvam API calls aggressively

## Next Steps
1. FastAPI backend + health check
2. Sarvam AI integration (ASR/TTS/LLM test)
3. RAG pipeline (FAQ PDF → embeddings → ChromaDB)
4. Voice endpoint (audio → text → LLM → audio)
5. React frontend with mic button
6. Create render.yaml
7. Deploy to Render
```
