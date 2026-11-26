import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

// CI-style checks for FE-UX-03 (text sizes) and FE-UI-01 (BaseButton). Each rule names the only
// files where the pattern may appear.

// `npm test` runs from frontend/, so the working directory is the frontend root.
const FRONTEND_ROOT = process.cwd();
const SOURCE_DIRS = ["app", "components", "hooks", "lib", "context"];

function sourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      out.push(...sourceFiles(full));
    } else if (/\.(ts|tsx)$/.test(entry) && !/\.test\.(ts|tsx)$/.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

const files = SOURCE_DIRS.flatMap((dir) => sourceFiles(join(FRONTEND_ROOT, dir)));

function offenders(pattern: RegExp, allowed: readonly string[]): string[] {
  const hits: string[] = [];
  for (const file of files) {
    const rel = relative(FRONTEND_ROOT, file).split(sep).join("/");
    if (allowed.includes(rel)) {
      continue;
    }
    const lines = readFileSync(file, "utf8").split("\n");
    lines.forEach((line, index) => {
      if (pattern.test(line)) {
        hits.push(`${rel}:${index + 1}`);
      }
    });
  }
  return hits;
}

describe("FE-UX-03 text sizes", () => {
  it("uses text-xs only for the notification count badge", () => {
    expect(offenders(/\btext-xs\b/, ["components/layout/NotificationBell.tsx"])).toEqual([]);
  });

  it("uses no arbitrary text size below 14px", () => {
    const small = /text-\[(\d+(?:\.\d+)?)px\]/;
    const bad = files.flatMap((file) => {
      const rel = relative(FRONTEND_ROOT, file).split(sep).join("/");
      return readFileSync(file, "utf8")
        .split("\n")
        .map((line, index) => ({ line, index }))
        .filter(({ line }) => {
          const match = small.exec(line);
          return match !== null && Number(match[1]) < 14;
        })
        .map(({ index }) => `${rel}:${index + 1}`);
    });
    expect(bad).toEqual([]);
  });
});

describe("FE-UI-01 BaseButton", () => {
  it("renders no raw <button> outside BaseButton.tsx", () => {
    expect(offenders(/<button[\s>]/, ["components/shared/BaseButton.tsx"])).toEqual([]);
  });
});
