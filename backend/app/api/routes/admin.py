from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.db.repository import get_supabase, row_of, rows_of
from app.models.admin import PromptTemplate, ReminderRule, TenantStatus
from app.models.user import User

router = APIRouter()


@router.get("/reminder-rules", response_model=list[ReminderRule])
async def get_reminder_rules(user: User = Depends(require_admin)) -> list[ReminderRule]:
    rows = rows_of(get_supabase().table("reminder_rules").select("*").execute())
    return [ReminderRule(**row) for row in rows]


@router.put("/reminder-rules/{session_type}", response_model=ReminderRule)
async def update_reminder_rule(session_type: str, body: ReminderRule, user: User = Depends(require_admin)) -> ReminderRule:
    result = (
        get_supabase()
        .table("reminder_rules")
        .update({"lead_time_working_days": body.lead_time_working_days, "naming_pattern": body.naming_pattern})
        .eq("session_type", session_type)
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return ReminderRule(**row)


@router.get("/prompt-templates", response_model=list[PromptTemplate])
async def get_prompt_templates(user: User = Depends(require_admin)) -> list[PromptTemplate]:
    rows = rows_of(get_supabase().table("prompt_templates").select("*").execute())
    return [PromptTemplate(**row) for row in rows]


@router.put("/prompt-templates/{session_type}/{phase}", response_model=PromptTemplate)
async def update_prompt_template(
    session_type: str, phase: str, body: PromptTemplate, user: User = Depends(require_admin)
) -> PromptTemplate:
    result = (
        get_supabase()
        .table("prompt_templates")
        .upsert({"session_type": session_type, "phase": phase, "body": body.body, "version": body.version})
        .execute()
    )
    row = row_of(result)
    assert row is not None
    return PromptTemplate(**row)


@router.get("/tenants", response_model=list[TenantStatus])
async def get_tenants(user: User = Depends(require_admin)) -> list[TenantStatus]:
    rows = rows_of(get_supabase().table("tenants").select("id,workspace_domain,connected").execute())
    return [TenantStatus(**row) for row in rows]
