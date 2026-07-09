"""Bilingual demo conversations for a quick first-run experience."""

DEMO_CONVERSATIONS = [
    {
        "source": "chatgpt", "source_id": "demo-chatgpt-1",
        "title": "بناء REST API بلغة Python", "created_at": "2026-01-14T09:20:00+00:00",
        "messages": [
            {"role": "user", "content": "اشرحلي شلون أبني REST API باستخدام FastAPI مع قاعدة بيانات MongoDB؟", "created_at": "2026-01-14T09:20:00+00:00"},
            {"role": "assistant", "content": "أكيد! FastAPI من أسرع أطر العمل بلغة Python.\n\n```python\nfrom fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/items')\nasync def list_items():\n    return {'items': []}\n```\n\nللاتصال بـ MongoDB استخدم مكتبة motor غير المتزامنة، وعرّف الموديلات باستخدام Pydantic للتحقق من صحة البيانات.", "created_at": "2026-01-14T09:21:00+00:00"},
            {"role": "user", "content": "وشلون أضيف التحقق من صحة البيانات validation؟", "created_at": "2026-01-14T09:23:00+00:00"},
            {"role": "assistant", "content": "استخدم Pydantic models:\n\n```python\nfrom pydantic import BaseModel, Field\n\nclass Item(BaseModel):\n    name: str = Field(min_length=1)\n    price: float = Field(gt=0)\n```\n\nFastAPI يتحقق تلقائياً من كل طلب ويرجع خطأ 422 إذا كانت البيانات غير صالحة.", "created_at": "2026-01-14T09:24:00+00:00"},
        ],
    },
    {
        "source": "chatgpt", "source_id": "demo-chatgpt-2",
        "title": "React hooks best practices", "created_at": "2026-02-03T14:05:00+00:00",
        "messages": [
            {"role": "user", "content": "What are the most important React hooks best practices for large applications?", "created_at": "2026-02-03T14:05:00+00:00"},
            {"role": "assistant", "content": "Key React hooks best practices:\n\n1. **Keep effects focused** — one useEffect per concern\n2. **Memoize expensive computations** with useMemo\n3. **Extract custom hooks** for reusable logic\n4. **Avoid stale closures** by listing all dependencies\n5. **Use useCallback** for functions passed to memoized children\n\nCustom hooks are the biggest win: they turn complex component logic into testable, reusable functions.", "created_at": "2026-02-03T14:06:00+00:00"},
        ],
    },
    {
        "source": "claude", "source_id": "demo-claude-1",
        "title": "خطة تسويق لمتجر إلكتروني", "created_at": "2026-02-19T11:30:00+00:00",
        "messages": [
            {"role": "user", "content": "عندي متجر إلكتروني جديد لبيع القهوة المختصة، شنو أفضل استراتيجية تسويق للبداية؟", "created_at": "2026-02-19T11:30:00+00:00"},
            {"role": "assistant", "content": "استراتيجية تسويق لمتجر قهوة مختصة:\n\n1. **المحتوى التعليمي**: فيديوهات قصيرة عن طرق التحضير (V60، إسبريسو، كولد برو)\n2. **إنستغرام وتيك توك**: صور احترافية للمنتج مع وصفات\n3. **عروض الإطلاق**: خصم 20% لأول 100 عميل مع شحن مجاني\n4. **التعاون مع المقاهي المحلية**: عينات مجانية مقابل الظهور\n5. **برنامج ولاء**: نقاط على كل عملية شراء\n\nركز أول 3 أشهر على بناء الثقة والمحتوى قبل الإعلانات المدفوعة.", "created_at": "2026-02-19T11:31:00+00:00"},
            {"role": "user", "content": "شنو الميزانية المناسبة للإعلانات الشهرية؟", "created_at": "2026-02-19T11:35:00+00:00"},
            {"role": "assistant", "content": "للبداية أنصح بميزانية تجريبية:\n\n- **الشهر الأول**: 300-500 دولار موزعة على إنستغرام (60%) وتيك توك (40%)\n- **قس النتائج**: كلفة الاستحواذ على العميل (CAC) يجب أن تكون أقل من 15 دولار\n- **بعد التحسين**: زد الميزانية تدريجياً 20% شهرياً على الحملات الرابحة\n\nالأهم: لا تزيد الميزانية قبل ما تعرف أي إعلان يجيب مبيعات فعلية.", "created_at": "2026-02-19T11:36:00+00:00"},
        ],
    },
    {
        "source": "claude", "source_id": "demo-claude-2",
        "title": "Writing a technical blog post", "created_at": "2026-03-07T16:45:00+00:00",
        "messages": [
            {"role": "user", "content": "Help me structure a technical blog post about database indexing strategies.", "created_at": "2026-03-07T16:45:00+00:00"},
            {"role": "assistant", "content": "Here's a proven structure for your database indexing article:\n\n**1. Hook** — start with a real slow-query war story\n**2. The problem** — explain full table scans with a concrete example\n**3. B-tree indexes** — the workhorse, with diagrams\n**4. Composite indexes** — column order matters, leftmost prefix rule\n**5. Covering indexes** — when the index IS the data\n**6. Trade-offs** — write amplification, storage cost\n**7. Practical checklist** — how to find missing indexes with EXPLAIN\n\nKeep code examples runnable and show actual query times before/after.", "created_at": "2026-03-07T16:46:00+00:00"},
        ],
    },
    {
        "source": "gemini", "source_id": "demo-gemini-1",
        "title": "Gemini prompt history", "created_at": "2026-03-22T08:15:00+00:00",
        "messages": [
            {"role": "user", "content": "ما هي أفضل تمارين اللياقة البدنية للمبتدئين في البيت؟", "created_at": "2026-03-22T08:15:00+00:00"},
            {"role": "assistant", "content": "أفضل تمارين منزلية للمبتدئين: تمارين الضغط، السكوات، البلانك، وصعود الدرج. ابدأ بـ 15 دقيقة يومياً وزد تدريجياً.", "created_at": "2026-03-22T08:15:30+00:00"},
            {"role": "user", "content": "Compare solar panels vs wind turbines for home energy", "created_at": "2026-03-25T19:40:00+00:00"},
            {"role": "assistant", "content": "Solar panels: lower maintenance, work in most locations, ~$15-25k installed. Wind turbines: need consistent 10+ mph winds, zoning restrictions, better for rural properties.", "created_at": "2026-03-25T19:40:30+00:00"},
        ],
    },
    {
        "source": "deepseek", "source_id": "demo-deepseek-1",
        "title": "تحسين أداء موقع ويب", "created_at": "2026-04-11T13:00:00+00:00",
        "messages": [
            {"role": "user", "content": "موقعي بطيء بالتحميل، شنو أهم الخطوات لتحسين الأداء؟", "created_at": "2026-04-11T13:00:00+00:00"},
            {"role": "assistant", "content": "أهم خطوات تحسين أداء الموقع:\n\n1. **ضغط الصور**: استخدم WebP بدل PNG/JPG — توفير 30-70%\n2. **Lazy loading**: حمّل الصور عند الحاجة فقط\n3. **تقليل JavaScript**: قسّم الحزم (code splitting)\n4. **CDN**: وزّع الملفات الثابتة جغرافياً\n5. **التخزين المؤقت (Caching)**: headers صحيحة للمتصفح\n\nابدأ بقياس الأداء عبر Lighthouse وركز على أكبر المشاكل أولاً.", "created_at": "2026-04-11T13:01:00+00:00"},
        ],
    },
    {
        "source": "grok", "source_id": "demo-grok-1",
        "title": "Learning plan for machine learning", "created_at": "2026-04-28T10:30:00+00:00",
        "messages": [
            {"role": "user", "content": "Give me a 3-month learning plan to get started with machine learning.", "created_at": "2026-04-28T10:30:00+00:00"},
            {"role": "assistant", "content": "**3-Month ML Learning Plan:**\n\n**Month 1 — Foundations**\n- Python + NumPy + Pandas\n- Statistics basics: distributions, hypothesis testing\n- Linear algebra essentials: vectors, matrices\n\n**Month 2 — Core ML**\n- Supervised learning: regression, classification\n- scikit-learn projects: predict house prices, classify images\n- Cross-validation and evaluation metrics\n\n**Month 3 — Deep Learning**\n- Neural networks with PyTorch\n- One end-to-end project: train, evaluate, deploy\n- Kaggle competition for practice\n\nSpend 60% of your time coding, not watching videos.", "created_at": "2026-04-28T10:31:00+00:00"},
        ],
    },
    {
        "source": "perplexity", "source_id": "demo-perplexity-1",
        "title": "أفضل وجهات السفر الاقتصادية 2026", "created_at": "2026-05-15T17:20:00+00:00",
        "messages": [
            {"role": "user", "content": "شنو أفضل وجهات السفر الاقتصادية لهذي السنة؟", "created_at": "2026-05-15T17:20:00+00:00"},
            {"role": "assistant", "content": "أفضل الوجهات الاقتصادية لعام 2026:\n\n1. **جورجيا (تبليسي)**: بدون فيزا لأغلب الدول العربية، تكلفة يومية ~40 دولار\n2. **أذربيجان (باكو)**: مزيج أوروبي-شرقي، أسعار ممتازة\n3. **تايلاند**: الشمال (شيانغ ماي) أرخص بكثير من بانكوك\n4. **مصر**: الأقصر وأسوان خارج الموسم\n5. **البوسنة**: طبيعة خلابة وأسعار منخفضة\n\nنصيحة: احجز الطيران قبل 6-8 أسابيع واستخدم مقارنات الأسعار.", "created_at": "2026-05-15T17:21:00+00:00"},
        ],
    },
    {
        "source": "chatgpt", "source_id": "demo-chatgpt-3",
        "title": "شرح مفهوم الذكاء الاصطناعي التوليدي", "created_at": "2026-05-30T21:10:00+00:00",
        "messages": [
            {"role": "user", "content": "اشرحلي بشكل مبسط شنو يعني الذكاء الاصطناعي التوليدي وشلون يشتغل؟", "created_at": "2026-05-30T21:10:00+00:00"},
            {"role": "assistant", "content": "الذكاء الاصطناعي التوليدي (Generative AI) هو نوع من الذكاء الاصطناعي يقدر **ينشئ محتوى جديد** — نصوص، صور، أصوات، وفيديو.\n\n**شلون يشتغل ببساطة:**\n1. يتدرب النموذج على كميات هائلة من البيانات\n2. يتعلم الأنماط والعلاقات بين الكلمات والمفاهيم\n3. عند سؤاله، يتنبأ بأفضل إجابة كلمة بكلمة\n\n**أشهر الأمثلة:** ChatGPT وClaude للنصوص، Midjourney للصور.\n\nالفكرة الجوهرية: النموذج ما يحفظ إجابات جاهزة، بل يتعلم كيف \"يفكر\" بالأنماط اللي شافها.", "created_at": "2026-05-30T21:11:00+00:00"},
            {"role": "user", "content": "وشنو الفرق بينه وبين الذكاء الاصطناعي التقليدي؟", "created_at": "2026-05-30T21:14:00+00:00"},
            {"role": "assistant", "content": "الفرق الأساسي:\n\n| | التقليدي | التوليدي |\n|---|---|---|\n| **الهدف** | تصنيف وتحليل | إنشاء محتوى جديد |\n| **المخرجات** | قرار أو رقم | نص، صورة، صوت |\n| **مثال** | كشف الاحتيال البنكي | كتابة مقال كامل |\n\nالتقليدي يجاوب \"هل هذي الصورة قطة؟\" — التوليدي يرسملك قطة من الصفر.", "created_at": "2026-05-30T21:15:00+00:00"},
        ],
    },
]
