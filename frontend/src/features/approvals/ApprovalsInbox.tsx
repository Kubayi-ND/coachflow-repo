import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/Toast";
import { CheckCircleIcon } from "@/components/ui/icons";
import { useApproveDraft, useDrafts, useRejectDraft } from "@/hooks/useDrafts";
import type { AiDraft, DraftType, TenantId } from "@/types";

const DRAFT_TYPE_LABEL: Record<DraftType, string> = {
  reminder: "Reminder",
  summary: "Summary",
  questionnaire: "Questionnaire",
  prep_email: "Prep email",
};

/** The core loop. Never auto-refresh-away an item the coach has started
 * editing — edited state is local to each row and only cleared on an
 * explicit action (frontend/CLAUDE.md). */
export function ApprovalsInbox() {
  const { data: drafts, isLoading } = useDrafts();
  const pendingCount = drafts?.length ?? 0;

  return (
    <div>
      <div className="mb-6 flex items-center gap-2 text-sm text-slate">
        <span className="rounded-full bg-amber/15 px-2 py-0.5 text-xs tabular-nums text-amber">{pendingCount} pending</span>
      </div>

      {isLoading && <ApprovalsSkeleton />}

      {drafts && drafts.length === 0 && (
        <div className="flex flex-col items-center rounded-xl border border-border bg-surface py-20 text-center shadow-card">
          <CheckCircleIcon className="h-12 w-12 text-teal/40" />
          <p className="mt-4 text-base font-medium text-ink">Inbox is clear</p>
          <p className="mt-1 text-sm text-slate">All drafts have been reviewed.</p>
        </div>
      )}

      <div className="space-y-4">
        {drafts?.map((draft) => (
          <DraftRow key={draft.id} draft={draft} />
        ))}
      </div>
    </div>
  );
}

function DraftRow({ draft }: { draft: AiDraft }) {
  const [editedBody, setEditedBody] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const approveDraft = useApproveDraft();
  const rejectDraft = useRejectDraft();
  const toast = useToast();

  const bodyValue = editedBody ?? draft.body;

  async function handleApprove() {
    try {
      await approveDraft.mutateAsync({ draftId: draft.id, editedBody: editedBody ?? undefined });
      toast.show("Sent");
    } catch {
      toast.show("Failed to send", "error");
    }
  }

  async function handleReject() {
    if (!rejectReason.trim()) return;
    try {
      await rejectDraft.mutateAsync({ draftId: draft.id, reason: rejectReason });
      toast.show("Draft rejected");
    } catch {
      toast.show("Failed to reject", "error");
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <div className="mb-4 flex items-center gap-2">
        <Pill tone="teal">{DRAFT_TYPE_LABEL[draft.draftType]}</Pill>
        <TenantPill tenantId={draft.tenantId} />
      </div>
      <Textarea className="min-h-36 bg-surface-2" value={bodyValue} onChange={(e) => setEditedBody(e.target.value)} />
      <p className="mt-1.5 text-right text-[10px] text-slate">{bodyValue.length} characters</p>
      {rejecting ? (
        <div className="flex flex-wrap items-center gap-2">
          <Input
            className="min-w-[200px] flex-1"
            placeholder="Reason for rejection"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <Button variant="danger" onClick={handleReject} isLoading={rejectDraft.isPending} disabled={!rejectReason.trim()}>
            Confirm reject
          </Button>
          <Button variant="secondary" onClick={() => setRejecting(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <Button className="flex-1 sm:flex-none" onClick={handleApprove} isLoading={approveDraft.isPending}>
            {editedBody !== null ? "Edit then approve" : "Approve & send"}
          </Button>
          <Button variant="danger" onClick={() => setRejecting(true)}>
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}

function ApprovalsSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-surface p-5 shadow-card space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-24 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-32 w-full" />
          <div className="flex gap-2">
            <Skeleton className="h-9 w-36" />
            <Skeleton className="h-9 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Originating tenant, always visible — this is a multi-tenant system and
 * the coach needs to know which mailbox a send will come from
 * (frontend/CLAUDE.md). */
function TenantPill({ tenantId }: { tenantId: TenantId }) {
  return <Pill>{tenantId === "tenant_a" ? "Tenant A" : "Tenant B"}</Pill>;
}
