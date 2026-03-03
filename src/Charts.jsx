// src/atlas/frontend/src/Charts.jsx
import React, { useEffect, useMemo, useRef } from "react";
import { createChart } from "lightweight-charts";

function normalizeCandles(candles) {
  const arr = Array.isArray(candles) ? candles : [];

  // sort asc by time, then dedupe (keep last occurrence)
  const sorted = [...arr].sort((a, b) => (a.time ?? 0) - (b.time ?? 0));

  const out = [];
  let prevT = null;

  for (const c of sorted) {
    const t = c?.time ?? null;
    if (t == null) continue;

    // If duplicate time, replace last candle (keep most recent values)
    if (prevT === t && out.length) {
      out[out.length - 1] = c;
      continue;
    }
    out.push(c);
    prevT = t;
  }
  return out;
}

export default function Charts({ candles }) {
  const ref = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const data = useMemo(() => normalizeCandles(candles), [candles]);

  useEffect(() => {
    if (!ref.current) return;

    // create chart once
    if (!chartRef.current) {
      const chart = createChart(ref.current, {
        layout: {
          background: { color: "#0b0f14" },
          textColor: "#cfe3ff",
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.06)" },
          horzLines: { color: "rgba(255,255,255,0.06)" },
        },
        rightPriceScale: { borderColor: "rgba(255,255,255,0.10)" },
        timeScale: { borderColor: "rgba(255,255,255,0.10)" },
        crosshair: { mode: 1 },
      });

      const series = chart.addCandlestickSeries({
        upColor: "#66ffb3",
        downColor: "#ff6b6b",
        borderUpColor: "#66ffb3",
        borderDownColor: "#ff6b6b",
        wickUpColor: "#66ffb3",
        wickDownColor: "#ff6b6b",
      });

      chartRef.current = chart;
      seriesRef.current = series;
    }

    const ro = new ResizeObserver(() => {
      if (!ref.current || !chartRef.current) return;
      chartRef.current.applyOptions({
        width: ref.current.clientWidth,
        height: ref.current.clientHeight,
      });
    });
    ro.observe(ref.current);

    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    if (!seriesRef.current) return;
    seriesRef.current.setData(data);
    if (chartRef.current) chartRef.current.timeScale().fitContent();
  }, [data]);

  return <div ref={ref} style={{ width: "100%", height: 520 }} />;
}// src/atlas/frontend/src/Charts.jsx
import React, { useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";

function toUnixSec(t) {
  // acepta:
  // - number ms
  // - number sec
  // - ISO string
  if (t == null) return null;

  if (typeof t === "number") {
    // si parece ms
    if (t > 10_000_000_000) return Math.floor(t / 1000);
    return Math.floor(t);
  }

  const s = String(t);
  const n = Number(s);
  if (Number.isFinite(n)) {
    if (n > 10_000_000_000) return Math.floor(n / 1000);
    return Math.floor(n);
  }

  const d = new Date(s);
  if (!Number.isFinite(d.getTime())) return null;
  return Math.floor(d.getTime() / 1000);
}

function normalizeCandle(c) {
  // soporta {t,o,h,l,c} o {time,open,high,low,close}
  const time = toUnixSec(c.t ?? c.time);
  const open = Number(c.o ?? c.open);
  const high = Number(c.h ?? c.high);
  const low = Number(c.l ?? c.low);
  const close = Number(c.c ?? c.close);

  if (!time || !Number.isFinite(open) || !Number.isFinite(high) || !Number.isFinite(low) || !Number.isFinite(close)) {
    return null;
  }

  return { time, open, high, low, close };
}

export default function Charts({ snapshot }) {
  const ref = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!ref.current) return;

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 420,
      layout: { background: { color: "white" }, textColor: "black" },
      grid: { vertLines: { visible: true }, horzLines: { visible: true } },
      timeScale: { timeVisible: true, secondsVisible: true },
      rightPriceScale: { borderVisible: false },
      crosshair: { mode: 0 },
    });

    // velas custom (sin verde/rojo default)
    const series = chart.addCandlestickSeries({
      upColor: "#2b2b2b",
      downColor: "#9a9a9a",
      borderUpColor: "#2b2b2b",
      borderDownColor: "#9a9a9a",
      wickUpColor: "#2b2b2b",
      wickDownColor: "#9a9a9a",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const ro = new ResizeObserver(() => {
      if (!ref.current) return;
      chart.applyOptions({ width: ref.current.clientWidth });
    });
    ro.observe(ref.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    const candles = Array.isArray(snapshot?.candles) ? snapshot.candles : [];
    const data = candles
      .map(normalizeCandle)
      .filter(Boolean);

    if (data.length === 0) {
      series.setData([]);
      return;
    }

    series.setData(data);
  }, [snapshot]);

  return (
    <div style={{ width: "100%" }}>
      <div ref={ref} />
    </div>
  );
}