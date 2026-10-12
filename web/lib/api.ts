export type Device = {
  id: number;
  name: string;
  color: string;
  adv_key_b64: string;
  created_at: string;
  last_polled_at: string | null;
};

export type Location = {
  device_id: number;
  timestamp: string;
  lat: number;
  lon: number;
  accuracy: number | null;
  confidence: number | null;
  status: number | null;
};

export type Status = {
  apple: "ok" | "needs_login";
  account: string | null;
  last_poll_at: string | null;
  last_error: string | null;
  poll_interval_min: number;
};

export type ApiKey = {
  id: number;
  name: string;
  prefix: string;
  rate_limit_per_min: number;
  created_at: string;
  last_used_at: string | null;
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail;
    throw new Error(
      typeof detail === "string" ? detail : `Request failed (${res.status})`,
    );
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const fetcher = <T,>(path: string) => api<T>(path);

export function timeAgo(iso: string, now: number): string {
  const s = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

export const flashCommand = (advKey: string) =>
  `./flash_esp32.sh -p /dev/ttyUSB0 "${advKey}"`;
