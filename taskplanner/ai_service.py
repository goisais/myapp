from __future__ import annotations

from typing import List
import typing_extensions as typing

from google import genai
from google.genai import types
from django.conf import settings

MODEL_CANDIDATES = [
    "models/gemini-flash-latest",
    "models/gemini-2.5-flash",
    "models/gemini-flash-lite-latest",
]

client = genai.Client(api_key=settings.GEMINI_API_KEY)


class PlanItem(typing.TypedDict):
    id: int
    estimated_minutes: int
    order: int


def ai_plan_tasks(task_dicts) -> List[PlanItem]:
    prompt = f"""
あなたはタスク計画アシスタントです。

以下のタスク一覧があります。
- estimated_minutes が null のものは所要時間を推定してください
- priority と deadline を考慮して実行順を決めてください

出力は JSON配列のみ（余計な文章は禁止）。

タスク一覧:
{task_dicts}
""".strip()

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=list[PlanItem],   # Python 3.11 なのでOK
    )

    last_err = None
    for model in MODEL_CANDIDATES:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            # ここが重要：文字列を正規表現で抜くより、parsed を使う
            parsed = getattr(resp, "parsed", None)
            if not isinstance(parsed, list):
                raise ValueError(f"AI parsed がlistではありません: {type(parsed)}")
            return parsed
        except Exception as e:
            last_err = e

    raise last_err
