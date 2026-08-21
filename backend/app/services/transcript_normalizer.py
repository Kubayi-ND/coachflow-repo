"""Converts whatever shape a source hands back into one schema: a list of
{speaker, timestamp, text}. Never lets a partial parse silently block the
pipeline — it logs and still attempts generation with an "unverified
transcript" flag carried into the draft (backend/CLAUDE.md phase 3).
"""
import json
import logging

from app.models.transcript import ParseStatus, TranscriptSegment, TranscriptSource

logger = logging.getLogger(__name__)


class NormalizedTranscript:
    def __init__(self, segments: list[TranscriptSegment], parse_status: ParseStatus):
        self.segments = segments
        self.parse_status = parse_status


def normalize(raw_bytes: bytes, source: TranscriptSource, attendee_names: list[str]) -> NormalizedTranscript:
    try:
        if source == TranscriptSource.GEMINI_MEET:
            segments, status = _normalize_gemini_meet(raw_bytes, attendee_names)
        else:
            segments, status = _normalize_plaud(raw_bytes, attendee_names)
        return NormalizedTranscript(segments, status)
    except Exception:
        logger.exception("Transcript parse failed for source=%s", source)
        return NormalizedTranscript([], ParseStatus.FAILED)


def _normalize_gemini_meet(raw_bytes: bytes, attendee_names: list[str]) -> tuple[list[TranscriptSegment], ParseStatus]:
    # Gemini Meet exports are structured JSON with named speakers already.
    data = json.loads(raw_bytes)
    segments = [
        TranscriptSegment(speaker=entry["speaker"], timestamp=entry["timestamp"], text=entry["text"])
        for entry in data.get("entries", [])
    ]
    status = ParseStatus.OK if segments else ParseStatus.PARTIAL
    return segments, status


def _normalize_plaud(raw_bytes: bytes, attendee_names: list[str]) -> tuple[list[TranscriptSegment], ParseStatus]:
    # Plaud exports are plain text with generic "Speaker 1:" / "Speaker 2:"
    # labels. Resolve them to real names using the calendar event's attendee
    # list as ground truth (coach is always the practice's own account; the
    # remaining attendee is the coachee for 1-on-1s).
    text = raw_bytes.decode("utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    speaker_map: dict[str, str] = {}
    segments: list[TranscriptSegment] = []
    partial = False

    for line in lines:
        if ":" not in line:
            partial = True
            continue
        raw_speaker, _, spoken_text = line.partition(":")
        raw_speaker = raw_speaker.strip()
        if raw_speaker not in speaker_map:
            resolved_index = len(speaker_map)
            speaker_map[raw_speaker] = (
                attendee_names[resolved_index] if resolved_index < len(attendee_names) else raw_speaker
            )
        segments.append(
            TranscriptSegment(speaker=speaker_map[raw_speaker], timestamp="", text=spoken_text.strip())
        )

    status = ParseStatus.PARTIAL if partial or not segments else ParseStatus.OK
    return segments, status
