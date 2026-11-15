import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

// Tokens do tema da Horizonte Digital (as cores ficam em src/index.css, em HSL)
const hsl = (v: string) => `hsl(var(--${v}))`;

export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.5rem", screens: { "2xl": "1280px" } },
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "Inter", "sans-serif"],
      },
      colors: {
        border: hsl("border"), input: hsl("input"), ring: hsl("ring"),
        background: hsl("background"), foreground: hsl("foreground"),
        hairline: hsl("hairline"), graphite: { DEFAULT: hsl("graphite"), soft: hsl("graphite-soft") },
        primary: { DEFAULT: hsl("primary"), foreground: hsl("primary-foreground"), glow: hsl("primary-glow"), deep: hsl("primary-deep") },
        secondary: { DEFAULT: hsl("secondary"), foreground: hsl("secondary-foreground") },
        destructive: { DEFAULT: hsl("destructive"), foreground: hsl("destructive-foreground") },
        muted: { DEFAULT: hsl("muted"), foreground: hsl("muted-foreground") },
        accent: { DEFAULT: hsl("accent"), foreground: hsl("accent-foreground") },
        popover: { DEFAULT: hsl("popover"), foreground: hsl("popover-foreground") },
        card: { DEFAULT: hsl("card"), foreground: hsl("card-foreground") },
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
      boxShadow: { ember: "var(--shadow-ember)", elevated: "var(--shadow-elevated)", "glow-sm": "var(--shadow-glow-sm)" },
      backgroundImage: { "gradient-ember": "var(--gradient-ember)", "gradient-card": "var(--gradient-card)" },
    },
  },
  plugins: [animate],
} satisfies Config;
