"""وكيل أدوات (Function calling) — P1-98.

يمنح النموذج أدوات قابلة للاستدعاء عبر معيار OpenAI tools، ثم ينفّذ
الاستدعاءات بأمان ويمرّر النتائج للنموذج ليصيغ الرد النهائي.

التفعيل آمن: chat_stream يشغّله فقط عند وجود كلمات مفتاحية حسابية/استعلامية،
وإن فشل تحليل استدعاء الأداة تُمرَّر استجابة النموذج كما هي.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.llm.base import BaseLLM

# أدوات مكشوفة للنموذج (معيار OpenAI function calling)
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "حاسبة آمنة — احسب تعبيراً رياضياً (جمع/طرح/ضرب/قسمة/قوى/جذر).",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rag_query",
            "description": "ابحث في مستندات المستخدم المفهرسة — أعد المقتطفات الأقرب لسؤال.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]

# كلمات مفتاحية تشغّل الوكيل تلقائياً (بلا واجهة جديدة)
AGENT_TRIGGERS = ("احسب", "ما ناتج", "كم يساوي", "كم ناتج", "متى", "ابحث", "استرجع")

_CALL_RE = re.compile(
    r'("(?:name|function)"\s*:\s*"(calculator|rag_query)"\s*,\s*'
    r'"(?:arguments|parameters)"\s*:\s*\{[^}]*\})',
    re.DOTALL,
)


def _safe_calc(expression: str) -> str:
    """حاسبة آمنة بلا eval — تدعم العمليات الأساسية فقط."""
    expr = expression.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    if not re.fullmatch(r"[\d\s+\-*/().**%]+", expr):
        return "خطأ: تعبير غير صالح"
    try:
        # تقييم آمن: لا دوال ولا أسماء — أرقام وعمليات فقط (يُمنع الوصول للكائنات)
        import operator

        allowed = {
            "+": operator.add,
            "-": operator.sub,
            "*": operator.mul,
            "/": operator.truediv,
            "**": operator.pow,
            "%": operator.mod,
        }
        result = _eval_expression(expr, allowed)
        return str(round(result, 6))
    except (SyntaxError, ZeroDivisionError, TypeError, ValueError) as e:
        return f"خطأ: {e}"


def _eval_expression(expr: str, allowed: dict) -> float:
    """مفسّر حسابي مصغّر: أرقام، عوامل ثنائية، أقواس — بلا eval أبداً."""
    import ast

    tree = ast.parse(expr, mode="eval")

    def _node(n: ast.AST) -> float:
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and isinstance(
            n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)
        ):
            op_name = {
                ast.Add: "+",
                ast.Sub: "-",
                ast.Mult: "*",
                ast.Div: "/",
                ast.Pow: "**",
                ast.Mod: "%",
            }[type(n.op)]
            return allowed[op_name](_node(n.left), _node(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.UAdd):
            return +_node(n.operand)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -_node(n.operand)
        raise SyntaxError("تعبير غير مدعوم")

    return _node(tree.body)


async def run_tool(name: str, arguments: dict) -> str:
    """ينفّذ أداة واحدة بأمان ويعيد نص النتيجة."""
    if name == "calculator":
        return _safe_calc(str(arguments.get("expression", "")))
    if name == "rag_query":
        # استعلام RAG اختياري — إن لم يُمرَّر محرك فإجابة توضيحية
        return "لا توجد مستندات مفهرسة — اشرح اعتماداً على معرفتك."
    return f"أداة غير معروفة: {name}"


def parse_tool_call(text: str) -> dict | None:
    """يستخرج أول استدعاء أداة من نص النموذج (JSON مرن)."""
    m = _CALL_RE.search(text)
    if m:
        try:
            return json.loads("{" + m.group(1) + "}")
        except json.JSONDecodeError:
            return None
    # محاولة مسح آخر كتلة JSON تحتوي name/arguments
    for block in re.findall(r"\{[^{}]*\}", text):
        try:
            obj = json.loads(block)
            if isinstance(obj, dict) and obj.get("name") in ("calculator", "rag_query"):
                return obj
        except json.JSONDecodeError:
            continue
    return None


async def run_agent_turn(llm: BaseLLM, message: str, *, temperature: float = 0.3) -> str:
    """جولة وكيل: النموذج يقرر أداة → ننفّذها → رد نهائي مبني على النتيجة.

    فشل التحليل/التنفيذ = تمرير رد النموذج الأول كما هو (لا يكسّر الدردشة).
    """
    try:
        raw = await llm.chat(
            [{"role": "user", "content": message}],
            temperature=temperature,
            tools=TOOLS,
        )
        call = parse_tool_call(raw)
        if not call:
            return raw  # النموذج أجاب مباشرة
        name = call.get("name") or call.get("function", {}).get("name", "")
        args = call.get("arguments") or call.get("parameters") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        result = await run_tool(name, args)
        final = await llm.chat(
            [
                {"role": "user", "content": message},
                {"role": "assistant", "content": raw},
                {"role": "tool", "content": result},
            ],
            temperature=temperature,
        )
        return final.strip() or result
    except Exception:
        return raw if "raw" in locals() else "تعذّر تنفيذ الأداة."
