import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#2C3E50", dark: "#34495E" },
        accent: { sage: "#A8C8B0", beige: "#F5E6D3" },
      },
    },
  },
  plugins: [],
};
export default config;
