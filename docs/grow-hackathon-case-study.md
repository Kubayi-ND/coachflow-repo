# Grow Coaching Hackathon Case Study

## Challenge Brief: Enterprise-Grade Automation for the Modern Solopreneur

## 1. Context & Background

**Grow Coaching** is an elite executive coaching firm operated by a single principal coach. The business model is simple but highly premium: the coach sells high-value strategic time by the hour. In this model, **time is the primary revenue driver**, meaning every hour spent on administrative tasks directly detracts from top-line revenue potential.
Currently, the coach is experiencing severe operational drag. Preparing for sessions, analyzing post-session outputs, and coordinating recurring strategic reviews require intense manual effort. The administrative burden is heavily exacerbated by a fragmented, multi-tenant digital ecosystem. The coach operates across **three distinct email environments and two platform providers** to accommodate historical setups and client-specific privacy needs:
- **Tenant A:** Google Workspace (Primary Brand & Calendar)
- **Tenant B:** Google Workspace (Secondary Venture)
- **Tenant C:** Microsoft 365 / Exchange (Corporate Client Liaison)
The objective of this hackathon is to design an automated, intelligent, and secure data orchestration engine that eliminates administrative overhead, standardizes client communication, and introduces automated quality assurance for the coaching sessions themselves.

## 2. The Current Workflow & System Bottlenecks

Currently, I make use of the following platforms, tools and actions.:
1. Google Calendar to schedule all my executive coaching and strategic workshops (in rare / exceptional situations I may be required to use Teams as the coaching platform depending on client needs).
2. Gemini Note taker in Google Meet to record meetings / transcripts
3. Google Drive with dedicated client folders, per company, and per coachee
4. Google Drive that contains a folder with my context library as detailed below. I am manually saving the recordings (Plaud or Gemini Notes) into the respective Google Drive client folders.
5. Plaud device to record in-person sessions
6. Gemini Notebook - Once for each client (company and individual). I manually update the Notebook sources from the relevant client Google Drive folders.
7. Obsidian to store my prompts. I have a “pre-coaching prompt and post coaching prompt. I manually copy and paste the prompt before (pre-coaching) after each coaching session (post-coaching prompt) into Gemini Notebook.
Note: Currently my Grow coaching email is joss@grow-za.com. This email is a Microsoft account. I also have a personal gmail joss.dutrevou@gmail.com in order to be able to use the Google Calendar. I am trying to find a way to migrate the Microsoft email to my Google environment.

## 3. The Required Workflow

The operational lifecycle of an executive coaching engagement at Grow Coaching is divided into four distinct phases. Cross-functional teams must map, optimize, and automate these workflows.
```text
[Calendar Trigger] ➔ [Context Aggregation] ➔ [AI Prompt Engine] ➔ [Draft Communications]
```

### A. Pre-Session Preparation (One-on-One Executive Coaching)

- **Trigger:** The system must scan the primary Google Calendar to identify upcoming 1-on-1 executive coaching sessions. These are typically recurring every four weeks and follow a strict naming convention: Grow Executive Coaching [Coachee Name].
- **Lead Time:** Exactly **3 working days (72 hours)** prior to the scheduled session, the system must execute the prep sequence.
- **Internal Notification:** Generate an automated briefing for the coach. This briefing must aggregate and synthesize historical data, specifically pulling notes and action items from the *immediate prior session* with that specific client.
- **Client Communications:** The system must generate a draft email addressed to the client from the correct originating email tenant. The email must:
  - Remind them of the upcoming session date/time.
  - Reference specific unresolved action items or discussions from the previous meeting.
  - Formally request the client to reply with any specific agenda items they wish to prioritize.

### B. Post-Session Analysis & Quality Critique

- **Trigger:** The conclusion of a 1-on-1 session and the availability of a meeting transcript.
- **Data Ingestion:** The system must ingest raw text transcripts generated from various capture tools (Plaud, Gemini, or MS Teams).
- **AI Evaluation:** The ingested transcript must be passed through an LLM evaluation engine. The engine will run a specialized prompt to critique the coach’s performance against a centralized **Context Library** (e.g., International Coaching Federation (ICF) core competencies and the GROW coaching model framework).
- **Output generation:** The system must produce two outputs:
  1. An internal performance scorecard/critique saved to the coach's files.
  2. A highly polished, concise summary email drafted for the client detailing key takeaways and newly assigned action items.
  3. Any action items for the coach to be automatically posted into Google Tasks.

