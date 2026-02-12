from __future__ import annotations

import os
import json
import re
from functools import lru_cache
from typing import List
import typing

from django.conf import settings
from google import genai
from google.genai import types


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    # settings.py に GEMINI_API_KEY = "..." を置く想定
    api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY が未設定です（settings.py か環境変数に設定してください）")

    return genai.Client(api_key=api_key)


MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]


class PlanItem(typing.TypedDict, total=False):
    id: int
    order: int
    start_at: str
    end_at: str
    estimated_minutes: int
    priority: int


def ai_plan_tasks(
    task_dicts,
    existing_events,
    availability,
    window_start: str,
    window_end: str,
) -> List[PlanItem]:
    client = _get_client()
    prompt = f"""
    あなたはタスク計画アシスタントです。
    目的: 既存カレンダー予定を避けて、新規タスクをスケジューリングしてください。

    制約:
    - 既存予定(existing_events)の時間帯には絶対に重ねない
    - window_start〜window_end の範囲内に収める
    - 作業可能時間(availability)の範囲内に入れる
    - deadline が近い/priority が高いタスクを優先
    - desired_at があるタスクは可能な限りその日時に寄せる（無理なら最も近い空き枠）
    - estimated_minutes が null のタスクは内容(memo/title)から推定して埋める
    - 1日の中で無理な詰め込みを避ける（連続作業は最大90分、間に10分休憩）
    - 出力は JSON配列のみ。余計な文章は禁止。
    - 各要素に order を必ず付ける（1からの連番）
    追加の重要ルール（固定値の尊重）:
    - tasks の *_locked が true の項目は絶対に変更しない
    - desired_at_locked=true のタスクは start_at/end_at を desired_at に合わせる（衝突時のみ最寄り空きへ）
    - estimated_minutes_locked=true のタスクは estimated_minutes を変更しない
    - priority_locked=true のタスクは priority を変更しない
    - *_locked=false または値が null の項目だけ推定・決定してよい

    出力方針:
    - 既に決まっている値を「上書き」するのは禁止
    - 未定な項目のみを決めて出力する


    入力:
    tasks: {task_dicts}

    existing_events:{existing_events}

    availability: {availability}

    window_start: "{window_start}"
    window_end: "{window_end}"
    """.strip()

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
    )

    last_err = None
    for model in MODEL_CANDIDATES:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            # --- ここから：自前でJSONパース ---
            text = getattr(resp, "text", None)
            if not text:
                # SDKによっては candidates から取れることもあるので保険
                raise ValueError("AI応答に text がありません")

            # たまに ```json ... ``` で返ってくる事故対策
            text = text.strip()
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)

            data = json.loads(text)

            if not isinstance(data, list):
                raise ValueError(f"AI出力がlistではありません: {type(data)}")

            return data
            # --- ここまで ---
        except Exception as e:
            last_err = e

    raise last_err
