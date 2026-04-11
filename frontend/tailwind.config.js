/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        corp: {
          navy: "#0B1F3A",
          gold: "#C9A84C",
          border: "#E5E7EB",
          muted: "#6B7280",
          surface: "#F9FAFB",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
