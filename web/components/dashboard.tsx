"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import useSWR from "swr";
import { KeyRound, MapPin, RefreshCw, Settings, Trash2, TriangleAlert } from "lucide-react";

import { AddDeviceDialog } from "@/components/add-device-dialog";
import { KeyInfo } from "@/components/key-info";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, fetcher, timeAgo, type Device, type Location, type Status } from "@/lib/api";
import { cn } from "@/lib/utils";

const MapView = dynamic(() => import("@/components/map-view"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse bg-muted" />,
});

const RANGES = [
  { id: "24h", label: "24 h", hours: 24 },
  { id: "7d", label: "7 d", hours: 24 * 7 },
  { id: "30d", label: "30 d", hours: 24 * 30 },
  { id: "all", label: "All", hours: null },
] as const;
type RangeId = (typeof RANGES)[number]["id"];

const REFRESH_MS = 60_000;

function useNow(intervalMs: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

function sinceFor(range: RangeId): string | null {
  const hours = RANGES.find((r) => r.id === range)!.hours;
  return hours == null ? null : new Date(Date.now() - hours * 3600_000).toISOString();
}

export function Dashboard() {
  const now = useNow(30_000);
  // `since` is fixed when the device/range is chosen so the history request key stays stable.
  const [view, setView] = useState<{ id: number | null; range: RangeId; since: string | null }>({
    id: null,
    range: "7d",
    since: null,
  });
  const [keyDevice, setKeyDevice] = useState<Device | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const status = useSWR<Status>("/api/status", fetcher, { refreshInterval: REFRESH_MS });
  const devices = useSWR<Device[]>("/api/devices", fetcher, { refreshInterval: REFRESH_MS });
  const latest = useSWR<Location[]>("/api/locations/latest", fetcher, {
    refreshInterval: REFRESH_MS,
  });
  const historyKey =
    view.id == null
      ? null
      : `/api/devices/${view.id}/locations${view.since ? `?since=${encodeURIComponent(view.since)}` : ""}`;
  const history = useSWR<Location[]>(historyKey, fetcher, {
    refreshInterval: REFRESH_MS,
    keepPreviousData: false,
  });

  const latestById = new Map((latest.data ?? []).map((l) => [l.device_id, l]));
  const loadError = devices.error ?? status.error;

  function select(id: number | null, range: RangeId = view.range) {
    setView({ id, range, since: sinceFor(range) });
    setConfirmDelete(null);
  }

  async function refresh(device: Device) {
    setRefreshing(device.id);
    setActionError(null);
    try {
      await api(`/api/devices/${device.id}/refresh`, { method: "POST" });
      await Promise.all([latest.mutate(), devices.mutate(), history.mutate(), status.mutate()]);
    } catch (err) {
      setActionError((err as Error).message);
    } finally {
      setRefreshing(null);
    }
  }

  async function remove(device: Device) {
    setActionError(null);
    try {
      await api(`/api/devices/${device.id}`, { method: "DELETE" });
      if (view.id === device.id) select(null);
      setConfirmDelete(null);
      await Promise.all([devices.mutate(), latest.mutate()]);
    } catch (err) {
      setActionError((err as Error).message);
    }
  }

  return (
    <div className="flex h-dvh flex-col md:flex-row">
      <aside className="flex max-h-[45dvh] w-full shrink-0 flex-col border-b md:max-h-none md:w-80 md:border-r md:border-b-0">
        <header className="flex items-center justify-between gap-2 border-b px-4 py-3">
          <div className="flex items-center gap-2 font-semibold">
            <MapPin className="size-4" /> fonek
          </div>
          <div className="flex items-center gap-1">
            <Link
              href="/settings"
              aria-label="Settings"
              className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
            >
              <Settings />
            </Link>
            <AddDeviceDialog
              onCreated={(device) => {
                devices.mutate();
                select(device.id);
              }}
            />
          </div>
        </header>

        {loadError ? (
          <Notice tone="error">Can&apos;t reach the backend: {loadError.message}</Notice>
        ) : status.data?.apple === "needs_login" ? (
          <Notice tone="warn">
            Apple login required. Run:
            <code className="mt-1 block rounded bg-background/60 px-1.5 py-1 font-mono text-[11px] break-words">
              docker compose run --rm backend python -m app.cli login
            </code>
          </Notice>
        ) : status.data?.last_error ? (
          <Notice tone="error">Last fetch failed: {status.data.last_error}</Notice>
        ) : null}
        {actionError && <Notice tone="error">{actionError}</Notice>}

        <ul className="min-h-0 flex-1 overflow-y-auto">
          {devices.data?.length === 0 && (
            <li className="px-4 py-8 text-center text-sm text-muted-foreground">
              No devices yet. Add one to get a key to flash onto your ESP32.
            </li>
          )}
          {devices.data?.map((device) => {
            const loc = latestById.get(device.id);
            const active = device.id === view.id;
            return (
              <li key={device.id} className={cn("border-b", active && "bg-muted")}>
                <button
                  type="button"
                  onClick={() => select(active ? null : device.id)}
                  aria-pressed={active}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/60"
                >
                  <span
                    className="size-3 shrink-0 rounded-full"
                    style={{ backgroundColor: device.color }}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{device.name}</span>
                    <span className="block text-xs text-muted-foreground">
                      {loc ? `Seen ${timeAgo(loc.timestamp, now)}` : "No location yet"}
                    </span>
                  </span>
                </button>

                {active && (
                  <div className="space-y-2 px-4 pb-3">
                    <div className="flex gap-1" role="group" aria-label="History range">
                      {RANGES.map((r) => (
                        <Button
                          key={r.id}
                          size="xs"
                          variant={r.id === view.range ? "default" : "outline"}
                          className="flex-1"
                          onClick={() => select(device.id, r.id)}
                        >
                          {r.label}
                        </Button>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {history.error
                        ? "Could not load history."
                        : history.data
                          ? `${history.data.length} point${history.data.length === 1 ? "" : "s"} in range`
                          : "Loading history…"}
                      {device.last_polled_at &&
                        ` · checked ${timeAgo(device.last_polled_at, now)}`}
                    </p>
                    <div className="flex gap-1">
                      <Button
                        size="xs"
                        variant="outline"
                        disabled={refreshing === device.id}
                        onClick={() => refresh(device)}
                      >
                        <RefreshCw className={cn(refreshing === device.id && "animate-spin")} />
                        Refresh
                      </Button>
                      <Button size="xs" variant="outline" onClick={() => setKeyDevice(device)}>
                        <KeyRound /> Key
                      </Button>
                      {confirmDelete === device.id ? (
                        <Button size="xs" variant="destructive" onClick={() => remove(device)}>
                          Delete device and history?
                        </Button>
                      ) : (
                        <Button
                          size="xs"
                          variant="ghost"
                          aria-label={`Delete ${device.name}`}
                          onClick={() => setConfirmDelete(device.id)}
                        >
                          <Trash2 />
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        {status.data && (
          <footer className="border-t px-4 py-2 text-xs text-muted-foreground">
            {status.data.account ? `${status.data.account} · ` : ""}
            {status.data.last_poll_at
              ? `Last fetch ${timeAgo(status.data.last_poll_at, now)}`
              : "Not fetched yet"}
            {` · every ${status.data.poll_interval_min} min`}
          </footer>
        )}
      </aside>

      <main className="relative z-0 min-h-0 flex-1">
        <MapView
          devices={devices.data ?? []}
          latest={latest.data ?? []}
          selectedId={view.id}
          history={history.data}
          viewKey={`${view.id}-${view.range}`}
          onSelect={(id) => select(id)}
        />
      </main>

      <Dialog open={keyDevice != null} onOpenChange={(open) => !open && setKeyDevice(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{keyDevice?.name}</DialogTitle>
            <DialogDescription>Key to flash onto the beacon.</DialogDescription>
          </DialogHeader>
          {keyDevice && <KeyInfo advKey={keyDevice.adv_key_b64} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Notice({ tone, children }: { tone: "warn" | "error"; children: React.ReactNode }) {
  return (
    <div
      role="status"
      className={cn(
        "flex gap-2 border-b px-4 py-2.5 text-xs",
        tone === "warn"
          ? "bg-amber-500/10 text-amber-900 dark:text-amber-200"
          : "bg-destructive/10 text-destructive",
      )}
    >
      <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
