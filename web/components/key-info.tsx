"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import { flashCommand } from "@/lib/api";

function CopyRow({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="min-w-0 space-y-1">
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
      <div className="flex items-center gap-2">
        <code className="min-w-0 flex-1 overflow-x-auto rounded-md bg-muted px-2 py-1.5 font-mono text-xs whitespace-nowrap">
          {value}
        </code>
        <Button
          variant="outline"
          size="icon-sm"
          aria-label={`Copy ${label.toLowerCase()}`}
          onClick={async () => {
            await navigator.clipboard?.writeText(value);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? <Check /> : <Copy />}
        </Button>
      </div>
    </div>
  );
}

export function KeyInfo({ advKey }: { advKey: string }) {
  return (
    <div className="min-w-0 space-y-3">
      <CopyRow label="Advertisement key" value={advKey} />
      <CopyRow label="Flash command (OpenHaystack ESP32 firmware)" value={flashCommand(advKey)} />
      <p className="text-xs text-muted-foreground">
        See <code>firmware/README.md</code> for the full flashing steps. Locations appear once an
        iPhone has passed near the beacon, usually within minutes to hours.
      </p>
    </div>
  );
}
