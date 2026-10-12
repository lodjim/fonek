"use client";

import { useState, useSyncExternalStore } from "react";
import Link from "next/link";
import useSWR from "swr";
import { ArrowLeft, Play, Trash2 } from "lucide-react";

import { CopyRow } from "@/components/key-info";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, fetcher, type ApiKey } from "@/lib/api";
import { cn } from "@/lib/utils";

const PATH = "/api/public/locations";

const EXAMPLE_RESPONSE = `[
  {
    "device_id": 1,
    "name": "Bike",
    "timestamp": "2026-10-05T09:12:44Z",
    "lat": 48.8566,
    "lon": 2.3522,
    "accuracy": 25,
    "confidence": 2,
    "status": 0
  }
]`;

const FIELDS = [
  ["device_id", "integer", "Stable id of the device"],
  ["name", "string", "Device name as shown in the dashboard"],
  ["timestamp", "string", "When the device was seen, ISO-8601 in UTC"],
  ["lat, lon", "number", "Position in decimal degrees (WGS 84)"],
  ["accuracy", "integer | null", "Horizontal accuracy in metres"],
  ["confidence, status", "integer | null", "Passed through from the Find My report"],
];

const ERRORS = [
  ["401", "The key is missing, wrong or revoked"],
  ["429", "Rate limit reached. Wait the number of seconds given in the Retry-After header"],
];

type Result = {
  status: number;
  ms: number;
  limit: string | null;
  remaining: string | null;
  retryAfter: string | null;
  body: string;
};

