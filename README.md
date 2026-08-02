# معلّمك — مساعد الدراسة المصري/العربي

مساعد دراسة ذكي **محلي أولاً**، مبني من الصفر، مع دعم **كل مزوّدي LLM** (محلي + سحابي)
ومنصة **إضافات** قابلة للتوسّع (جدول الدراسة، الكتب، تقارير AI عند الطلب…).

## البنية

```
project3/
├── backend/          # FastAPI + SQLite (Python 3.12)
│   ├── app/
│   │   ├── core/     # الإعدادات والبنية التحتية
│   │   ├── chat/     # الدردشة (SSE)
│   │   ├── documents/# استيراد المستندات (markitdown + OCR)
│   │   ├── rag/      # الاسترجاع (LlamaIndex + LanceDB + bge-m3)
│   │   ├── websearch/# البحث (tavily + SearXNG + كاش SQLite)
│   │   └── plugins/  # منصة الإضافات (Pluggy + عقود Pydantic)
│   ├── plugins/      # الإضافات المثبّتة
│   └── tests/
├── frontend/         # Vite + React 19 + Tailwind v4 + shadcn/ui (RTL/Cairo)
├── docker-compose.yml
└── .env.example
```

## التشغيل محلياً (تطوير)

**Backend** (مطلوب Python 3.12):
```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000/docs
```

**Frontend** (مطلوب Node 22+):
```bash
cd frontend
npm install
npm run dev                                  # http://localhost:3002
# ملاحظة: المنفذ 3002 لأن 3000/3001 مشغولان بخدمات أخرى على جهاز التطوير
```

**التكامل**: الواجهة توكّل `/api/*` إلى الـ backend تلقائياً (vite proxy).

## التشغيل عبر Docker

```bash
cp .env.example .env    # وعدّل حسب حاجتك
docker compose up --build
```

- الواجهة: `http://localhost:3002`
- الـ API: `http://localhost:8000/docs`
- Ollama: `http://localhost:11434` — شغّل نموذجاً محلياً:
  ```bash
  docker exec muallemk-ollama ollama pull qwen2.5:7b
  ```

## الجودة

```bash
cd backend && .venv/bin/black . && .venv/bin/ruff check . && .venv/bin/pytest
cd frontend && npx tsc --noEmit && npm run build
```
