async def run(ctx, action="list", payload=None):
    """مكتبة كتب بسيطة — تخزين معزول داخل data/books.json."""
    if action == "add":
        books = ctx.read_json("books.json") if (ctx.data_dir / "books.json").exists() else []
        entry = {"title": payload.get("title", "بدون عنوان"), "author": payload.get("author", "")}
        books.append(entry)
        ctx.write_json("books.json", books)
        return {"added": entry, "total": len(books)}
    if action == "list":
        if not (ctx.data_dir / "books.json").exists():
            return {"books": []}
        return {"books": ctx.read_json("books.json")}
    if action == "for-rag":
        # يمنح محتوى الكتب كسلسلة نصية لخط RAG — الواجهة تختار كيف تستخدمه
        books = ctx.read_json("books.json") if (ctx.data_dir / "books.json").exists() else []
        return {"books": books}
    return {"error": "إجراء غير معروف"}
