// Generates frontend/src/types/sessionTypes.generated.ts from session-types.json.
// Run via `pnpm --filter frontend run gen:session-types` (wired as a pre-dev script).
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = JSON.parse(
  readFileSync(join(here, "..", "session-types.json"), "utf-8")
) as {
  sessionTypes: {
    id: string;
    label: string;
    namingPattern: string;
    leadTimeWorkingDays: number;
  }[];
};

const outPath = join(here, "..", "..", "..", "frontend", "src", "types", "sessionTypes.generated.ts");

const body = `// AUTO-GENERATED from shared/types/session-types.json. Do not edit by hand.
// Regenerate: node shared/types/scripts/generate-session-types.ts

export type SessionTypeId = ${source.sessionTypes.map((t) => `"${t.id}"`).join(" | ")};

export interface SessionTypeDefinition {
  id: SessionTypeId;
  label: string;
  namingPattern: string;
  leadTimeWorkingDays: number;
}

export const SESSION_TYPES: Record<SessionTypeId, SessionTypeDefinition> = {
${source.sessionTypes
  .map(
    (t) => `  ${t.id}: {
    id: "${t.id}",
    label: ${JSON.stringify(t.label)},
    namingPattern: ${JSON.stringify(t.namingPattern)},
    leadTimeWorkingDays: ${t.leadTimeWorkingDays},
  },`
  )
  .join("\n")}
};

export const SESSION_TYPE_IDS: SessionTypeId[] = [
${source.sessionTypes.map((t) => `  "${t.id}",`).join("\n")}
];
`;

mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, body);
console.log(`Generated ${outPath}`);
