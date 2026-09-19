-- Prompt template descriptions + ICF-grounded post-session templates, for a
-- database provisioned from an older schema.sql. Idempotent: safe to re-run.
-- Run after 2026-09-18_privacy_lockdown.sql:
--
--   psql "$DATABASE_URL" -f app/db/patches/2026-09-19_icf_critique_and_prompt_descriptions.sql
--
-- Templates are append-only: the new post-session prompts are posted as the
-- next version of each existing slot, so history and any admin edits stay
-- browsable. Descriptions are filled in place on every version (they're
-- metadata about the slot, not prompt text).

begin;

alter table prompt_templates add column if not exists description text;

-- A view's column list is fixed when it's created, so re-create it to expose
-- the new column (still security_invoker, per the privacy lockdown).
drop view if exists prompt_templates_current;
create view prompt_templates_current with (security_invoker = true) as
    select distinct on (entry_group_id) *
    from prompt_templates
    order by entry_group_id, version desc;
revoke all on prompt_templates_current from anon, authenticated;

update prompt_templates set description = 'Runs 3 working days before each 1-on-1 session (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past 1-on-1 sessions with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.'
where session_type = 'one_on_one' and phase = 'pre' and description is null;

update prompt_templates set description = 'Runs 5 working days before each Quarterly Strategic Review (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past Quarterly Strategic Reviews with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.'
where session_type = 'quarterly_review' and phase = 'pre' and description is null;

update prompt_templates set description = 'Runs 10 working days before each Annual Strategic Review (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past Annual Strategic Reviews with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.'
where session_type = 'annual_review' and phase = 'pre' and description is null;

update prompt_templates set description = 'Runs 5 working days before each Monthly Strategic Council (adjustable in reminder rules), and when the coach opens the session''s prep. Uses the client profile, the most relevant Context Library entries and past Monthly Strategic Councils with this client. Produces the coach-only prep briefing shown in the dashboard and a prep email draft that waits in Approvals. Nothing is sent without the coach''s approval.'
where session_type = 'monthly_council' and phase = 'pre' and description is null;

insert into prompt_templates (entry_group_id, session_type, phase, title, description, body, version)
select entry_group_id, session_type, phase, '1-on-1 Executive Coaching — Post-Session ICF Critique & Summary',
       'Runs when a 1-on-1 session transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.',
       $tpl$You are an experienced ICF assessor (MCC level) reviewing a 1-on-1 session that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
A 1-on-1 executive coaching session with an individual. Pay particular attention to: the session agreement at the start (3.1–3.4); the GROW flow (Goal, Reality, Options, Way forward); presence and the quality of questions (competencies 5 and 7); and a close that turns insight into action with accountability the client designs (8.5–8.9).

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$,
       version + 1
from prompt_templates_current
where session_type = 'one_on_one' and phase = 'post'
  and not exists (
      select 1 from prompt_templates
      where session_type = 'one_on_one' and phase = 'post' and body like '%{icf_rubric}%'
  );

update prompt_templates set description = 'Runs when a 1-on-1 session transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.'
where session_type = 'one_on_one' and phase = 'post' and description is null;

insert into prompt_templates (entry_group_id, session_type, phase, title, description, body, version)
select entry_group_id, session_type, phase, 'Quarterly Strategic Review — Post-Session ICF Critique & Summary',
       'Runs when a Quarterly Strategic Review transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.',
       $tpl$You are an experienced ICF assessor (MCC level) reviewing a Quarterly Strategic Review that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
A Quarterly Strategic Review, with an individual or a company team. Pay particular attention to: agreeing the quarter's strategic goals and how success is measured (3.1–3.4); evoking awareness of patterns across the quarter (6.5, 7.3, 7.4); and turning the review into next-quarter commitments (8.4–8.7). If this is a team session, assess whether the coach drew in every voice.

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$,
       version + 1
from prompt_templates_current
where session_type = 'quarterly_review' and phase = 'post'
  and not exists (
      select 1 from prompt_templates
      where session_type = 'quarterly_review' and phase = 'post' and body like '%{icf_rubric}%'
  );

update prompt_templates set description = 'Runs when a Quarterly Strategic Review transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.'
where session_type = 'quarterly_review' and phase = 'post' and description is null;

insert into prompt_templates (entry_group_id, session_type, phase, title, description, body, version)
select entry_group_id, session_type, phase, 'Annual Strategic Review — Post-Session ICF Critique & Summary',
       'Runs when a Annual Strategic Review transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.',
       $tpl$You are an experienced ICF assessor (MCC level) reviewing a Annual Strategic Review that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
