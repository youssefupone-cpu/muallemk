"""اختبارات م6 — التطبيع العربي والتقطيع."""

from app.rag.chunker import (
    chunk_index_text,
    chunk_text,
    chunk_with_heading,
    split_sentences,
)
from app.rag.normalize import normalize_arabic


def test_normalize_hamza_unification():
    assert normalize_arabic("أحمد أحمد إحسان آدم") == "احمد احمد احسان ادم"


def test_normalize_yaa_and_taa():
    assert normalize_arabic("مصرية مصرية هدى هدى") == "مصريه مصريه هدي هدي"


def test_normalize_diacritics_removed():
    assert normalize_arabic("مُحَمَّدٌ كِتَابْ") == "محمد كتاب"


def test_normalize_keeps_latin_and_digits():
    out = normalize_arabic("Python 3.12 وسلام")
    assert "python" in out
    assert "3.12" in out


def test_split_sentences_basic():
    text = "الجملة الأولى. الجملة الثانية؟ والثالثة!"
    s = split_sentences(text)
    assert len(s) == 3
    assert s[0].startswith("الجملة الأولى")


def test_split_sentences_headings_kept():
    text = "# مقدمة\nنص هنا. جملة أخرى.\n## فصل الثاني\nكلام في الفصل."
    s = split_sentences(text)
    assert "# مقدمة" in s
    assert "## فصل الثاني" in s


def test_chunk_text_respects_limit():
    text = " ".join(["كلمة" * 5] * 300)
    chunks = chunk_text(text, chunk_chars=300)
    for c in chunks:
        assert len(c) <= 400  # سقف مرن قليلاً
    assert len(chunks) > 1


def test_chunk_with_heading_attaches_headings():
    text = "# التنفس\nهذا عن التنفس.\n# الدوران\nهذا عن الدوران."
    chunks = chunk_with_heading(text)
    # عنوانان → جزآن على الأقل بترويسات مختلفة (ما لم يجمعا)
    heads = [c["heading"] or "" for c in chunks]
    assert any("التنفس" in h for h in heads)
    assert any("الدوران" in h for h in heads)


def test_chunk_index_text_prepends_heading():
    chunk = chunk_index_text("# الرياضيات\nالتفاضل أساسي", chunk_chars=400)
    assert chunk[0].startswith("# الرياضيات")
