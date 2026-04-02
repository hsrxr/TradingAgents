/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Space Grotesk", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      backgroundImage: {
        matrix:
          "radial-gradient(circle at 20% 0%, rgba(16, 185, 129, 0.18) 0%, rgba(0, 0, 0, 0) 40%), radial-gradient(circle at 95% 10%, rgba(6, 95, 70, 0.28) 0%, rgba(0, 0, 0, 0) 35%), linear-gradient(180deg, #040808 0%, #020404 100%)",
      },
      keyframes: {
        riseIn: {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        riseIn: "riseIn 0.5s ease-out forwards",
      },
    },
  },
  plugins: [],
}

