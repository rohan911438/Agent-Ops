"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, AlertDescription, Badge, Button, Card, CardContent, CardHeader, CardTitle } from "@agentops/ui";
import type { HealthScan } from "@agentops/shared-types";
import { apiFetch, ApiError } from "@/lib/api-client";

type SourceKind = "file_upload" | "github";

const COMING_SOON = [
  { label: "LangGraph", description: "Discover agents from a LangGraph deployment." },
  { label: "CrewAI", description: "Discover agents from a CrewAI crew definition." },
  { label: "OpenAI Agents SDK", description: "Discover agents registered via the Agents SDK." },
];

async function beginScan(scan: HealthScan): Promise<HealthScan> {
  return apiFetch<HealthScan>(`/scans/${scan.id}/start`, { method: "POST" });
}

export function DataSourcePicker() {
  const router = useRouter();
  const [selected, setSelected] = useState<SourceKind | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) return;
    setSubmitting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const scan = await apiFetch<HealthScan>("/scans/upload", { method: "POST", body: formData });
      await beginScan(scan);
      router.push(`/health-scan/${scan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the scan.");
      setSubmitting(false);
    }
  }

  async function handleGithub() {
    if (!repoUrl.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const scan = await apiFetch<HealthScan>("/scans/github", {
        method: "POST",
        body: JSON.stringify({
          repo_url: repoUrl.trim(),
          github_token: githubToken.trim() || null,
        }),
      });
      await beginScan(scan);
      router.push(`/health-scan/${scan.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start the scan.");
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <button type="button" onClick={() => setSelected("file_upload")} className="text-left">
          <Card className={selected === "file_upload" ? "border-primary" : undefined}>
            <CardHeader>
              <CardTitle className="text-foreground">Upload File</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Upload a JSON or YAML file describing your agents.
            </CardContent>
          </Card>
        </button>
        <button type="button" onClick={() => setSelected("github")} className="text-left">
          <Card className={selected === "github" ? "border-primary" : undefined}>
            <CardHeader>
              <CardTitle className="text-foreground">GitHub Repository</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Point at a repo — we&apos;ll look for known agent-framework dependencies.
            </CardContent>
          </Card>
        </button>
        {COMING_SOON.map((source) => (
          <Card key={source.label} className="opacity-50">
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-foreground">{source.label}</CardTitle>
                <Badge variant="secondary">Coming soon</Badge>
              </div>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{source.description}</CardContent>
          </Card>
        ))}
      </div>

      {selected === "file_upload" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-foreground">Upload agent definitions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <input
              type="file"
              accept=".json,.yaml,.yml"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-sm text-muted-foreground file:mr-4 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-primary-foreground"
            />
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button onClick={handleUpload} disabled={!file || submitting}>
              {submitting ? "Starting scan…" : "Start Health Scan"}
            </Button>
          </CardContent>
        </Card>
      )}

      {selected === "github" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-foreground">Connect a GitHub repository</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-muted-foreground">Repository URL</label>
              <input
                type="text"
                placeholder="https://github.com/owner/repo"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs text-muted-foreground">
                Personal access token (optional — raises the GitHub API rate limit)
              </label>
              <input
                type="password"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button onClick={handleGithub} disabled={!repoUrl.trim() || submitting}>
              {submitting ? "Starting scan…" : "Start Health Scan"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