### C. Quarterly Strategic Review (QSR) Preparation

- **Trigger:** Identification of a high-level "Quarterly Strategic Review" on the Google Calendar.
- **Lead Time:** Exactly **5 working days** prior to the review.
- **Workflow:**
  - Aggregate data from the past three months of Strategic Council Meetings sessions.
  - Generate a coach notification summarizing the previous quarter's overarching outcomes and pending strategic action items.
  - Utilize an AI prompt to isolate recurring macroeconomic or behavioral themes across the client's history to suggest high-level strategic topics for the review.
  - Draft a pre-session email to the client containing a link to or an inline copy of a pre-populated strategic questionnaire to gauge alignment.

### D. Annual Strategic Review (ASR) Preparation

- **Trigger:** Identification of an "Annual Strategic Review" on the calendar.
- **Lead Time:** Exactly **10 working days** prior to the review.
- **Workflow:**
  - Generate a long-range notification for the coach summarizing the year-long trajectory.
  - Draft a comprehensive preparatory email to the client setting expectations for the deep-dive annual strategy session.

### E. Monthly Strategic Council Preparation

- **Trigger:** Identification of a " Monthly Strategic Council" on the calendar.
- **Lead Time:** Exactly **5 working days** prior to the review.
- **Workflow:**
  - Generate a long-range notification for the coach summarizing the month-long trajectory.
  - Draft a comprehensive preparatory email to the client setting expectations for the recurring monthly strategy council session.

## 3. Data & Technology Footprint

Participants must design a solution that bridges the following disconnected technologies:
```text
+--------------------------------------------------------------------------+
|                            THE FRAGMENTED TECH STACK                     |
+-----------------------------------+--------------------------------------+
| Google Ecosystem                  | Microsoft & Hardware Ecosystem       |
+-----------------------------------+--------------------------------------+
| • 2x Google Workspace Accounts    | • 1x Microsoft 365 Exchange Account  |
| • Google Calendar (Primary Sync)  | • MS Teams (Transcript Source)       |
| • Google Drive (Context Library)  | • Plaud AI (Hardware Audio Captures) |
| • Gemini (Ad-hoc AI Transcript)   |                                      |
+-----------------------------------+--------------------------------------+
```

### Data Formats & Payload Types

- **Calendar Data:** JSON payloads from Google Calendar API v3 (Event names, Start/End times, Attendee metadata).
- **Transcripts:** Unstructured text files, vtt/srt caption files, or markdown exports. Text formatting varies significantly between Plaud webhooks, Microsoft Graph transcript extractions, and Gemini exports.
- **Context Library:** Semi-structured Markdown, PDFs, and Google Docs stored within a central Google Drive repository containing coaching frameworks and client historical logs.

## 4. Business Constraints, Risks, and Assumptions

### Gaps & Systemic Risks

> [!WARNING]
> **Data Orchestration Complexity:** Managing OAuth2 authentication tokens, webhooks, and state persistence across three separate email accounts and two separate platform providers presents a major architectural hurdle. Security tokens must be handled securely without cross-tenant data leakage.

- **Ambiguous Naming Triggers:** While 1-on-1 meetings use a predictable string (Grow Executive Coaching [Coachee Name]), Quarterly (QSR) and Annual (ASR) reviews lack standardized naming conventions in the historical calendar.
- **Transcript Variability:** Transcripts will vary in quality, speaker diarization tags (e.g., "Speaker 1" vs. actual names), and structural layout depending on whether they originate from Teams, Gemini, or Plaud hardware.
- **AI Evaluation Subjectivity:** Grading a human coach's soft skills via an LLM introduces hallucination and subjectivity risks. The solution must ensure the AI critique remains highly objective, structured, and anchored directly to the provided Context Library documents.
- All recordings and transcripts are of a **highly confidential** nature and client needs assurance that their personal data is not compromised or made freely available outside the Grow coaching environment.

### Assumptions & Constraints Matrix

