import type { Config } from "tailwindcss";

// Palette: "kagaz" paper, indigo ink, saffron + turmeric accents, deep India-green for safe, sindoor red for scam.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: { DEFAULT: "#FBF5E9", 2: "#F3EAD7", card: "#FFFDF8" },
        ink: { DEFAULT: "#1A1633", soft: "#4A4566", faint: "#8A85A3" },
        line: { DEFAULT: "#E4D8BF", strong: "#CDBF9F" },
        saffron: { DEFAULT: "#E8761A", deep: "#C25A08", wash: "#FDEBD6" },
        turmeric: { DEFAULT: "#F2B21B", wash: "#FDF1CF" },
        tiranga: "#138808",
        safe: { DEFAULT: "#0F7B3E", wash: "#DDF3E4" },
        warn: { DEFAULT: "#D9570F", wash: "#FDE6D8" },
        scam: { DEFAULT: "#B3261E", wash: "#FADDD9" },
        chakra: "#1F3A93",
      },
      fontFamily: {
        display: ['"Fraunces Variable"', '"Tiro Devanagari Hindi"', "Georgia", "serif"],
        hindi: ['"Tiro Devanagari Hindi"', "Georgia", "serif"],
        sans: ["Hind", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        mono: ['"DM Mono"', "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 rgba(26,22,51,.04), 0 10px 30px -12px rgba(26,22,51,.18)",
        lift: "0 2px 0 rgba(26,22,51,.05), 0 18px 40px -14px rgba(26,22,51,.28)",
      },
    },
  },
  plugins: [],
};
export default config;
