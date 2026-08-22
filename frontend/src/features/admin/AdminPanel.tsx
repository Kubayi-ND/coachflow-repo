import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { apiFetch } from "@/lib/apiClient";
import { SESSION_TYPES } from "@/types";
import type { SessionTypeId } from "@/types";

import { ContextLibrarySection } from "./ContextLibrarySection";
import { PromptTemplateSection } from "./PromptTemplateSection";

interface ReminderRule {
  sessionType: SessionTypeId;
  leadTimeWorkingDays: number;
  namingPattern: string;
}

interface TenantStatus {
  id: string;
  workspaceDomain: string;
  connected: boolean;
}

/** Tenant credential status, reminder-rule editor, prompt template editor,
 * and Context Library editor — the templates that replaced Obsidian
 * (frontend/CLAUDE.md). User management is not yet built. */
export function AdminPanel() {
  return (
    <div className="space-y-10">
      <h1 className="text-2xl">Admin</h1>
      <TenantStatusSection />
      <ReminderRulesSection />
      <PromptTemplateSection />
      <ContextLibrarySection />
    </div>
  );
}

function TenantStatusSection() {
  const { data: tenants, isLoading } = useQuery({
    queryKey: ["admin", "tenants"],
    queryFn: () => apiFetch<TenantStatus[]>("/api/admin/tenants"),
  });

  return (
    <section>
      <h2 className="text-lg mb-2">Tenants</h2>
      {isLoading ? (
        <RowsSkeleton count={2} />
      ) : (
        <ul className="space-y-2">
          {tenants?.map((tenant) => (
            <li
              key={tenant.id}
              className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3"
            >
              <span>{tenant.workspaceDomain}</span>
              {/* Connection status only — never the raw token, per root CLAUDE.md. */}
              <Pill tone={tenant.connected ? "teal" : "amber"}>{tenant.connected ? "Connected" : "Expired"}</Pill>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ReminderRulesSection() {
  const queryClient = useQueryClient();
  const { data: rules, isLoading } = useQuery({
    queryKey: ["admin", "reminder-rules"],
    queryFn: () => apiFetch<ReminderRule[]>("/api/admin/reminder-rules"),
  });

  const updateRule = useMutation({
    mutationFn: (rule: ReminderRule) =>
      apiFetch(`/api/admin/reminder-rules/${rule.sessionType}`, {
        method: "PUT",
        body: JSON.stringify({
          session_type: rule.sessionType,
          lead_time_working_days: rule.leadTimeWorkingDays,
          naming_pattern: rule.namingPattern,
        }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "reminder-rules"] }),
  });

  return (
    <section>
      <h2 className="text-lg mb-2">Reminder rules</h2>
      {isLoading ? (
        <RowsSkeleton count={4} />
      ) : (
        <div className="space-y-2">
          {rules?.map((rule) => (
            <ReminderRuleRow key={rule.sessionType} rule={rule} onSave={(next) => updateRule.mutate(next)} />
          ))}
        </div>
      )}
    </section>
  );
}

/** Shared by both admin sections — each row here is the same
 * label-left/control-right shape as a tenant row or reminder-rule row. */
function RowsSkeleton({ count }: { count: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3">
          <div className="space-y-2">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-48" />
          </div>
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

function ReminderRuleRow({ rule, onSave }: { rule: ReminderRule; onSave: (rule: ReminderRule) => void }) {
  const [leadTime, setLeadTime] = useState(rule.leadTimeWorkingDays);

  return (
    <div className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3">
      <div>
        <p className="text-sm">{SESSION_TYPES[rule.sessionType].label}</p>
        <p className="text-xs text-slate">{rule.namingPattern}</p>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="number"
          min={0}
          className="w-16 rounded-md border border-slate/30 bg-transparent px-2 py-1 text-sm tabular-nums"
          value={leadTime}
          onChange={(e) => setLeadTime(Number(e.target.value))}
        />
        <span className="text-xs text-slate">working days</span>
        <Button
          variant="secondary"
          onClick={() => onSave({ ...rule, leadTimeWorkingDays: leadTime })}
          disabled={leadTime === rule.leadTimeWorkingDays}
        >
          Save
        </Button>
      </div>
    </div>
  );
}