| Type | ID | Technical / Business Definition |
| --- | --- | --- |
| Assumption | ASM-001 | Calendar events for standard sessions are consistently named Grow Executive Coaching [Coachee Name], or Grow Quarterly Strategic Review, or Grow Annual Strategic Review, or Grow Monthly Strategic Council |
| Assumption | ASM-002 | Meeting transcripts from all sources are available in a machine-readable text format via API, webhook, or manual drop. |
| Assumption | ASM-003 | The "Context Library" documentation is centrally stored in a master Google Drive folder accessible by the orchestration system. |
| Constraint | CON-001 | The system must authenticate and interact with 3 distinct email addresses (2x Google Workspace, 1x Microsoft) without cross-contamination. |
| Constraint | CON-002 | The automation engine must differentiate between standard (3-day), quarterly (5-day), and annual (10-day) lead times based purely on calendar parsing logic. |

## 5. Hackathon Blueprint & Evaluation Framework

### For a High-Pressure 24/48-Hour Weekend Sprint

To extract maximum value from a short, intense sprint, the hackathon must balance rapid prototyping with sound architectural thinking.

### Recommended Sprint Timeline

- **Friday 18:00 | Kickoff & Architecture Brainstorm:** Problem statement drop, API credential provisioning, and team alignment.
- **Saturday 09:00 | Mid-Point Technical Review:** Teams must present an architecture diagram/data flow to the technical experts to ensure no one spends 48 hours down a dead-end technical path.
- **Sunday 12:00 | Code Freeze & Data Validation:** Stop all development. Teams focus purely on preparing working demonstrations and refining their pitch decks.
- **Sunday 14:00 | Final Presentations:** 7-minute presentations followed by 5 minutes of intensive QA per team.

### Role-Specific Deliverables (What the Judges Are Looking For)

#### 1. Business Analysts (BA)

- **Process Architecture:** A clear "As-Is" vs. "To-Be" process map illustrating how human-in-the-loop validation works (e.g., where the coach reviews a draft email before it auto-sends).
- **Exception Handling Framework:** Documented logic for what occurs if a client changes a meeting time within the 3-day buffer window, or if a transcript fails to upload.

#### 2. Data Analysts

- **Metrics Dashboard & ROI Evaluation:** Define the Key Performance Indicators (KPIs) to measure success (e.g., Admin Hours Saved, Pipeline Speed, Token Cost vs. Billable Time Saved).
- **Data Standardization Layer:** A mapping design detailing how disparate transcript formats (Plaud, Teams, Gemini) are cleaned, normalized, and parsed into a consistent schema for LLM consumption.

#### 3. Software Developers

- **Integration Pipeline (Proof of Concept):** A functional script or low-code orchestration (e.g., Make.com, n8n, LangChain, or AWS Step Functions) that successfully captures a mock calendar trigger and fetches the corresponding mock historical client data.
- **Multi-Tenant Auth Architecture:** A clear security framework explanation detailing how Microsoft Graph API and Google Workspace APIs are safely managed using secure environment secrets.

### Evaluation Committee & Oversight Framework

To ensure a fair and rigorous evaluation, the panel must include at least one Senior Enterprise Architect (Technical), one Senior Analytics Lead (Data), and one Product/Operations Manager (Business).
```text
[ EVALUATION COMMITTEE ]
│
┌───────────────────────┼───────────────────────┐
▼                       ▼                       ▼
[Technical Feasibility] [Data Analytics & QA]   [Business Value & Ops]
(Weight: 40%)           (Weight: 30%)           (Weight: 30%)
```

#### Scoring Matrix (Total 100 Points)

#### Technical Feasibility & Architecture (40 Points)

- **API & Integrity Design (20 pts):** How elegantly does the team handle the multi-tenant Google/Microsoft challenge? Is the design secure, or does it risk sending Client A's data from Client B's email?
- **Prompt Engineering & RAG Robustness (20 pts):** How well does the system ground its critiques in the Context Library? Are the prompts designed to minimize hallucinations and output standardized JSON/Markdown summaries?

#### Data Analytics & Quality Assurance (30 Points)

- **Parsing and Normalization Logic (15 pts):** Did the team address transcript variability? Is there a programmatic approach to clean raw audio transcripts before analysis?
- **Operational Metrics & Observability (15 pts):** Is there a mechanism to track system performance, token costs, and processing errors?

#### Business Value & Operational Usability (30 Points)

- **Human-In-The-Loop Design (15 pts):** Does the system give the coach a frictionless way to review and tweak draft emails, or does it try to do too much autonomously, risking client relationship damage?
- **Process Optimization & UX (15 pts):** Is the output clean, highly scannable, and actionable for a busy executive coach, or does it overwhelm them with text?
