"""حدّ معدل بسيط بالذاكرة (P0-51) — نوافذ زمنية لكل (مسار، IP).

الحد لكل IP على المسارات الحساسة (رفع مستندات / استدعاء إضافات / دردشة).
الافتراضي: RATE_LIMIT_PER_MINUTE=60 لكل مسار — كافٍ للاستخدام الشخصي
وحاجز ضد الدورات العشوائية. عند 0 يُعطَّل بالكامل.

خلف nginx (نشر docker-compose): نقرأ أول عنصر من X-Forwarded-For — يضبطه
nginx من $remote_addr الحقيقي (frontend/nginx.conf:33)، فالحد يبقى لكل IP
وليس لكل حاوية وكيل (إصلاح مراجعة 2026-08-02).
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_limits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_GC_THRESHOLD = 512  # فوقه ننظّف المفاتيح المنتهية — يمنع نمو الذاكرة بلا سقف
_GC_INTERVAL = 60.0  # ثوانٍ بين عمليات التنظيف


def _client_host(request: Request) -> str:
    """عنوان العميل الحقيقي: أول قيمة X-Forwarded-For (nginx موثوق) ثم fallback."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


def _gc(now: float) -> None:
    """يزيل مفاتيح انتهت نوافذها تماماً — حد أقصى فعلي للذاكرة (P0-51)."""
    if len(_limits) < _GC_THRESHOLD:
        return
    for key, q in list(_limits.items()):
        if q and now - q[-1] > _GC_INTERVAL:
            del _limits[key]


def rate_limiter(limit: int, window: int = 60):
    """dependency مصنّع: `limit` طلباً لكل IP في `window` ثانية (0 = تعطيل)."""

    def check(request: Request) -> None:
        if limit <= 0:
            return
        host = _client_host(request)
        key = (request.url.path, host)
        now = time.monotonic()
        _gc(now)
        q = _limits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="طلبات كثيرة — حاول بعد قليل")
        q.append(now)

    return check
