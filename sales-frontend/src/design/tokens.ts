export const colors = {
  bg:           "#f1f4f3",
  surface:      "#ffffff",
  surfaceAlt:   "#ececf3",
  border:       "#c9ccd1",
  borderSubtle: "#e2e4e8",

  accent:       "#7c5cbf",
  accentMuted:  "#6b4aad",
  accentLight:  "#c6afec",
  accentFaint:  "rgba(198,175,236,0.18)",

  text:          "#1a1630",
  textSecondary: "#4a4468",
  muted:         "#7b6fa3",
  mutedLight:    "#a89fc5",
} as const;

export const typography = {
  fontSans: ["Inter", "system-ui", "sans-serif"],
  fontMono: ["'JetBrains Mono'", "'Fira Code'", "ui-monospace", "monospace"],

  heading: {
    xl: { fontSize: "2.25rem", fontWeight: "700", lineHeight: "1.15", letterSpacing: "-0.025em" },
    lg: { fontSize: "1.5rem",  fontWeight: "700", lineHeight: "1.2",  letterSpacing: "-0.02em"  },
    md: { fontSize: "1.125rem",fontWeight: "600", lineHeight: "1.3",  letterSpacing: "-0.01em"  },
    sm: { fontSize: "0.875rem",fontWeight: "600", lineHeight: "1.4",  letterSpacing: "-0.005em" },
  },

  body: {
    lg: { fontSize: "1rem",    fontWeight: "400", lineHeight: "1.7"  },
    md: { fontSize: "0.875rem",fontWeight: "400", lineHeight: "1.65" },
    sm: { fontSize: "0.75rem", fontWeight: "400", lineHeight: "1.6"  },
  },

  medium: {
    lg: { fontSize: "1rem",    fontWeight: "500", lineHeight: "1.6"  },
    md: { fontSize: "0.875rem",fontWeight: "500", lineHeight: "1.5"  },
    sm: { fontSize: "0.75rem", fontWeight: "500", lineHeight: "1.45" },
  },

  label: {
    md: { fontSize: "0.75rem",  fontWeight: "600", letterSpacing: "0.06em", textTransform: "uppercase" as const },
    sm: { fontSize: "0.625rem", fontWeight: "600", letterSpacing: "0.08em", textTransform: "uppercase" as const },
  },

  caption: { fontSize: "0.625rem", fontWeight: "400", lineHeight: "1.5" },
} as const;

export const shadows = {
  card:  "0 1px 4px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06)",
  modal: "0 8px 40px rgba(0,0,0,0.18)",
  glow:  "0 0 0 3px rgba(124,92,191,0.2)",
} as const;
