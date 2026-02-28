"""Voice map configuration for AI Live Podcast.

Maps languages to available edge-tts voices with gender, name, and preview text.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# ── Voice Map ─────────────────────────────────────────────────
# Each language maps to a list of voice entries.
# Each entry: {id, name, gender, description, preview_text}

VOICE_MAP: Dict[str, List[dict]] = {
    "en": [
        {"id": "en-US-GuyNeural", "name": "Guy", "gender": "male", "description": "Warm, conversational American male"},
        {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "female", "description": "Clear, friendly American female"},
        {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "male", "description": "Professional, steady American male"},
        {"id": "en-US-AriaNeural", "name": "Aria", "gender": "female", "description": "Expressive, engaging American female"},
    ],
    "hi": [
        {"id": "hi-IN-MadhurNeural", "name": "Madhur", "gender": "male", "description": "Natural Hindi male voice"},
        {"id": "hi-IN-SwaraNeural", "name": "Swara", "gender": "female", "description": "Warm Hindi female voice"},
    ],
    "gu": [
        {"id": "gu-IN-NiranjanNeural", "name": "Niranjan", "gender": "male", "description": "Natural Gujarati male voice"},
        {"id": "gu-IN-DhwaniNeural", "name": "Dhwani", "gender": "female", "description": "Warm Gujarati female voice"},
    ],
    "es": [
        {"id": "es-ES-AlvaroNeural", "name": "Alvaro", "gender": "male", "description": "Professional Spanish male"},
        {"id": "es-ES-ElviraNeural", "name": "Elvira", "gender": "female", "description": "Natural Spanish female"},
    ],
    "ar": [
        {"id": "ar-SA-HamedNeural", "name": "Hamed", "gender": "male", "description": "Clear Arabic male voice"},
        {"id": "ar-SA-ZariyahNeural", "name": "Zariyah", "gender": "female", "description": "Warm Arabic female voice"},
    ],
    "fr": [
        {"id": "fr-FR-HenriNeural", "name": "Henri", "gender": "male", "description": "Professional French male"},
        {"id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "female", "description": "Natural French female"},
    ],
    "de": [
        {"id": "de-DE-ConradNeural", "name": "Conrad", "gender": "male", "description": "Clear German male voice"},
        {"id": "de-DE-KatjaNeural", "name": "Katja", "gender": "female", "description": "Professional German female"},
    ],
    "ja": [
        {"id": "ja-JP-KeitaNeural", "name": "Keita", "gender": "male", "description": "Natural Japanese male"},
        {"id": "ja-JP-NanamiNeural", "name": "Nanami", "gender": "female", "description": "Clear Japanese female"},
    ],
    "zh": [
        {"id": "zh-CN-YunxiNeural", "name": "Yunxi", "gender": "male", "description": "Natural Chinese male"},
        {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "gender": "female", "description": "Warm Chinese female"},
    ],
    "pt": [
        {"id": "pt-BR-AntonioNeural", "name": "Antonio", "gender": "male", "description": "Natural Portuguese male"},
        {"id": "pt-BR-FranciscaNeural", "name": "Francisca", "gender": "female", "description": "Warm Portuguese female"},
    ],
}

# Default voice pairs per language (host, guest)
DEFAULT_VOICES: Dict[str, dict] = {
    "en": {"host": "en-US-GuyNeural", "guest": "en-US-JennyNeural"},
    "hi": {"host": "hi-IN-MadhurNeural", "guest": "hi-IN-SwaraNeural"},
    "gu": {"host": "gu-IN-NiranjanNeural", "guest": "gu-IN-DhwaniNeural"},
    "es": {"host": "es-ES-AlvaroNeural", "guest": "es-ES-ElviraNeural"},
    "ar": {"host": "ar-SA-HamedNeural", "guest": "ar-SA-ZariyahNeural"},
    "fr": {"host": "fr-FR-HenriNeural", "guest": "fr-FR-DeniseNeural"},
    "de": {"host": "de-DE-ConradNeural", "guest": "de-DE-KatjaNeural"},
    "ja": {"host": "ja-JP-KeitaNeural", "guest": "ja-JP-NanamiNeural"},
    "zh": {"host": "zh-CN-YunxiNeural", "guest": "zh-CN-XiaoxiaoNeural"},
    "pt": {"host": "pt-BR-AntonioNeural", "guest": "pt-BR-FranciscaNeural"},
}

# Language display names
LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English", "hi": "Hindi", "gu": "Gujarati", "es": "Spanish",
    "ar": "Arabic", "fr": "French", "de": "German", "ja": "Japanese",
    "zh": "Chinese", "pt": "Portuguese",
}

# Preview texts per language
PREVIEW_TEXTS: Dict[str, str] = {
    "en": "Welcome to this podcast where we explore fascinating topics together.",
    "hi": "इस पॉडकास्ट में आपका स्वागत है जहाँ हम साथ मिलकर दिलचस्प विषयों की खोज करते हैं।",
    "gu": "આ પોડકાસ્ટમાં આપનું સ્વાગત છે જ્યાં આપણે સાથે મળીને રસપ્રદ વિષયોની શોધ કરીએ છીએ.",
    "es": "Bienvenidos a este podcast donde exploramos temas fascinantes juntos.",
    "ar": "مرحبًا بكم في هذا البودكاست حيث نستكشف معًا مواضيع رائعة.",
    "fr": "Bienvenue dans ce podcast où nous explorons ensemble des sujets fascinants.",
    "de": "Willkommen zu diesem Podcast, in dem wir gemeinsam faszinierende Themen erkunden.",
    "ja": "このポッドキャストへようこそ。一緒に魅力的なトピックを探求しましょう。",
    "zh": "欢迎来到本播客，让我们一起探索有趣的话题。",
    "pt": "Bem-vindos a este podcast onde exploramos temas fascinantes juntos.",
}


def get_voices_for_language(language: str) -> List[dict]:
    """Return available voices for a language."""
    return VOICE_MAP.get(language, VOICE_MAP["en"])


def get_default_voices(language: str) -> dict:
    """Return default host/guest voice IDs for a language."""
    return DEFAULT_VOICES.get(language, DEFAULT_VOICES["en"])


def get_preview_text(language: str) -> str:
    """Return preview text for a language."""
    return PREVIEW_TEXTS.get(language, PREVIEW_TEXTS["en"])


def validate_voice(voice_id: str, language: str) -> bool:
    """Check if a voice ID is valid for the given language."""
    voices = get_voices_for_language(language)
    return any(v["id"] == voice_id for v in voices)
