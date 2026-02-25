import os

# Set TTS model download path before importing TTS
TTS_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data",
    "models",
)
os.makedirs(TTS_MODEL_DIR, exist_ok=True)
os.environ["TTS_HOME"] = TTS_MODEL_DIR

from TTS.api import TTS
import numpy as np
import soundfile as sf
import torch
from io import BytesIO


_tts = None
_speaker_host = None
_speaker_guest = None


def _get_tts():
    global _tts, _speaker_host, _speaker_guest
    if _tts is None:
        _tts = TTS("tts_models/en/vctk/vits", gpu=torch.cuda.is_available())
        _speaker_host = _tts.speakers[7]
        _speaker_guest = _tts.speakers[4]
    return _tts, _speaker_host, _speaker_guest


def generate_dialogue_audio(dialogue: list) -> tuple[BytesIO, list]:
    """
    Generate audio from dialogue and return timing information.

    Returns:
        tuple: (audio_buffer, timing_data)
        - audio_buffer: BytesIO containing the WAV audio
        - timing_data: list of dicts with start_time, end_time, speaker, text
    """
    tts, speaker_host, speaker_guest = _get_tts()

    audio_data = []
    timing_data = []
    sample_rate = None
    current_time = 0.0

    for speaker_type, text in dialogue:
        speaker = speaker_host if speaker_type == "host" else speaker_guest
        wav = tts.tts(text=text, speaker=speaker)

        if sample_rate is None:
            sample_rate = tts.synthesizer.output_sample_rate

        # Calculate duration of this segment
        duration = len(wav) / sample_rate

        timing_data.append(
            {
                "speaker": speaker_type,
                "text": text,
                "start_time": current_time,
                "end_time": current_time + duration,
            }
        )

        audio_data.append(wav)
        current_time += duration

    final_wav = np.concatenate(audio_data)

    buffer = BytesIO()
    sf.write(buffer, final_wav, sample_rate, format="WAV")
    buffer.seek(0)
    return buffer, timing_data
