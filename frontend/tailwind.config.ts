import type { Config } from "tailwindcss";

// CoachFlow design tokens (frontend/CLAUDE.md). Light values are the CSS
// custom-property defaults; dark values are applied via the `.dark` class
// toggled by a theme provider (see src/app/providers.tsx).
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "rgb(var(--color-paper) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        teal: {
          DEFAULT: "rgb(var(--color-teal) / <alpha-value>)",
          soft: "rgb(var(--color-teal-soft) / <alpha-value>)",
        },
        amber: "rgb(var(--color-amber) / <alpha-value>)",
        slate: "rgb(var(--color-slate) / <alpha-value>)",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Public Sans", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
