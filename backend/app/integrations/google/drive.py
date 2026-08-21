import io

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.integrations.google.auth import get_tenant_credentials


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
