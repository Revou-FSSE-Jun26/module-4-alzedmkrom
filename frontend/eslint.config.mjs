import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/ban-ts-comment": [
        "error",
        {
          "ts-ignore": true,
          "ts-nocheck": true,
        },
      ],
      "react/no-danger": "error",
      "no-alert": "error",
      "no-console": ["error", { allow: ["warn", "info"] }],
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXOpeningElement[name.name='button']",
          message:
            "Use BaseButton from components/shared/BaseButton.tsx instead of a raw <button> element.",
        },
      ],
      "no-restricted-imports": [
        "error",
        {
          name: "react-hot-toast",
          message: "Import toast helpers from lib/toast.ts instead of react-hot-toast.",
        },
      ],
    },
  },
  {
    files: ["components/shared/BaseButton.tsx"],
    rules: {
      "no-restricted-syntax": "off",
    },
  },
  {
    files: ["lib/toast.ts", "app/layout.tsx"],
    rules: {
      "no-restricted-imports": "off",
    },
  },
  globalIgnores([
    ".next/**",
    "node_modules/**",
    "playwright-report/**",
    "test-results/**",
    "coverage/**",
    "next-env.d.ts",
  ]),
]);
