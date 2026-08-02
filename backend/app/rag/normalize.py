"""تطبيع عربي للنصوص قبل التضمين والاسترجاع.

يجمع الأشكال المختلفة لنفس الكلمة العربية:
- توحيد الهمزات: أ/إ/آ/ؤ → ا (مع ؤ→و اختيارياً)
- ى → ي ، ة → ه
- إزالة التشكيل والتنوين
- تصغير التكرارات المفرطة (أحرف مشددة مكررة)
"""

import re
import unicodedata

# إزالة التشكيل (حركات + تنوين + شدات + سكون)
_HARAKAT = re.compile(r"[\u064B-\u0652\u0670]")
# رموز قرآنية/تحكم
_EXTRA = re.compile(r"[\u0640\u06D6-\u06ED\u08F0-\u08FF\uFE70-\uFEFF\uFFFF]")

_TRANS = str.maketrans(
    {
        "\u0623": "\u0627",  # أ -> ا
        "\u0625": "\u0627",  # إ -> ا
        "\u0622": "\u0627",  # آ -> ا
        "\u0624": "\u0648",  # ؤ -> و
        "\u0626": "\u064a",  # ئ -> ي
        "\u0649": "\u064a",  # ى -> ي
        "\u0629": "\u0647",  # ة -> ه
        "\u0671": "\u0627",  # ٱ -> ا
    }
)


def normalize_arabic(text: str) -> str:
    """يطبّع نصاً عربياً لتوحيد أشكال الكلمات — يحافظ على كلمات أجنبية/أرقام."""
    if not text:
        return ""
    # NFC أولاً
    text = unicodedata.normalize("NFC", text)
    # إزالة التشكيل والرموز
    text = _HARAKAT.sub("", text)
    text = _EXTRA.sub("", text)
    # تحويل الهمزات وغيرها
    text = text.translate(_TRANS)
    # طي حالة اللاتينية (لأرقام وكلمات أجنبية صغيرة/كبيرة)
    text = text.casefold()
    # تصغير المسافات
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_arabic(ch: str) -> bool:
    return "\u0600" <= ch <= "\u06ff" or "\u0750" <= ch <= "\u077f"
