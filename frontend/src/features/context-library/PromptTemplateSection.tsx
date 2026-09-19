import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { CopyButton } from "@/components/ui/CopyButton";
import { Input } from "@/components/ui/Input";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { Textarea } from "@/components/ui/Textarea";
import {
  useCreatePromptTemplate,
  usePostPromptTemplateVersion,
  usePromptTemplateHistory,
  usePromptTemplates,
} from "@/hooks/usePromptTemplates";
import { SESSION_TYPE_IDS, SESSION_TYPES } from "@/types";
import type { PromptTemplate, SessionTypeId } from "@/types";

const templateSchema = z.object({
  title: z.string().trim().min(1, "Heading is required."),
  description: z.string().trim().optional(),
  body: z.string().trim().min(1, "Body is required."),
});
type TemplateFormValues = z.infer<typeof templateSchema>;

const PHASES = ["pre", "post"] as const;

const DESCRIPTION_HINT =
  "What this prompt does: when it runs, what it uses, and what it produces (and whether the output reaches the client).";

/** Context Library page editor for prompt templates — these rows are the live source
 * draft_generator.py / post_session.py read at generation time, so
 * posting a new version here actually changes what the AI sends to Gemini.
 * Append-only, same shape as the Context Library editor: edits post a new
 * version rather than overwrite in place. */
export function PromptTemplateSection() {
  const { data: templates, isLoading } = usePromptTemplates();
  const [expandedGroupId, setExpandedGroupId] = useState<string | null>(null);

  const bySlot = new Map<string, PromptTemplate>();
  templates?.forEach((template) => bySlot.set(`${template.sessionType}:${template.phase}`, template));

  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate">Prompt library</h2>
      {isLoading ? (
        <RowsSkeleton count={4} />
      ) : (
        <div className="space-y-2">
          {SESSION_TYPE_IDS.flatMap((sessionType) =>
            PHASES.map((phase) => {
              const template = bySlot.get(`${sessionType}:${phase}`);
              return template ? (
                <PromptTemplateRow
                  key={`${sessionType}:${phase}`}
                  template={template}
                  expanded={expandedGroupId === template.entryGroupId}
                  onToggleHistory={() =>
                    setExpandedGroupId((prev) => (prev === template.entryGroupId ? null : template.entryGroupId))
                  }
                />
              ) : (
                <CreateTemplateRow key={`${sessionType}:${phase}`} sessionType={sessionType} phase={phase} />
              );
            })
          )}
        </div>
      )}
    </section>
  );
}

