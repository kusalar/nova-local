/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        nova: {
          dark: "#02060e",
          midnight: "#040c1c",
          surface: "rgba(6, 17, 34, 0.75)",
          surfaceLight: "rgba(12, 28, 54, 0.65)",
          cyan: "#00f0ff",
          cyanDim: "#00b4cc",
          electric: "#0077ff",
          teal: "#00e5c0",
          amber: "#f59e0b",
          purple: "#9d4edd",
          emerald: "#10b981",
          crimson: "#ff3366",
          border: "rgba(0, 240, 255, 0.18)",
          borderHover: "rgba(0, 240, 255, 0.45)",
          textDim: "#64748b",
          textLight: "#94a3b8",
          textBright: "#f8fafc"
        }
      },
      fontFamily: {
        sans: ["Rajdhani", "Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        display: ["Orbitron", "Rajdhani", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "Courier New", "monospace"]
      },
      boxShadow: {
        'nova-cyan': '0 0 15px rgba(0, 240, 255, 0.35)',
        'nova-cyan-lg': '0 0 30px rgba(0, 240, 255, 0.55)',
        'nova-blue': '0 0 20px rgba(0, 119, 255, 0.4)',
        'nova-orb': '0 0 50px rgba(0, 240, 255, 0.6), inset 0 0 30px rgba(0, 240, 255, 0.4)',
        'nova-panel': '0 8px 32px 0 rgba(0, 0, 0, 0.65)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 24s linear infinite',
        'spin-reverse-slow': 'spin-reverse 30s linear infinite',
        'wave': 'wave 1.2s ease-in-out infinite',
      },
      keyframes: {
        'spin-reverse': {
          from: { transform: 'rotate(360deg)' },
          to: { transform: 'rotate(0deg)' }
        },
        wave: {
          '0%, 100%': { height: '6px' },
          '50%': { height: '24px' }
        }
      }
    },
  },
  plugins: [],
}
