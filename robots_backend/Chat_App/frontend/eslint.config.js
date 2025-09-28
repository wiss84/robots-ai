// Flat config for ESLint with TypeScript support
// Requires: eslint, typescript, @typescript-eslint/parser, @typescript-eslint/eslint-plugin
import js from "@eslint/js";
import ts from "typescript-eslint";

export default [
  js.configs.recommended,
  ...ts.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx,js,jsx}"],
    rules: {
      // Prefer TS compiler's unused checks
      "no-unused-vars": "off"
    }
  }
];
