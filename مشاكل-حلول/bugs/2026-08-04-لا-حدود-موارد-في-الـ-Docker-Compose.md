# لا حدود موارد (mem/cpu) في Docker Compose — خطر استنزاف النظام

- **التاريخ**: 2026-08-04
- **النوع**: bug (security / Docker / DoS)
- **الوضعية**: reviewer
- **الحالة**: fixed
- **الأولوية**: high
- **الملف**: `docker-compose.yml`

## الوصف

لم يُحدّد أي حد لاستهلاك الموارد (ذاكرة RAM، CPU) على أي خدمة في `docker-compose.yml`. هذا يعني أن أي خدمة (خاصةً Ollama و backend) يمكنها استهلاك **كامل موارد النظام**، مما يؤدي إلى توقف الخوادم الأخرى أو نظام التشغيل ككل.

## الأدلة

```yaml
# docker-compose.yml — لا أي resource limits
services:
  backend:
    build: .
    ports: ["8000:8000"]
    volumes: ["./backend/app:/app/app"]  # ← volume mount غير مناسب للإنتاج
    env_file:
      - ./.env                           # ← .env كامل داخل الحاوية
    depends_on: [lancedb, ollama]

  ollama:
    image: ollama/ollama:0.6.5           # ← :latest في الأصل
    ports: ["11434:11434"]               # ← مُعرّض على المضيف!
    volumes:
      ollama-data:/root/.ollama

  searxng:
    image: searxng/searxng:1.0.0
    ports: ["8080:8080"]                 # ← مُعرّض على المضيف!

  frontend:
    build: ./frontend
    ports: ["3002:80"]
    # ← لا CPU، لا RAM، لا diskIO limits على أي خدمة
```

لا يوجد:
- `mem_limit:` ولا `mem_reservation:` ولا `mem_swappiness:`
- `cpus:` ولا `cpu_quota:` ولا `cpu_shares:`
- `log_driver:`/حد لحجم الـ logs

## التأثير

- **Ollama**: استنزاف RAM كامل النظام → kernel OOM killer يقتل العمليات العشوائياً.
- **Backend**: استنزاف RAM خلال معالجة PDF كبيرة أو batch embedding → توقف الخدمة.
- **SearXNG**: fork bomb ممكن إذا كان مكشوفاً على الإنترنت.
- مراقبة سجلات Docker: `/var/lib/docker/containers/*/*.log` ينمو إلى GB بلا حد — `json-file` driver بلا `max-size`.

## الحل

```yaml
services:
  backend:
    ...
    deploy:
      resources:
        limits:
          memory: 1g
          cpus: "1.5"
        reservations:
          memory: 512m
          cpus: "0.5"
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  ollama:
    ...
    deploy:
      resources:
        limits:
          memory: 4g       # ← حسب VRAM المتاحة
          cpus: "2.0"

  searxng:
    ...
    deploy:
      resources:
        limits:
          memory: 512m
          cpus: "0.5"
    expose:                # ← بدلاً من ports — خاصة للـ dev
      - "8080"
```

## المراجع

- [Compose: الخصائص resources](https://docs.docker.com/compose/how-tos/deploy-resource-constraints/)
- [Docker: Resource constraints cheet sheet](https://learn.microsoft.com/en-us/azure/container-instances/container-instances-resource-constraints)

## سجل
- 2026-09-05: حُدّثت الحالة إلى `fixed` بعد إصلاح شامل في جلسة Arena.