An Annual Strategic Review, with an individual or a company team. Pay particular attention to: exploring the year's growth and who the client is becoming (5.1, 7.2, 8.2); acknowledging progress (8.8); and clear agreements for the year ahead (3.1–3.4). If this is a team session, assess whether the coach drew in every voice.

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$,
       version + 1
from prompt_templates_current
where session_type = 'annual_review' and phase = 'post'
  and not exists (
      select 1 from prompt_templates
      where session_type = 'annual_review' and phase = 'post' and body like '%{icf_rubric}%'
  );

update prompt_templates set description = 'Runs when a Annual Strategic Review transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.'
where session_type = 'annual_review' and phase = 'post' and description is null;

insert into prompt_templates (entry_group_id, session_type, phase, title, description, body, version)
select entry_group_id, session_type, phase, 'Monthly Strategic Council — Post-Session ICF Critique & Summary',
       'Runs when a Monthly Strategic Council transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.',
       $tpl$You are an experienced ICF assessor (MCC level) reviewing a Monthly Strategic Council that has just taken place.
Give the coach an honest, specific, evidence-based critique of their coaching against the ICF Core
Competencies and PCC markers, so they can see where they meet the standard and where to improve.
Only the coach sees this critique.

## ICF rubric
{icf_rubric}

## Context Library (ICF material, GROW model, this client's notes)
Each entry is headed with its id. When a judgement relies on an entry, put its id in "citations".
{context_library}

## Client profile
{client_profile}

## Transcript
Lines are numbered L1, L2, ... Quote word for word and give the line number.
{transcript}

## Focus for this session
A Monthly Strategic Council, with an individual or a company team. Pay particular attention to: holding focus and time (3.1, 5.3); challenging without attachment (7.5); and clear actions with accountability (8.6, 8.7). If this is a team session, assess whether the coach drew in every voice.

## How to assess
- Assess all 8 competencies, in order. For each give: a rating, a one- or two-sentence summary,
  1-3 evidence quotes copied exactly from the transcript with their line number and speaker, the PCC
  markers of that competency you observed or clearly missed, strengths, and growth areas.
- Rate only what the transcript shows. With no evidence, use "not_observed" and say so; don't infer.
- Make growth areas concrete: point to the moment (line) and suggest the question or move that would
  have met the marker.
- Estimate who did most of the talking (PCC marker 7.8).
- Coach action items: 2-4 things the coach can practise next session. Client action items: what the
  client committed to, in their words.

## Output
Respond with JSON only, in exactly this shape. "competencies" must hold 8 entries, ids 1-8, and each
entry's "pcc_markers" may only use that competency's marker ids.
{{
  "scorecard": {{
    "rubric_version": "icf-pcc-v1",
    "overall_alignment": {{"rating": "meets_pcc", "summary": "..."}},
    "competencies": [
      {{
        "id": 1, "name": "Demonstrates Ethical Practice", "rating": "meets_pcc", "summary": "...",
        "evidence": [{{"quote": "...", "line": 12, "speaker": "Coach"}}],
        "pcc_markers": [],
        "strengths": ["..."], "growth_areas": ["..."], "citations": ["<context library id>"]
      }}
    ],
    "top_strengths": ["..."],
    "top_growth_areas": ["..."],
    "coach_action_items": ["..."],
    "client_action_items": ["..."],
    "talk_ratio_estimate": "client about 70%, coach about 30%"
  }},
  "client_summary": "..."
}}

"client_summary" is written to the client: a warm, plain-prose summary of what they explored, the
insights they named and the actions they committed to. It must not mention ratings, the ICF rubric
or any assessment of the coach.
$tpl$,
       version + 1
from prompt_templates_current
where session_type = 'monthly_council' and phase = 'post'
  and not exists (
      select 1 from prompt_templates
      where session_type = 'monthly_council' and phase = 'post' and body like '%{icf_rubric}%'
  );

update prompt_templates set description = 'Runs when a Monthly Strategic Council transcript is linked to its session, or when the coach clicks Analyse session. Uses the numbered transcript, the ICF rubric (8 core competencies, 37 PCC markers), the Context Library and the client profile. Produces a coach-only ICF critique (a rating per competency with transcript evidence, strengths and where to improve) and a client summary draft that waits in Approvals.'
where session_type = 'monthly_council' and phase = 'post' and description is null;

commit;
