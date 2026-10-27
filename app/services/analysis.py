from dotenv import load_dotenv
from app.services.text_analysis import analyze_text

load_dotenv()


def analyze_dialogue(text: str, speaker_name: str, listener_name: str | None = None):
    return analyze_text(text, speaker_name, listener_name)
