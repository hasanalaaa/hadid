"""Heuristic auto-tagging for conversations (English + Arabic keywords)."""

from __future__ import annotations

import re
from typing import Any

_TOPICS: dict[str, list[str]] = {
    "coding": [
        "code", "function", "class", "python", "javascript", "typescript",
        "react", "api", "bug", "error", "debug", "github", "commit", "pr",
        "variable", "loop", "async", "await", "sql", "database", "backend",
        "frontend", "html", "css", "component", "deploy", "server", "docker",
        "برمجة", "كود", "دالة", "خطأ", "برنامج", "موقع", "تطبيق", "قاعدة بيانات",
    ],
    "design": [
        "design", "ui", "ux", "user interface", "mockup", "figma", "layout",
        "typography", "color", "palette", "wireframe", "prototype", "brand",
        "تصميم", "واجهة", "ألوان", "شعار",
    ],
    "writing": [
        "write", "draft", "essay", "article", "blog", "email", "copy",
        "proofread", "edit", "story", "script", "content", "summary", "translate",
        "كتابة", "مقال", "ترجمة", "ملخص", "قصة", "رسالة",
    ],
    "business": [
        "business", "strategy", "marketing", "sales", "customer", "revenue",
        "startup", "investor", "pitch", "meeting", "proposal", "budget",
        "project", "team", "okr", "kpi",
        "تسويق", "مشروع", "شركة", "عمل", "استثمار", "ميزانية",
    ],
    "learning": [
        "explain", "tutorial", "learn", "course", "study", "definition",
        "concept", "introduction", "beginner", "guide", "how to", "example",
        "difference between", "compare",
        "اشرح", "تعلم", "دورة", "شرح", "مثال", "الفرق بين",
    ],
    "life": [
        "health", "fitness", "recipe", "travel", "advice", "relationship",
        "personal", "habit", "goal", "meditation", "therapy", "plan",
        "صحة", "رياضة", "وصفة", "سفر", "نصيحة", "خطة",
    ],
}


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\u0600-\u06FF\s-]", "", text.lower())


def suggest_tags(conv: dict[str, Any]) -> list[str]:
    text = _normalize(" ".join(m.get("content", "") for m in conv.get("messages", [])))
    words = set(text.split())
    matches: set[str] = set()
    for tag, keywords in _TOPICS.items():
        for kw in keywords:
            if " " in kw:
                if kw in text:
                    matches.add(tag)
                    break
            elif kw in words:
                matches.add(tag)
                break
    return sorted(matches)
