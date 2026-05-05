import json
import os

_QUIZ_PATH = os.path.join(os.path.dirname(__file__), "..", "content", "quiz_questions.json")


def load_quiz_config() -> dict:
    with open(_QUIZ_PATH, encoding="utf-8") as f:
        return json.load(f)
