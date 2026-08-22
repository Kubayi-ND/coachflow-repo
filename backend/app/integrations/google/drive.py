import io
from typing import Any

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.integrations.google.auth import get_tenant_credentials

_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


async def download_file(tenant_id: str, file_id: str) -> bytes:
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("drive", "v3", credentials=credentials)

    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


async def move_file_to_folder(tenant_id: str, file_id: str, destination_folder_id: str) -> None:
    """Files a transcript into the matching client's Transcripts subfolder,
    per phase 2 (Transcript ingestion) in backend/CLAUDE.md."""
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("drive", "v3", credentials=credentials)

    file_meta = service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file_meta.get("parents", []))
    service.files().update(
        fileId=file_id,
        addParents=destination_folder_id,
        removeParents=previous_parents,
        fields="id, parents",
    ).execute()


async def list_folder_contents(tenant_id: str, folder_id: str) -> list[dict[str, Any]]:
    """Non-folder children of a Drive folder, one level deep — used by the
    one-time Drive backfill (services/drive_backfill.py) to enumerate the
    GROW context library folder and each per-client notes/transcripts
    subfolder. Unlike download_file/move_file_to_folder above, this is a
    bulk-listing capability nothing in the ongoing single-file webhook path
    needs."""
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("drive", "v3", credentials=credentials)

    files: list[dict[str, Any]] = []
    page_token: str | None = None
    query = f"'{folder_id}' in parents and trashed = false and mimeType != '{_FOLDER_MIME_TYPE}'"
    while True:
        response = (
            service.files()
            .list(q=query, fields="nextPageToken, files(id, name, mimeType, createdTime)", pageToken=page_token)
            .execute()
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return files


async def list_subfolders(tenant_id: str, folder_id: str) -> list[dict[str, Any]]:
    """Immediate subfolders of a Drive folder — the per-client folder walk
    for the client-notes and transcripts backfill sources."""
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("drive", "v3", credentials=credentials)

    query = f"'{folder_id}' in parents and trashed = false and mimeType = '{_FOLDER_MIME_TYPE}'"
    response = service.files().list(q=query, fields="files(id, name)").execute()
    return list(response.get("files", []))


async def export_google_doc_text(tenant_id: str, file_id: str) -> str:
    """Exports a native Google Doc as plain text via the Drive API — the
    counterpart to download_file for files that have no raw byte content of
    their own to download."""
    credentials = await get_tenant_credentials(tenant_id)
    credentials.refresh(Request())
    service = build("drive", "v3", credentials=credentials)

    request = service.files().export_media(fileId=file_id, mimeType="text/plain")
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue().decode("utf-8", errors="replace")
