"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import {
  Circle,
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";

import type { Device, Location } from "@/lib/api";

type Props = {
  devices: Device[];
  latest: Location[];
  selectedId: number | null;
  history: Location[] | undefined;
  // Changes whenever the view should be re-centred (device or time range switched).
  viewKey: string;
  onSelect: (id: number) => void;
};

const formatTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

/** Fits the map to `points` once per `viewKey`, so background refreshes don't move the view. */
function FitView({ points, viewKey }: { points: Location[] | undefined; viewKey: string }) {
  const map = useMap();
  const fitted = useRef<string | null>(null);

  useEffect(() => {
    if (!points?.length || fitted.current === viewKey) return;
    fitted.current = viewKey;
    map.fitBounds(L.latLngBounds(points.map((p) => [p.lat, p.lon])), {
      padding: [48, 48],
      maxZoom: 16,
    });
  }, [map, points, viewKey]);

  return null;
}

export default function MapView({ devices, latest, selectedId, history, viewKey, onSelect }: Props) {
  const selected = devices.find((d) => d.id === selectedId);
  const latestById = new Map(latest.map((l) => [l.device_id, l]));
  const selectedLatest = selectedId != null ? latestById.get(selectedId) : undefined;

  return (
    <MapContainer center={[20, 0]} zoom={2} className="size-full" worldCopyJump>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitView points={selected ? history : latest} viewKey={viewKey} />

      {selected && history && history.length > 0 && (
        <>
          <Polyline
            positions={history.map((p) => [p.lat, p.lon])}
            pathOptions={{ color: selected.color, weight: 3, opacity: 0.6 }}
          />
          {history.map((p) => (
            <CircleMarker
              key={`${p.timestamp}-${p.lat}-${p.lon}`}
              center={[p.lat, p.lon]}
              radius={4}
              pathOptions={{ color: selected.color, weight: 1, fillColor: "#fff", fillOpacity: 1 }}
            >
              <Popup>
                {formatTime(p.timestamp)}
                {p.accuracy != null && <br />}
                {p.accuracy != null && `± ${p.accuracy} m`}
              </Popup>
            </CircleMarker>
          ))}
        </>
      )}

      {selected && selectedLatest?.accuracy != null && (
        <Circle
          center={[selectedLatest.lat, selectedLatest.lon]}
          radius={selectedLatest.accuracy}
          pathOptions={{ color: selected.color, weight: 1, fillOpacity: 0.12 }}
          interactive={false}
        />
      )}

      {devices.map((d) => {
        const loc = latestById.get(d.id);
        if (!loc) return null;
        const active = d.id === selectedId;
        return (
          <CircleMarker
            key={d.id}
            center={[loc.lat, loc.lon]}
            radius={active ? 10 : 8}
            pathOptions={{ color: "#fff", weight: 3, fillColor: d.color, fillOpacity: 1 }}
            eventHandlers={{ click: () => onSelect(d.id) }}
          >
            <Tooltip direction="top" offset={[0, -8]}>
              <strong>{d.name}</strong>
              <br />
              {formatTime(loc.timestamp)}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
