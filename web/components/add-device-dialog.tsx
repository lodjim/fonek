"use client";

import { useState } from "react";
import { Plus } from "lucide-react";

import { KeyInfo } from "@/components/key-info";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type Device } from "@/lib/api";

const COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"];

export function AddDeviceDialog({ onCreated }: { onCreated: (device: Device) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [color, setColor] = useState(COLORS[0]);
  const [privateKey, setPrivateKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [created, setCreated] = useState<Device | null>(null);

  function reset() {
    setName("");
    setColor(COLORS[0]);
    setPrivateKey("");
    setError(null);
    setCreated(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const device = await api<Device>("/api/devices", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          color,
          private_key_b64: privateKey.trim() || null,
        }),
      });
      setCreated(device);
      onCreated(device);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button
        size="sm"
        onClick={() => {
          reset();
          setOpen(true);
        }}
      >
        <Plus /> Add device
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          {created ? (
            <>
              <DialogHeader>
                <DialogTitle>{created.name} is ready to flash</DialogTitle>
                <DialogDescription>
                  Flash this key onto the ESP32. You can find it again later from the device list.
                </DialogDescription>
              </DialogHeader>
              <KeyInfo advKey={created.adv_key_b64} />
              <DialogFooter>
                <Button onClick={() => setOpen(false)}>Done</Button>
              </DialogFooter>
            </>
          ) : (
            <form onSubmit={submit} className="contents">
              <DialogHeader>
                <DialogTitle>Add device</DialogTitle>
                <DialogDescription>
                  A new Find My key pair is generated for the beacon.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="device-name">Name</Label>
                  <Input
                    id="device-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Bike, backpack…"
                    maxLength={64}
                    required
                    autoFocus
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Colour</Label>
                  <div className="flex gap-2">
                    {COLORS.map((c) => (
                      <button
                        key={c}
                        type="button"
                        aria-label={`Colour ${c}`}
                        aria-pressed={c === color}
                        onClick={() => setColor(c)}
                        className="size-6 rounded-full ring-offset-2 ring-offset-background aria-pressed:ring-2 aria-pressed:ring-foreground"
                        style={{ backgroundColor: c }}
                      />
                    ))}
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="device-key">Existing private key (optional)</Label>
                  <Input
                    id="device-key"
                    value={privateKey}
                    onChange={(e) => setPrivateKey(e.target.value)}
                    placeholder="Base64 — leave empty to generate"
                    className="font-mono text-xs"
                  />
                </div>
                {error && <p className="text-sm text-destructive">{error}</p>}
              </div>
              <DialogFooter>
                <Button type="submit" disabled={busy || !name.trim()}>
                  {busy ? "Creating…" : "Create"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