export function Settings() {
  const origin = useSyncExternalStore(
    () => () => {},
    () => window.location.origin,
    () => "",
  );
  const [name, setName] = useState("");
  const [limit, setLimit] = useState("60");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<(ApiKey & { key: string }) | null>(null);
  const [tryKey, setTryKey] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  const keys = useSWR<ApiKey[]>("/api/keys", fetcher);
  const shownKey = tryKey.trim() || "YOUR_API_KEY";
  const url = `${origin}${PATH}`;

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await keys.mutate();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    run(async () => {
      const key = await api<ApiKey & { key: string }>("/api/keys", {
        method: "POST",
        body: JSON.stringify({ name: name.trim(), rate_limit_per_min: Number(limit) }),
      });
      setCreated(key);
      setTryKey(key.key);
      setName("");
    });
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const started = performance.now();
    try {
      const res = await fetch(PATH, { headers: { Authorization: `Bearer ${tryKey.trim()}` } });
      const text = await res.text();
      let body = text;
      try {
        body = JSON.stringify(JSON.parse(text), null, 2);
      } catch {}
      setResult({
        status: res.status,
        ms: Math.round(performance.now() - started),
        limit: res.headers.get("X-RateLimit-Limit"),
        remaining: res.headers.get("X-RateLimit-Remaining"),
        retryAfter: res.headers.get("Retry-After"),
        body,
      });
      keys.mutate();
    } catch (err) {
      setResult({ status: 0, ms: 0, limit: null, remaining: null, retryAfter: null, body: (err as Error).message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-10 px-4 py-8">
      <header className="space-y-3">
        <Link href="/" className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-2.5")}>
          <ArrowLeft /> Map
        </Link>
        <h1 className="text-2xl font-semibold">Settings</h1>
      </header>

      <Section
        title="API keys"
        intro="A key lets a third party read the latest location of your devices, and nothing else. Each key has its own rate limit and can be revoked at any time."
      >
        {created && (
          <div className="min-w-0 space-y-1 rounded-md border border-amber-500/40 bg-amber-500/10 p-3">
            <CopyRow label={`Key for ${created.name}`} value={created.key} />
            <p className="text-xs text-muted-foreground">
              Copy it now. It is not stored and cannot be shown again.
            </p>
          </div>
        )}

        <ul className="divide-y rounded-md border">
          {keys.data?.length === 0 && (
            <li className="px-3 py-4 text-center text-xs text-muted-foreground">
              No API keys yet.
            </li>
          )}
          {keys.data?.map((k) => (
            <li key={k.id} className="flex items-center gap-2 px-3 py-2">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{k.name}</span>
                <span className="block text-xs text-muted-foreground">
                  <code>{k.prefix}…</code> · {k.rate_limit_per_min} requests/min ·{" "}
                  {k.last_used_at
                    ? `last used ${new Date(k.last_used_at).toLocaleString()}`
                    : "never used"}
                </span>
              </span>
              <Button
                size="icon-sm"
                variant="ghost"
                aria-label={`Revoke ${k.name}`}
                disabled={busy}
                onClick={() =>
                  run(async () => {
                    await api(`/api/keys/${k.id}`, { method: "DELETE" });
                    if (created?.id === k.id) setCreated(null);
                  })
                }
              >
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>

        <form onSubmit={submit} className="flex items-end gap-2">
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label htmlFor="key-name">New key name</Label>
            <Input
              id="key-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Who is it for?"
              maxLength={64}
              required
            />
          </div>
          <div className="w-28 space-y-1.5">
            <Label htmlFor="key-limit">Requests/min</Label>
            <Input
              id="key-limit"
              type="number"
              min={1}
              max={6000}
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={busy || !name.trim()}>
            Generate
          </Button>
        </form>
        {(error ?? keys.error) && (
          <p className="text-sm text-destructive">{error ?? keys.error.message}</p>
        )}
      </Section>

      <Section
        title="Playground"
        intro="Send a real request with a key and see exactly what the third party will get. Each request counts against that key's rate limit."
      >
        <form onSubmit={send} className="flex items-end gap-2">
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label htmlFor="try-key">API key</Label>
            <Input
              id="try-key"
              value={tryKey}
              onChange={(e) => setTryKey(e.target.value)}
              placeholder="fonek_…"
              className="font-mono text-xs"
              autoComplete="off"
            />
          </div>
          <Button type="submit" disabled={busy}>
            <Play /> Send
          </Button>
        </form>
        <p className="font-mono text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">GET</span> {url}
        </p>
        {result && (
          <div className="space-y-2" aria-live="polite">
            <p className="text-xs text-muted-foreground">
              <span
                className={cn(
                  "mr-2 rounded px-1.5 py-0.5 font-mono font-semibold",
                  result.status >= 200 && result.status < 300
                    ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                    : "bg-destructive/10 text-destructive",
                )}
              >
                {result.status || "Failed"}
              </span>
              {result.ms} ms
              {result.limit && ` · ${result.remaining} of ${result.limit} requests left this minute`}
              {result.retryAfter && ` · retry in ${result.retryAfter} s`}
            </p>
            <Code>{result.body}</Code>
          </div>
        )}
      </Section>

      <Section
        title="Documentation"
        intro="Everything a third party needs. The examples use the key typed in the playground."
      >
        <h3 className="text-sm font-medium">Request</h3>
        <p className="text-sm text-muted-foreground">
          One endpoint, read-only. Send the key as a bearer token in the{" "}
          <code>Authorization</code> header.
        </p>
        <CopyRow label="curl" value={`curl -H "Authorization: Bearer ${shownKey}" ${url}`} />
        <div className="space-y-1">
          <div className="text-xs font-medium text-muted-foreground">JavaScript</div>
          <Code>{`const res = await fetch("${url}", {
  headers: { Authorization: "Bearer ${shownKey}" },
});
const locations = await res.json();`}</Code>
        </div>
        <div className="space-y-1">
          <div className="text-xs font-medium text-muted-foreground">Python</div>
          <Code>{`import requests

res = requests.get("${url}", headers={"Authorization": "Bearer ${shownKey}"})
locations = res.json()`}</Code>
        </div>

        <h3 className="pt-2 text-sm font-medium">Response</h3>
        <p className="text-sm text-muted-foreground">
          <code>200</code> with the most recent known location of every device that has one.
          Positions come from the Find My network, so a location is as fresh as the last time an
          iPhone passed near the beacon.
        </p>
        <Code>{EXAMPLE_RESPONSE}</Code>
        <Table head={["Field", "Type", "Meaning"]} rows={FIELDS} />

        <h3 className="pt-2 text-sm font-medium">Rate limit</h3>
        <p className="text-sm text-muted-foreground">
          Each key has its own limit, counted per clock minute. Every response carries{" "}
          <code>X-RateLimit-Limit</code> and <code>X-RateLimit-Remaining</code>.
        </p>

        <h3 className="pt-2 text-sm font-medium">Errors</h3>
        <p className="text-sm text-muted-foreground">
          Errors are JSON: <code>{`{"detail": "message"}`}</code>.
        </p>
        <Table head={["Status", "Meaning"]} rows={ERRORS} />
      </Section>
    </div>
  );
}

function Section({
  title,
  intro,
  children,
}: {
  title: string;
  intro: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="space-y-1 border-b pb-2">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{intro}</p>
      </div>
      {children}
    </section>
  );
}

function Code({ children }: { children: string }) {
  return (
    <pre className="max-h-96 overflow-auto rounded-md bg-muted px-3 py-2 font-mono text-xs">
      {children}
    </pre>
  );
}

function Table({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="w-full text-left text-xs">
        <thead className="bg-muted/50 text-muted-foreground">
          <tr>
            {head.map((h) => (
              <th key={h} className="px-3 py-1.5 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((row) => (
            <tr key={row[0]}>
              {row.map((cell, i) => (
                <td key={i} className={cn("px-3 py-1.5", i === 0 && "font-mono whitespace-nowrap")}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
