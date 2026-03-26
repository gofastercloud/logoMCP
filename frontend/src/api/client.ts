import type { BrandBrief, JobStatus } from "../types";

const BASE = "/api";

export async function submitBrief(brief: BrandBrief): Promise<{ job_id: string }> {
  const res = await fetch(`${BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(brief),
  });
  if (!res.ok) throw new Error(`Submit failed: ${res.status}`);
  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Job fetch failed: ${res.status}`);
  return res.json();
}

export function getAssetUrl(jobId: string, filename: string): string {
  return `${BASE}/jobs/${jobId}/assets/${filename}`;
}

export function getDownloadUrl(jobId: string): string {
  return `${BASE}/jobs/${jobId}/download`;
}

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
