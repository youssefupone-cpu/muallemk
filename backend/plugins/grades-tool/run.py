async def run(ctx, grades):
    """يحسب معدل قائمة درجات: [{"subject": "رياضيات", "grade": 85}, ...]."""
    grades = grades or []
    if not grades:
        return {"average": 0, "count": 0}
    total = sum(float(g.get("grade", 0)) for g in grades)
    return {
        "average": round(total / len(grades), 2),
        "count": len(grades),
        "max": max(float(g.get("grade", 0)) for g in grades),
    }
