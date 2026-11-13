/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        space: {
          950: "#05070a", // Deep cosmic void
          900: "#090d14", // Panel background
          850: "#0e1420", // Card surface background
          800: "#141d2e", // Elevated card / border
          700: "#1e2b42", // Structural borders
          600: "#2d3e5e", // Muted borders
          400: "#64748b", // Secondary typography
          200: "#94a3b8", // Primary typography muted
          100: "#f1f5f9", // Crisp primary text
        },
        telemetry: {
          nominal: "#2ecc71",   // Stress < 35%
          mild: "#f1c40f",      // Stress 35-55%
          elevated: "#e67e22",  // Stress 55-75%
          critical: "#e74c3c",  // Stress > 75%
        },
        emotion: {
          happy: "#ffd600",
          neutral: "#94a3b8",
          surprise: "#00e5ff",
          sad: "#2979ff",
          fear: "#d500f9",
          angry: "#e74c3c",
          disgust: "#2ecc71",
        }
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        "glow-nominal": "0 0 15px -3px rgba(46, 204, 113, 0.45)",
        "glow-mild": "0 0 15px -3px rgba(241, 196, 15, 0.45)",
        "glow-elevated": "0 0 15px -3px rgba(230, 126, 34, 0.45)",
        "glow-critical": "0 0 20px -2px rgba(231, 76, 60, 0.65)",
        "glass-panel": "inset 0 1px 1px 0 rgba(255, 255, 255, 0.08), 0 8px 32px 0 rgba(0, 0, 0, 0.45)",
      }
    },
  },
  plugins: [],
}
