import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IcfCritique } from "@/features/scorecards/IcfCritique";
import type { IcfCritique as IcfCritiqueData } from "@/types";

const NAMES = [
  "Demonstrates Ethical Practice",
  "Embodies a Coaching Mindset",
  "Establishes and Maintains Agreements",
  "Cultivates Trust and Safety",
  "Maintains Presence",
  "Listens Actively",
  "Evokes Awareness",
  "Facilitates Client Growth",
];

function critique(): IcfCritiqueData {
  return {
    rubric_version: "icf-pcc-v1",
    overall_alignment: { rating: "meets_pcc", summary: "Solid PCC-level session." },
    competencies: NAMES.map((name, i) => ({
      id: i + 1,
      name,
      rating: i === 6 ? "emerging" : "meets_pcc",
      summary: `Summary ${i + 1}`,
      evidence:
        i === 2
          ? [
              { quote: "What would make this hour worthwhile?", line: 1, speaker: "Coach", verified: true },
              { quote: "An invented quote", line: 9, speaker: "Coach", verified: false },
            ]
          : [],
      pcc_markers: i === 2 ? [{ id: "3.1", observed: true, note: "" }, { id: "3.2", observed: false, note: "" }] : [],
      strengths: [],
      growth_areas: i === 6 ? ["Ask one question at a time (L14)"] : [],
      citations: i === 2 ? ["ctx-1"] : [],
    })),
    top_strengths: ["Clear session agreement"],
    top_growth_areas: ["Stacked questions"],
    coach_action_items: ["Pause after each question"],
    client_action_items: ["Draft the one-pager"],
    talk_ratio_estimate: "client about 70%",
    transcript_unverified: true,
  };
}

describe("IcfCritique", () => {
  it("renders every competency with its rating, evidence and markers", () => {
    render(<IcfCritique critique={critique()} citations={[{ context_id: "ctx-1", title: "ICF CCs with PCC Markers" }]} />);

    for (const name of NAMES) expect(screen.getByText(name)).toBeInTheDocument();
    expect(screen.getByText("Overall: Meets PCC")).toBeInTheDocument();
    expect(screen.getByText("Emerging")).toBeInTheDocument();
    expect(screen.getByText("3.1 observed")).toBeInTheDocument();
    expect(screen.getByText("3.2 missed")).toBeInTheDocument();
    expect(screen.getByText("Grounded in: ICF CCs with PCC Markers")).toBeInTheDocument();
    expect(screen.getByText("Coach-only · never sent to the client")).toBeInTheDocument();
  });

  it("flags quotes that weren't found in the transcript and partial transcripts", () => {
    render(<IcfCritique critique={critique()} />);

    expect(screen.getAllByText(/not found in transcript/)).toHaveLength(1);
    expect(screen.getByText(/only partly parsed/)).toBeInTheDocument();
  });

  it("falls back to a raw view for older, unstructured scorecards", () => {
    render(<IcfCritique critique={{ notes: "legacy critique text" }} />);

    expect(screen.queryByText("ICF core competencies")).not.toBeInTheDocument();
    expect(screen.getByText(/legacy critique text/)).toBeInTheDocument();
  });
});
