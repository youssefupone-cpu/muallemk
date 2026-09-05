# `|| true` في CI يلغي فحص الثغرات الأمنية — CI يقبل PRs بثغرات معروفة

- **التاريخ**: 2026-08-04
- **النوع**: bug (security / CI)
- **الوضعية**: reviewer
- **الحالة**: fixed
- **الأولوية**: critical
- **الملف**: `.github/workflows/ci.yml:71`

## الوصف

خطوة فحص الأمان في CI تنتهي بإنجاح دائم بفضل `|| true`، مما يعني أن **أي ثغرة أمنية في التبعيات لن تُعيق دمج PRs الخاصة بك**.

## الأدلة

```yaml
# .github/workflows/ci.yml:71
- name: Security audit
  run: npm audit --audit-level moderate || true   # ← || true يلغي الفشل دائماً
```

بما أن الخطوة تنتهي بـ `|| true`، فإن `npm audit` ستُعيد exit code 1 في وجود ثغرات — لكن `|| true` يحوّله إلى 0. الخطوة **لن تفشل أبداً** مهما كانت الثغرات.

## التأثير

- **CI موثوق بهذه الثغرات**: PRs تُدمج رغم وجود ثغرات Critical/High في التبعيات.
- **انتشارهما للإنتاج**: Docker image النهائي يحمل التبعيات الضعيفة.
- **فقدان الثقة في الـ CI**: فريقك يعتقد أن "CI يمرّر" = "آمن"، لكنه ليس كذلك.

## الحل

```yaml
- name: Security audit
  run: npm audit --audit-level high
  # أو: fail-fast على المستويات الحرجة وتوثيق المعروفة
```

استراتيجيات بديلة:
1. **إزالة `|| true`** — أبسط وأقوى حل.
2. **GitHub Dependabot** مع `target-branch: main` + `ignore` للثغرات المعلقة.
3. **`npm audit --audit-level high`** مع استثناءات موثقة في `audit-ci` config.

## المراجع

- [npm audit docs](https://docs.npmjs.com/cli/v10/commands/npm-audit)
- [GitHub Actions: Security hardening for workflows](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)

## سجل
- 2026-09-05: حُدّثت الحالة إلى `fixed` بعد إصلاح شامل في جلسة Arena.
