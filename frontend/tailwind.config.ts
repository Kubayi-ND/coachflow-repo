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
        surface: {
          DEFAULT: "rgb(var(--color-surface) / <alpha-value>)",
          2: "rgb(var(--color-surface-2) / <alpha-value>)",
        },
        border: "rgb(var(--color-border) / <alpha-value>)",
        sidebar: {
          bg: "rgb(var(--color-sidebar-bg) / <alpha-value>)",
          fg: "rgb(var(--color-sidebar-fg) / <alpha-value>)",
          accent: "rgb(var(--color-sidebar-accent) / <alpha-value>)",
        },
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        body: ["Public Sans", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
        cardmd: "0 4px 12px 0 rgb(0 0 0 / 0.10), 0 2px 4px -2px rgb(0 0 0 / 0.08)",
        panel: "0 8px 24px 0 rgb(0 0 0 / 0.14), 0 4px 8px -4px rgb(0 0 0 / 0.10)",
      },
    },
  },
  plugins: [],
} satisfies Config;
