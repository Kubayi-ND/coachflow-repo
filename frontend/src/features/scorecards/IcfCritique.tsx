import { JsonTree } from "@/components/ui/JsonTree";
import { Pill } from "@/components/ui/Pill";
import type { IcfCompetencyAssessment, IcfCritique as IcfCritiqueData, IcfRating, ScorecardCitation } from "@/types";

const RATING_LABEL: Record<IcfRating, string> = {
  not_observed: "Not observed",
  emerging: "Emerging",
  meets_pcc: "Meets PCC",
  exceeds_pcc: "Exceeds PCC",
};

const RATING_TONE: Record<IcfRating, "neutral" | "teal" | "amber"> = {
  not_observed: "neutral",
  emerging: "amber",
  meets_pcc: "teal",
  exceeds_pcc: "teal",
};

/** True when a stored critique has the ICF shape; older scorecards (before
 * the ICF rubric) fall back to a raw JSON view. */
function isIcfCritique(value: unknown): value is IcfCritiqueData {
  const critique = value as Partial<IcfCritiqueData> | null;
  return !!critique && typeof critique === "object" && Array.isArray(critique.competencies) && !!critique.overall_alignment;
}

/** The coach-only post-session ICF critique: overall alignment, one card per
 * core competency with transcript evidence and PCC markers, then where to
 * improve. Never shown to or sent to the client. */
export function IcfCritique({ critique, citations = [] }: { critique: unknown; citations?: unknown[] }) {
  if (!isIcfCritique(critique)) {
    return (
      <div className="rounded-lg bg-surface-2 p-4">
        <JsonTree value={critique} />
      </div>
    );
  }
  const titles = new Map(
    (citations as ScorecardCitation[]).filter((c) => c && c.context_id).map((c) => [c.context_id, c.title])
  );

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <div className="flex flex-wrap items-center gap-2">
          <Pill tone={RATING_TONE[critique.overall_alignment.rating]}>
            Overall: {RATING_LABEL[critique.overall_alignment.rating]}
          </Pill>
          <span className="text-xs text-slate">Coach-only · never sent to the client</span>
        </div>
        <p className="mt-3 text-sm leading-6 text-ink">{critique.overall_alignment.summary}</p>
        {critique.talk_ratio_estimate && (
          <p className="mt-2 text-xs text-slate">Talk time: {critique.talk_ratio_estimate}</p>
        )}
        {critique.transcript_unverified && (
          <p className="mt-3 rounded-lg bg-amber/10 px-3 py-2 text-xs text-amber">
            The transcript only partly parsed, so some competencies may be under-evidenced.
          </p>
        )}
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        <ListCard title="Top strengths" items={critique.top_strengths} />
        <ListCard title="Where to improve" items={critique.top_growth_areas} />
        <ListCard title="Practise next session" items={critique.coach_action_items} />
        <ListCard title="Client's commitments" items={critique.client_action_items} />
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate">ICF core competencies</h2>
        {critique.competencies.map((assessment) => (
          <CompetencyCard key={assessment.id} assessment={assessment} titles={titles} />
        ))}
      </section>
    </div>
  );
}

function CompetencyCard({ assessment, titles }: { assessment: IcfCompetencyAssessment; titles: Map<string, string> }) {
  return (
    <article className="rounded-xl border border-border bg-surface p-4 shadow-card">
      <header className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-medium text-ink">
          <span className="tabular-nums text-slate">{assessment.id}.</span> {assessment.name}
        </h3>
        <Pill tone={RATING_TONE[assessment.rating]}>{RATING_LABEL[assessment.rating]}</Pill>
      </header>
      <p className="mt-2 text-sm leading-6 text-ink">{assessment.summary}</p>

      {assessment.evidence.length > 0 && (
        <ul className="mt-3 space-y-2">
          {assessment.evidence.map((evidence, i) => (
            <li key={i} className="border-l-2 border-teal/40 pl-3 text-sm leading-6 text-ink">
              &ldquo;{evidence.quote}&rdquo;
              <span className="ml-2 text-xs text-slate">
                {[evidence.speaker, evidence.line != null ? `line ${evidence.line}` : null].filter(Boolean).join(" · ")}
              </span>
              {!evidence.verified && (
                <span className="ml-2 text-xs text-amber">not found in transcript, check before relying on it</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {assessment.pcc_markers.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5" aria-label="PCC markers">
          {assessment.pcc_markers.map((marker) => (
            <span
              key={marker.id}
              title={marker.note || undefined}
              className={`rounded-full px-2 py-0.5 text-[11px] tabular-nums ${
                marker.observed ? "bg-teal-soft text-teal" : "bg-surface-2 text-slate line-through"
              }`}
            >
              {marker.id} {marker.observed ? "observed" : "missed"}
            </span>
          ))}
        </div>
      )}

      {(assessment.strengths.length > 0 || assessment.growth_areas.length > 0) && (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <MiniList title="Strengths" items={assessment.strengths} />
          <MiniList title="Growth areas" items={assessment.growth_areas} />
        </div>
      )}

      {assessment.citations.length > 0 && (
        <p className="mt-3 text-xs text-slate">
          Grounded in: {assessment.citations.map((id) => titles.get(id) ?? "Context Library entry").join("; ")}
        </p>
      )}
    </article>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-xl border border-border bg-surface p-4 shadow-card">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate">{title}</h2>
      {items.length > 0 ? (
        <ul className="space-y-1.5 text-sm leading-6 text-ink">
          {items.map((item, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-teal">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate">Nothing noted.</p>
      )}
    </section>
  );
}

function MiniList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate">{title}</p>
      <ul className="mt-1 space-y-1 text-sm leading-6 text-ink">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
