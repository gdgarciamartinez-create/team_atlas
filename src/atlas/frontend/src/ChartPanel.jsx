import React, { useEffect, useMemo, useRef, useState } from "react";
import AtlasChart from "./AtlasChart";

// ----------------------------------------------------
// URL builder (DEV estable: snapshot pega directo a 8001)
// - Evita proxy colgado en /api/snapshot
// - Mantiene "/api/..." para producción si algún día lo usás
// ----------------------------------------------------
function buildUrl({ world, atlas_mode, symbol, tf, limit }) {
  const p = new URLSearchParams();
  if (world) p.set("world", world);
  if (atlas_mode) p.set("atlas_mode", atlas_mode);
  if (symbol) p.set("symbol", symbol);
  if (tf) p.set("tf", tf);
  if (limit) p.set("limit", String(limit));

  // DEV: si estamos en localhost/127.0.0.1, pegamos directo al backend 8001
  const isLocal =
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname === "localhost";

  const base = isLocal ? "http://127.0.0.1:8001" : "";
  return `${base}/api/snapshot?${p.toString()}`;
}

function pickCandles(snap) {
  if (!snap) return [];
  if (Array.isArray(snap.candles)) return snap.candles;
  if (Array.isArray(snap?.data?.candles)) return snap.data.candles; // legacy
  if (Array.isArray(snap?.analysis?.candles)) return snap.analysis.candles; // fallback
  return [];
}

export default function ChartPanel({ world, atlas_mode, symbol, tf, count }) {
  // UI "count" → backend "limit"
  const limit = count;

  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const pollRef = useRef(null);
  const inflightRef = useRef(null);

  const url = useMemo(
    () => buildUrl({ world, atlas_mode, symbol, tf, limit }),
    [world, atlas_mode, symbol, tf, limit]
  );

  async function fetchSnapshot() {
    // Cancelar request anterior si quedó colgada
    if (inflightRef.current) {
      try {
        inflightRef.current.abort();
      } catch {}
    }

    const controller = new AbortController();
    inflightRef.current = controller;

    try {
      setLoading(true);
      setError(null);

      // timeout duro (para evitar "pending" infinito)
      const timeoutId = setTimeout(() => {
        try {
          controller.abort();
        } catch {}
      }, 3500);

      const res = await fetch(url, {
        cache: "no-store",
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!res.ok) throw new Error(`Snapshot error ${res.status}`);

      const data = await res.json();

      // debug pro: te dice qué llega realmente
      console.log(
        "SNAPSHOT",
        data?.analysis?.source,
        "candles=",
        (data?.candles || []).length
      );

      setSnapshot(data);
      setError(null);
    } catch (err) {
      const msg = String(err?.message || err);
      setError(msg.includes("aborted") ? "Timeout / request abortada" : msg);
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);

    fetchSnapshot();
    pollRef.current = setInterval(fetchSnapshot, 1200);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (inflightRef.current) {
        try {
          inflightRef.current.abort();
        } catch {}
      }
    };
  }, [url]); // eslint-disable-line

  const candles = useMemo(() => pickCandles(snapshot), [snapshot]);
  const source =
    snapshot?.analysis?.source || snapshot?.analysis?.meta?.source || "-";
  const state = snapshot?.analysis?.logic?.state || "—";
  const note =
    snapshot?.analysis?.logic?.note || snapshot?.analysis?.note || "—";

  return (
    <div className="rounded-2xl border border-neutral-800 bg-neutral-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm text-neutral-400">
          {world} | {atlas_mode} | {symbol} | {tf}
        </div>
        <div className="text-xs text-neutral-500">
          source:{" "}
          <span className="text-neutral-200 font-semibold">{source}</span>
        </div>
      </div>

      {error && <div className="text-red-400 text-sm mb-2">{error}</div>}

      <div className="mb-2 text-xs text-neutral-400">
        estado:{" "}
        <span className="text-neutral-200 font-semibold">{state}</span> · {note}
      </div>

      {/* CHART REAL */}
      <div className="rounded-2xl overflow-hidden border border-neutral-800">
        <AtlasChart candles={candles} symbol={symbol} tf={tf} />
      </div>

      <div className="mt-3 text-sm">
        {loading ? (
          <span className="text-yellow-400">Cargando snapshot...</span>
        ) : candles?.length ? (
          <span className="text-cyan-300">Candles OK: {candles.length}</span>
        ) : (
          <span className="text-yellow-400">Esperando velas...</span>
        )}
      </div>
    </div>
  );
}
