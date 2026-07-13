/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "'Fira Code'", "ui-monospace", "monospace"],
      },
      colors: {
        bg:              "#f1f4f3",
        surface:         "#ffffff",
        "surface-alt":   "#ececf3",
        border:          "#c9ccd1",
        "border-subtle": "#e2e4e8",

        accent:          "#7c5cbf",
        "accent-muted":  "#6b4aad",
        "accent-light":  "#c6afec",
        "accent-faint":  "rgba(198,175,236,0.18)",

        muted:           "#7b6fa3",
        "muted-light":   "#a89fc5",
      },
      boxShadow: {
        card:  "0 1px 4px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.06)",
        modal: "0 8px 40px rgba(0,0,0,0.18)",
        glow:  "0 0 0 3px rgba(124,92,191,0.2)",
      },
      backgroundImage: {
        "purple-gradient": "linear-gradient(135deg, #9b7ed4 0%, #7c5cbf 100%)",
      },
      keyframes: {
        "fade-up": {
          "0%":   { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "scale-in": {
          "0%":   { opacity: "0", transform: "scale(0.97)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "slide-down": {
          "0%":   { opacity: "0", transform: "translateY(-6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up":    "fade-up 0.22s ease-out both",
        "fade-in":    "fade-in 0.18s ease-out both",
        "scale-in":   "scale-in 0.2s ease-out both",
        "slide-down": "slide-down 0.18s ease-out both",
      },
    },
  },
  plugins: [],
}
