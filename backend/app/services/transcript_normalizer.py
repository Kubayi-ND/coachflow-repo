"""Converts whatever shape a source hands back into one schema: a list of
{speaker, timestamp, text}. Never lets a partial parse silently block the
pipeline — it logs and still attempts generation with an "unverified
transcript" flag carried into the draft (backend/CLAUDE.md phase 3).
"""
import json
import logging
import re

from app.models.transcript import ParseStatus, TranscriptSegment, TranscriptSource

logger = logging.getLogger(__name__)

# Gemini "Meeting Notes" Markdown: a `## Transcript` section of
# `**Name:** text` lines, optionally prefixed with `[hh:mm:ss]`.
_GEMINI_LINE = re.compile(r"^(?:\[(?P<ts>[^\]]*)\]\s*)?\*\*(?P<speaker>[^*]+?):?\*\*:?\s*(?P<text>.*)$")
# Plaud export: header lines, then `[hh:mm:ss] Speaker 1: text`.
_PLAUD_LINE = re.compile(r"^\[(?P<ts>[^\]]*)\]\s*(?P<speaker>[^:]*):\s*(?P<text>.*)$")
_PLAUD_MARKER = re.compile(r"^\[[^\]:]*\]$")
_TIMESTAMP = re.compile(r"^\d{1,2}:\d{2}:\d{2}$")


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


def segments_to_text(segments: list[TranscriptSegment]) -> str:
    """Numbered transcript for prompts: `L12 [00:04:10] Coach: text`. The line
    numbers give the model something to cite for evidence quotes, and let the
    post-session critique check a quote against the transcript."""
    lines = []
    for number, segment in enumerate(segments, start=1):
        stamp = f" [{segment.timestamp}]" if segment.timestamp else ""
        lines.append(f"L{number}{stamp} {segment.speaker}: {segment.text}")
    return "\n".join(lines)


def _normalize_gemini_meet(raw_bytes: bytes, attendee_names: list[str]) -> tuple[list[TranscriptSegment], ParseStatus]:
    text = raw_bytes.decode("utf-8")
    if text.lstrip().startswith(("{", "[")):
        # Structured JSON export with named speakers already.
        data = json.loads(text)
        segments = [
            TranscriptSegment(speaker=entry["speaker"], timestamp=entry["timestamp"], text=entry["text"])
            for entry in data.get("entries", [])
        ]
        return segments, ParseStatus.OK if segments else ParseStatus.PARTIAL
    return _normalize_gemini_markdown(text)


def _normalize_gemini_markdown(text: str) -> tuple[list[TranscriptSegment], ParseStatus]:
    lines = text.splitlines()
    heading = next((i for i, line in enumerate(lines) if line.strip().lower() == "## transcript"), None)
    body: list[str] = []
    if heading is None:
        body = lines
    else:
        for line in lines[heading + 1 :]:
            if line.startswith("## "):
                break
            body.append(line)

    segments: list[TranscriptSegment] = []
    partial = heading is None
    for line in (raw.strip() for raw in body):
        if not line:
            continue
        match = _GEMINI_LINE.match(line)
        if match is None or not match["text"].strip():
            partial = True
            continue
        timestamp = (match["ts"] or "").strip()
        if timestamp and not _TIMESTAMP.match(timestamp):
            partial, timestamp = True, ""
        segments.append(
            TranscriptSegment(speaker=match["speaker"].strip(), timestamp=timestamp, text=match["text"].strip())
        )
    return segments, ParseStatus.PARTIAL if partial or not segments else ParseStatus.OK


def _normalize_plaud(raw_bytes: bytes, attendee_names: list[str]) -> tuple[list[TranscriptSegment], ParseStatus]:
    # Plaud exports use generic "Speaker 1:" / "Speaker 2:" labels. Resolve
    # them to real names using the calendar event's attendee list as ground
    # truth (coach is always the practice's own account; the remaining
    # attendee is the coachee for 1-on-1s).
    text = raw_bytes.decode("utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bracketed = any(_PLAUD_LINE.match(line) for line in lines)

    speaker_map: dict[str, str] = {}
    segments: list[TranscriptSegment] = []
    partial = "�" in text

    def resolve(raw_speaker: str) -> str:
        if raw_speaker not in speaker_map:
            index = len(speaker_map)
            speaker_map[raw_speaker] = attendee_names[index] if index < len(attendee_names) else raw_speaker
        return speaker_map[raw_speaker]

    for line in lines:
        if bracketed:
            if _PLAUD_MARKER.match(line):
                continue  # export annotation such as "[END OF RECORDING]"
            match = _PLAUD_LINE.match(line)
            if match is None:
                # Lines before the first segment are the export header
                # (device, file, duration); anything later is damage.
                partial = partial or bool(segments)
                continue
            raw_speaker, timestamp, spoken = match["speaker"].strip(), match["ts"].strip(), match["text"].strip()
            if not raw_speaker or "?" in raw_speaker:
                partial, raw_speaker = True, "Unknown speaker"
            if not _TIMESTAMP.match(timestamp):
                partial, timestamp = True, ""
        else:
            if ":" not in line:
                partial = True
                continue
            raw_speaker, _, spoken = line.partition(":")
            raw_speaker, timestamp, spoken = raw_speaker.strip(), "", spoken.strip()
        segments.append(TranscriptSegment(speaker=resolve(raw_speaker), timestamp=timestamp, text=spoken))

    status = ParseStatus.PARTIAL if partial or not segments else ParseStatus.OK
    return segments, status
