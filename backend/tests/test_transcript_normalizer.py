import json

from app.models.transcript import ParseStatus, TranscriptSource
from app.services.transcript_normalizer import normalize


def test_normalize_gemini_meet_ok():
    payload = json.dumps(
        {"entries": [{"speaker": "Jane Doe", "timestamp": "00:00:01", "text": "Hello"}]}
    ).encode()

    result = normalize(payload, TranscriptSource.GEMINI_MEET, attendee_names=["Jane Doe"])

    assert result.parse_status == ParseStatus.OK
    assert result.segments[0].speaker == "Jane Doe"


def test_normalize_plaud_resolves_generic_labels():
    raw = b"Speaker 1: Hi there\nSpeaker 2: Hello coach"

    result = normalize(raw, TranscriptSource.PLAUD, attendee_names=["Coach Name", "Jane Doe"])

    assert result.parse_status == ParseStatus.OK
    assert result.segments[0].speaker == "Coach Name"
    assert result.segments[1].speaker == "Jane Doe"


def test_normalize_plaud_partial_on_malformed_line():
    raw = b"Speaker 1: Hi there\nthis line has no colon"

    result = normalize(raw, TranscriptSource.PLAUD, attendee_names=[])

    assert result.parse_status == ParseStatus.PARTIAL


def test_normalize_failure_never_raises():
    result = normalize(b"\xff\xfe not json", TranscriptSource.GEMINI_MEET, attendee_names=[])
    assert result.parse_status == ParseStatus.FAILED
    assert result.segments == []
