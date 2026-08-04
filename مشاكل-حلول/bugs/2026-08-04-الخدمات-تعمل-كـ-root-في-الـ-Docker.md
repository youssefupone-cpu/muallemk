# جميع الخدمات تعمل كـ root في Docker — ثغرة امتيازات افتراضية

- **التاريخ**: 2026-08-04
- **النوع**: bug (security / Docker)
- **الوضعية**: reviewer
- **الحالة**: open
- **الأولوية**: high
- **الملفات المتأثرة**: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`

## الوصف

جميع الخدمات (backend، frontend/nginx، ollama، searxng) تعمل كـ **root** داخل الحاويات. إذا اقتُحت ثغرة RCE في أي خدمة (مثلاً exploit في markitdown OCR أو Tesseract)، يكتسب المهاجم **صلاحيات root كاملة** داخل الحاوية — مما يؤدي إلى توسع الاختراق.

## الأدلة

### backend/Dockerfile (ليس هناك USER statement)
```dockerfile
FROM python:3.12-slim AS runtime
...
RUN pip install --no-cache-dir --no-deps lancedb==0.33.0 ...
COPY --from=builder /app/app ./app
COPY --from=builder /app/plugins ./plugins
WORKDIR /app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# ← لا USER statement — يعمل كـ root افتراضياً
```

### frontend/Dockerfile (ليس هناك USER statement)
```dockerfile
FROM nginx:1.27-alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
# ← يعمل على nginx كـ root افتراضياً (nginx master process = root)
```

### docker-compose.yml (بدون user directive)
```yaml
services:
  backend:
    build: .
    # ← لا user: أو USER
  ollama:
    image: ollama/ollama:0.6.5
    # ← يعمل كـ root
  searxng:
    image: searxng/searxng:1.0.0
    # ← يعمل كـ root
```

## التأثير

- إذا تم اختراق أي خدمة، يحصل المهاجم على root داخل الحاوية.
- يسهل التصعيد إلى host filesystem إذا كان هناك ثغرة privilege escalation أو volume مكشوف.

## الحل

1. **backend/Dockerfile**: أضف مستخدم غير root:
   ```dockerfile
   RUN useradd -r -u 1000 -g appgroup appuser
   USER appuser
   WORKDIR /app
   ```

2. **frontend/Dockerfile**: nginx يجب أن يعمل على user غير root:
   ```dockerfile
   RUN addgroup -S -g 101 appgroup && adduser -S -u 101 -G appgroup appuser
   USER appuser
   ```

3. **docker-compose.yml**: أضف `user: "1000:1000"` لجميع الخدمات.

## المراجع

- [Docker: Best practices for writing Dockerfiles — Run as non-root](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [OWASP: Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
