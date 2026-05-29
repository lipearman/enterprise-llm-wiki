import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      animation: {
        float:        "float 6s ease-in-out infinite",
        "float-slow": "floatSlow 9s ease-in-out infinite 1.5s",
        "fade-up":    "fadeUp 0.8s ease-out forwards",
        shimmer:      "shimmer 3s linear infinite",
      },
      keyframes: {
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%":     { transform: "translateY(-18px)" },
        },
        floatSlow: {
          "0%,100%": { transform: "translateY(0) scale(1)" },
          "50%":     { transform: "translateY(-10px) scale(1.02)" },
        },
        fadeUp: {
          from: { opacity: "0", transform: "translateY(28px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% center" },
          "100%": { backgroundPosition: "200% center" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
