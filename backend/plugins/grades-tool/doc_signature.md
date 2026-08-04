# grades-tool — توثيق التوقيع (P3-79)

## المشكلة
`grades-tool` يعرّض `run(ctx, grades)` فقط لا يقبل معامل `action`، على عكس
`books-reports` الذي يعرّض `run(ctx, action, ...)`.

هذا يعني أن **المرسل العام** (`/plugins/{name}/invoke`) يجب أن يمرّر للـ plugin
موجهاً فقط باستخدام `Plugin.accepts(param)` — وهو ما يفعله بالفعل في
`app/plugins/manager.py`:

```python
def accepts(self, param: str) -> bool:
    return param in inspect.signature(mod.run).parameters
```

وفي `router.py`:

```python
kwargs = {k: v for k, v in body.items() if p.accepts(k)}
```

## التوقيع المتوافق
| الحقل       | النوع          | ملاحظة                                 |
|-------------|----------------|-----------------------------------------|
| `ctx`       | dict           | يُحقن تلقائياً — لا تُرسله من العميل.    |
| `grades`    | list[GradeIn]  | قائمة (مادة/درجة) لاحتساب المعدل.       |

`action` **غير مقبول** — لو وصلته من العميل يُتجاهّل صامتاً.

## مثال الاستدعاء
```json
POST /plugins/grades-tool/invoke
{
  "grades": [
    {"subject": "الرياضيات", "grade": 95},
    {"subject": "اللغة العربية", "grade": 88}
  ]
}
```

## التصحيح المستقبلي (اقتراح)
إذا أضيف `action` إلى grades-tool مستقبلاً، يجب توحيده مع
books/reports عبر `action: Literal["calc","report"]` — انظر `problems/P3-79-unified-action.md`.
