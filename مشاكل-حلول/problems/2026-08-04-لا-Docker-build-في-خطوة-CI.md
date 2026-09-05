# مشكلة: لا يوجد Docker build في خطوة CI — لا نشر موثوق

- **التاريخ**: 2026-08-04
- **النوع**: problem (CI/CD / deployment)
- **الوضعية**: reviewer
- **الحالة**: fixed
- **الأولوية**: medium
- **الملف**: `.github/workflows/ci.yml`

## الوصف

خطوة CI الأساسية تُنفذ **lint + test فقط** — ولا تُؤخذ أي صورة Docker ولا تُدفع لـ registry. هذا يعني أن:

1. **Docker build غير مختبر في CI**: `lancedb==0.36.0` (غير موجود) أو أي broken dependency لن يُكتشف حتى يحاول أحده تشغيل `docker compose up --build`.
2. **لا انعكاس على التكلفة أو الزمن**: الـ CI يمرّر في 20 ثانية، لكن الـ Docker build يأخذ 5 minutes وممكن أن يفشل.
3. **Plan.md §3** ينص على: "معيار النجاح: Docker build ناجح" — لكن CI لا يتحقق من هذا.

## الأدلة

```yaml
# .github/workflows/ci.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - checkout@v4
      - setup-python@v5
      - setup-node@v4
      - cd backend && pip install -e ".[dev]" && ruff && pytest     # Backend tests
      - cd frontend && npm ci && tsc && build && vitest              # Frontend tests
      - pip-audit, npm audit                                        # Security (لكن npm audit || true!)
      # ← لا Docker build job!
```

## الحل

أضف `docker-build` job منفصل:

```yaml
jobs:
  docker-build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: docker-compose.yml
          load: true              # تحميل الصورة محلياً للاختبار
          push: false
          target: backend
          # أو استخدم docker compose بدلاً من build مباشر
      - name: Verify image
        run: |
          docker run --rm muallemk-backend python -c "import app; print('OK')"
          docker run --rm muallemk-backend uvicorn --help  # smoke test
```

### أو باستخدام docker compose:
```yaml
      - name: Docker compose config check
        run: docker compose -f docker-compose.yml config --quiet
      - name: Docker build smoke test
        run: |
          docker buildx bake --load backend
          docker run --rm muallemk-backend:sha-$GITHUB_SHA /health-check
```

## المراجع

- [docker/build-push-action](https://github.com/docker/build-push-action)
- [GitHub Actions: Building and testing Docker images](https://docs.github.com/en/actions/use-case-deployment-for-docker-containers/building-and-testing-docker-images-as-part-of-a-workflow)

## سجل
- 2026-09-05: حُدّثت الحالة إلى `fixed` بعد إصلاح شامل في جلسة Arena.
