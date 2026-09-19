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


_GEMINI_MARKDOWN = """# Gemini — Meeting Notes
**Meeting:** Grow Executive Coaching Jane Doe
**Participants:** Coach, Jane Doe

## Summary
Jane talked about a hard conversation.

## Action Items
- Draft the one-pager.

## Transcript
**Coach:** What would make this hour worthwhile?
**Jane:** Deciding how to raise it with my co-founder.
[00:01:10] **Coach:** What's the cost of waiting?
""".encode()


def test_normalize_gemini_markdown_reads_only_the_transcript_section():
    result = normalize(_GEMINI_MARKDOWN, TranscriptSource.GEMINI_MEET, attendee_names=[])

    assert result.parse_status == ParseStatus.OK
    assert [s.speaker for s in result.segments] == ["Coach", "Jane", "Coach"]
    assert result.segments[2].timestamp == "00:01:10"
    assert all("Draft the one-pager" not in s.text for s in result.segments)


_PLAUD_EXPORT = b"""PLAUD NOTE - Voice Recording Export
Device: PLAUD Note  |  File: REC0001.wav  |  Duration: 00:47:12
Recorded: 2026-07-24 13:03  |  Language: en
--------------------------------------------------------------------
[00:00:03] Speaker 1: Where shall we start today?
[00:00:07] Speaker 2: The disposal decision.
"""


def test_normalize_plaud_bracketed_export_skips_header_and_keeps_timestamps():
    result = normalize(_PLAUD_EXPORT, TranscriptSource.PLAUD, attendee_names=["Coach", "Jane Doe"])

    assert result.parse_status == ParseStatus.OK
    assert [(s.timestamp, s.speaker) for s in result.segments] == [("00:00:03", "Coach"), ("00:00:07", "Jane Doe")]


def test_normalize_plaud_damaged_export_is_partial_not_failed():
    raw = _PLAUD_EXPORT + b"[00:00:0?] Speaker ?: garbled\n<<< TRANSCRIPT TRUNCATED >>>\n"

    result = normalize(raw, TranscriptSource.PLAUD, attendee_names=[])

    assert result.parse_status == ParseStatus.PARTIAL
    assert result.segments[-1].speaker == "Unknown speaker"
    assert result.segments[-1].timestamp == ""


def test_segments_to_text_numbers_lines_for_citation():
    from app.services.transcript_normalizer import segments_to_text

    result = normalize(_PLAUD_EXPORT, TranscriptSource.PLAUD, attendee_names=["Coach", "Jane"])

    assert segments_to_text(result.segments).splitlines() == [
        "L1 [00:00:03] Coach: Where shall we start today?",
        "L2 [00:00:07] Jane: The disposal decision.",
    ]
