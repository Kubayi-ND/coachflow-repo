import { BrowserRouter } from "react-router-dom";

import { AppRouter } from "./router";
import { Providers } from "./providers";
import { NavShell } from "./NavShell";

// prettier-ignore
const DIRECTION_CONTRACT = `<!--
impeccable:direction seed=coachflow-flowmail-dashboard
THESIS: CoachFlow becomes a sidebar-and-card operations console — stat tiles surface what needs attention before the coach scrolls, refusing the flat top-nav list the app shipped with.
OWN-WORLD: dark teal sidebar rail with icon+label nav and a live approvals badge; paper-toned content on elevated surface cards (shadow-card/cardmd/panel); teal primary + amber attention accents; Fraunces display / Public Sans body; tabular-nums throughout.
STORY: a coach opens the app and reads active clients, upcoming sessions, prep-ready, and attention counts before scrolling, then scans the approvals queue always knowing which tenant a send comes from.
FIRST VIEWPORT: fixed 240px dark sidebar; top bar with page title, notifications, theme toggle, avatar; a 4-tile KPI strip; session rows grouped by client as hover-interactive cards with countdown chips.
FORM: modern SaaS admin dashboard (sidebar + topbar + stat tiles + elevated cards) — brief-pinned to the FlowMail Dribbble reference, no roll.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
-->`;

export function App() {
  return (
    <>
      <span style={{ display: "none" }} aria-hidden="true" dangerouslySetInnerHTML={{ __html: DIRECTION_CONTRACT }} />
      <Providers>
        <BrowserRouter>
          <NavShell>
            <AppRouter />
          </NavShell>
        </BrowserRouter>
      </Providers>
    </>
  );
}
