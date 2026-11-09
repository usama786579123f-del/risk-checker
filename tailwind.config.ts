import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#4F46E5",
          dark: "#3730A3",
          soft: "#EEF0FF",
          mist: "#F6F7FF",
        },
        ink: {
          DEFAULT: "#14143A",
          muted: "#5B5F7A",
        },
      },
      boxShadow: {
        card: "0 8px 30px -12px rgba(79,70,229,0.18)",
        float: "0 20px 50px -18px rgba(20,20,58,0.28)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
