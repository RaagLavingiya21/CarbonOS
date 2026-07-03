import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1320px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        "border-strong": "hsl(var(--border-strong))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        // Layered surfaces (Linear/Stripe-style depth).
        surface: "hsl(var(--surface))",
        "surface-2": "hsl(var(--surface-2))",
        elevated: "hsl(var(--elevated))",
        subtle: "hsl(var(--subtle))",
        // State semantics (kept in sync with the data palette via CSS vars).
        success: "hsl(var(--success))",
        "success-bg": "hsl(var(--success-bg))",
        warning: "hsl(var(--warning))",
        "warning-bg": "hsl(var(--warning-bg))",
        info: "hsl(var(--info))",
        "info-bg": "hsl(var(--info-bg))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Semantic data palette — emission tiers + states.
        data: {
          low: "hsl(var(--data-low))",
          "low-bg": "hsl(var(--data-low-bg))",
          medium: "hsl(var(--data-medium))",
          "medium-bg": "hsl(var(--data-medium-bg))",
          high: "hsl(var(--data-high))",
          "high-bg": "hsl(var(--data-high-bg))",
          neutral: "hsl(var(--data-neutral))",
          "neutral-bg": "hsl(var(--data-neutral-bg))",
          info: "hsl(var(--data-info))",
          "info-bg": "hsl(var(--data-info-bg))",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        serif: ["var(--font-serif)"],
        mono: ["var(--font-mono)"],
        display: ["var(--font-display)"],
      },
      fontSize: {
        // Compact, data-dense type scale (size / line-height / tracking).
        caption: ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.01em" }],
        small: ["0.75rem", { lineHeight: "1.1rem" }],
        body: ["0.8125rem", { lineHeight: "1.45" }],
        "body-lg": ["0.875rem", { lineHeight: "1.55" }],
        h3: ["0.9375rem", { lineHeight: "1.35", letterSpacing: "-0.01em" }],
        h2: ["1.125rem", { lineHeight: "1.3", letterSpacing: "-0.015em" }],
        h1: ["1.375rem", { lineHeight: "1.2", letterSpacing: "-0.02em" }],
        display: ["1.75rem", { lineHeight: "1.15", letterSpacing: "-0.025em" }],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        xs: "var(--shadow-xs)",
        overlay: "var(--shadow-overlay)",
      },
      transitionTimingFunction: {
        out: "var(--ease-out)",
        "in-out": "var(--ease-in-out)",
      },
      transitionDuration: {
        micro: "120ms",
        DEFAULT: "200ms",
        panel: "320ms",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms var(--ease-out)",
        "slide-up": "slide-up 240ms var(--ease-out)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
export default config;
