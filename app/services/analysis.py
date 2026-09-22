import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models.analysis import DialogueAnalysis


load_dotenv()

client = OpenAI()


def analyze_dialogue(
    text: str,
    speaker_name: str,
    listener_name: str,
) -> DialogueAnalysis:
    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-6-astra",
    )

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "너는 가상 마을의 대화를 분석하는 사회 관계 분석기다. "
                    "제3자에 대한 정보, 사적인 계획, 행동 평가 또는 평판에 "
                    "영향을 줄 수 있는 이야기를 가십으로 판단한다. "
                    "단순한 인사나 현재 대화 상대에 대한 직접적인 질문은 "
                    "가십으로 판단하지 않는다. "
                    "확실성은 confirmed, hearsay, speculation 중 하나로 분류한다. "
                    "평판 영향은 -1.0부터 1.0 사이로 평가한다. "
                    "모든 설명은 한국어로 작성한다."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"화자: {speaker_name}\n"
                    f"청자: {listener_name}\n"
                    f"대화: {text}"
                ),
            },
        ],
        text_format=DialogueAnalysis,
    )

    analysis = response.output_parsed

    if analysis is None:
        raise RuntimeError(
            "AI 분석 결과를 구조화하지 못했습니다."
        )

    return analysis