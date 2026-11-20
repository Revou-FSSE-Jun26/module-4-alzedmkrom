export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
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