function PromptTemplateRow({
  template,
  expanded,
  onToggleHistory,
}: {
  template: PromptTemplate;
  expanded: boolean;
  onToggleHistory: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const { data: history } = usePromptTemplateHistory(expanded ? template.entryGroupId : null);

  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-3 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-ink">{template.title}</p>
          <p className="mt-1 text-xs text-slate">
            {SESSION_TYPES[template.sessionType].label} — {template.phase === "pre" ? "before the session" : "after the session"}
          </p>
          {template.description ? (
            <p className="mt-2 max-w-prose text-sm leading-6 text-ink">{template.description}</p>
          ) : (
            <p className="mt-2 text-sm italic text-slate">No description yet. Add one when you post the next version.</p>
          )}
        </div>
        <div className="flex flex-shrink-0 items-center gap-1">
          <CopyButton text={template.body} label="Copy prompt" />
          <Pill>v{template.version}</Pill>
        </div>
      </div>
      <div className="mt-2 flex gap-3 text-xs">
        <button className="text-teal hover:underline" onClick={() => setEditing((e) => !e)}>
          {editing ? "Cancel" : "Post new version"}
        </button>
        <button className="text-slate hover:underline" onClick={onToggleHistory}>
          {expanded ? "Hide history" : "View history"}
        </button>
      </div>

      {editing && (
        <PostVersionForm
          entryGroupId={template.entryGroupId}
          initialTitle={template.title}
          initialDescription={template.description ?? ""}
          initialBody={template.body}
          onDone={() => setEditing(false)}
        />
      )}

      {expanded && (
        <div className="mt-3 space-y-1 border-t border-border pt-3">
          {history?.map((version) => (
            <div key={version.id} className="text-xs text-slate">
              <span className="tabular-nums">v{version.version}</span> — {version.title}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PostVersionForm({
  entryGroupId,
  initialTitle,
  initialDescription,
  initialBody,
  onDone,
}: {
  entryGroupId: string;
  initialTitle: string;
  initialDescription: string;
  initialBody: string;
  onDone: () => void;
}) {
  const postVersion = usePostPromptTemplateVersion();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<TemplateFormValues>({
    resolver: zodResolver(templateSchema),
    defaultValues: { title: initialTitle, description: initialDescription, body: initialBody },
  });

  const onSubmit = handleSubmit((values) => {
    postVersion.mutate(
      { entryGroupId, title: values.title, description: values.description ?? "", body: values.body },
      { onSuccess: onDone }
    );
  });

  return (
    <form onSubmit={onSubmit} className="mt-3 space-y-2 border-t border-border pt-3">
      <Input aria-label="Heading" error={!!errors.title} {...register("title")} />
      {errors.title && <p className="text-xs text-amber">{errors.title.message}</p>}
      <Textarea rows={3} aria-label="Description" placeholder={DESCRIPTION_HINT} {...register("description")} />
      <Textarea rows={10} className="font-mono" aria-label="Prompt body" error={!!errors.body} {...register("body")} />
      {errors.body && <p className="text-xs text-amber">{errors.body.message}</p>}
      <Button type="submit" variant="secondary" isLoading={postVersion.isPending}>
        Post version
      </Button>
    </form>
  );
}

/** Only reachable if a session type/phase slot has no prompt yet (e.g. a
 * newly added session type) — the seed migration covers all slots that
 * exist today. */
function CreateTemplateRow({ sessionType, phase }: { sessionType: SessionTypeId; phase: "pre" | "post" }) {
  const [creating, setCreating] = useState(false);
  const createTemplate = useCreatePromptTemplate();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TemplateFormValues>({ resolver: zodResolver(templateSchema) });

  const onSubmit = handleSubmit((values) => {
    createTemplate.mutate(
      { sessionType, phase, title: values.title, description: values.description, body: values.body },
      { onSuccess: () => { reset(); setCreating(false); } }
    );
  });

  return (
    <div className="rounded-xl border border-dashed border-border px-4 py-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate">
          {SESSION_TYPES[sessionType].label} — {phase} (no prompt yet)
        </p>
        <Button variant="secondary" onClick={() => setCreating((c) => !c)}>
          {creating ? "Cancel" : "Create prompt"}
        </Button>
      </div>
      {creating && (
        <form onSubmit={onSubmit} className="mt-3 space-y-2">
          <Input placeholder="Heading" error={!!errors.title} {...register("title")} />
          {errors.title && <p className="text-xs text-amber">{errors.title.message}</p>}
          <Textarea rows={3} aria-label="Description" placeholder={DESCRIPTION_HINT} {...register("description")} />
          <Textarea
            rows={10}
            className="font-mono"
            placeholder="Prompt body / instructions"
            error={!!errors.body}
            {...register("body")}
          />
          {errors.body && <p className="text-xs text-amber">{errors.body.message}</p>}
          <Button type="submit" isLoading={createTemplate.isPending}>
            Create
          </Button>
        </form>
      )}
    </div>
  );
}

function RowsSkeleton({ count }: { count: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center justify-between rounded-xl border border-border px-4 py-3">
          <div className="space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-32" />
          </div>
          <Skeleton className="h-5 w-10 rounded-full" />
        </div>
      ))}
    </div>
  );
}
