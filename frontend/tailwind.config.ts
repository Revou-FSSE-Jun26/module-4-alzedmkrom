const config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Design tokens (.kiro/design-visual/design.html). The values are CSS variables in globals.css,
        // so light and dark share the same class names (FE-UX-04).
        bg: "var(--bg)",
        surface: "var(--surface)",
        line: "var(--line)",
        ink: "var(--ink)",
        mute: "var(--mute)",
        brand: {
          50: "#eff6ff",
          100: "#dbeafe",
          300: "#93c5fd",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
        },
        badge: {
          gray: { bg: "#f3f4f6", text: "#374151" },
          blue: { bg: "#dbeafe", text: "#1e40af" },
          green: { bg: "#dcfce7", text: "#166534" },
          yellow: { bg: "#fef9c3", text: "#854d0e" },
          red: { bg: "#fee2e2", text: "#991b1b" },
        },
        button: {
          primary: { bg: "#2563eb", hover: "#1d4ed8", text: "#ffffff" },
          secondary: { bg: "#ffffff", hover: "#f3f4f6", text: "#374151" },
          destructive: { bg: "#dc2626", hover: "#b91c1c", text: "#ffffff" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
