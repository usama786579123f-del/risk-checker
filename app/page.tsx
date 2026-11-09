import fs from "node:fs";
import path from "node:path";
import Checker from "@/components/Checker";
import type { Company, Status } from "@/lib/risk";

function readJson<T>(name: string, fallback: T): T {
  try {
    return JSON.parse(fs.readFileSync(path.join(process.cwd(), "public", "data", name), "utf8")) as T;
  } catch {
    return fallback;
  }
}

export default function Page() {
  const companies = readJson<Company[]>("companies.json", []);
  const status = readJson<Status | null>("status.json", null);
  return <Checker companies={companies} status={status} />;
}
