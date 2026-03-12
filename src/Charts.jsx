import React, { useEffect, useMemo, useRef } from "react";
import { createChart, LineStyle } from "lightweight-charts";

function toUnixSec(t) {
  if (t == null) return null;

  if (typeof t === "number") {
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
  const time = toUnixSec(c?.t ?? c?.time);
  const open = Number(c?.o ?? c?.open);
  const high = Number(c?.h ?? c?.high);
  const low = Number(c?.l ?? c?.low);
  const close = Number(c?.c ?? c?.close);

  if (
    time == null ||
    !Number.isFinite(open) ||
    !Number.isFinite(high) ||
    !Number.isFinite(low) ||
    !Number.isFinite(close)
  ) {
    return null;
  }

  return { time, open, high, low, close };
}

function normalizeCandles(arr) {
  const candles = Array.isArray(arr) ? arr : [];

  const normalized = candles.map(normalizeCandle).filter(Boolean);

  normalized.sort((a, b) => a.time - b.time);

  const deduped = [];
  let prevTime = null;

  for (const c of normalized) {
    if (prevTime === c.time && deduped.length) {
      deduped[deduped.length - 1] = c;
    } else {
      deduped.push(c);
      prevTime = c.time;
    }
  }

  return deduped;
}

function buildShortLevelSeries(data, price) {
  if (!Array.isArray(data) || data.length < 2) return [];
  if (!Number.isFinite(Number(price))) return [];

  const len = data.length;
  const startIndex = Math.max(0, len - 8);
  const endIndex = len - 1;

  const startTime = data[startIndex]?.time;
  const endTime = data[endIndex]?.time;

  if (startTime == null || endTime == null) return [];

  return [
    { time: startTime, value: Number(price) },
    { time: endTime, value: Number(price) },
  ];
}

function lastRowFromSnapshot(snapshot) {
  const rows = snapshot?.ui?.rows;
  if (!Array.isArray(rows) || rows.length === 0) return null;

  const signalRow = rows.find((r) => r?.state === "SIGNAL");
  return signalRow || rows[0] || null;
}

export default function Charts({ snapshot, accent = "#ff2fb3" }) {
  const ref = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);

  const entrySeriesRef = useRef(null);
  const peSeriesRef = useRef(null);
  const tpSeriesRef = useRef(null);
  const slSeriesRef = useRef(null);

  const data = useMemo(() => {
    return normalizeCandles(snapshot?.candles);
  }, [snapshot]);

  const activeRow = useMemo(() => lastRowFromSnapshot(snapshot), [snapshot]);

  useEffect(() => {
    if (!ref.current) return;

    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 520,
      layout: {
        background: { color: "#0b0f14" },
        textColor: "#d8e6ff",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.05)" },
        horzLines: { color: "rgba(255,255,255,0.05)" },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.10)",
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.10)",
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 1,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#8b8b8b",
      downColor: "#2b2b2b",
      borderUpColor: "#8b8b8b",
      borderDownColor: "#2b2b2b",
      wickUpColor: "#8b8b8b",
      wickDownColor: "#2b2b2b",
      priceLineVisible: false,
      lastValueVisible: true,
    });

    const entrySeries = chart.addLineSeries({
      color: accent,
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    const peSeries = chart.addLineSeries({
      color: "#f0b35a",
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    const tpSeries = chart.addLineSeries({
      color: "#63c787",
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    const slSeries = chart.addLineSeries({
      color: "#ff6b6b",
      lineWidth: 2,
      lineStyle: LineStyle.Solid,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    entrySeriesRef.current = entrySeries;
    peSeriesRef.current = peSeries;
    tpSeriesRef.current = tpSeries;
    slSeriesRef.current = slSeries;

    const ro = new ResizeObserver(() => {
      if (!ref.current || !chartRef.current) return;
      chartRef.current.applyOptions({
        width: ref.current.clientWidth,
        height: ref.current.clientHeight || 520,
      });
    });

    ro.observe(ref.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      entrySeriesRef.current = null;
      peSeriesRef.current = null;
      tpSeriesRef.current = null;
      slSeriesRef.current = null;
    };
  }, [accent]);

  useEffect(() => {
    if (!candleSeriesRef.current) return;

    candleSeriesRef.current.setData(data);

    if (chartRef.current && data.length > 0) {
      chartRef.current.timeScale().fitContent();
    }
  }, [data]);

  useEffect(() => {
    if (!entrySeriesRef.current || !peSeriesRef.current || !tpSeriesRef.current || !slSeriesRef.current) {
      return;
    }

    const state = activeRow?.state;
    const entry = Number(activeRow?.entry);
    const parcial = Number(activeRow?.parcial ?? activeRow?.partial ?? activeRow?.tp1);
    const tp = Number(activeRow?.tp);
    const sl = Number(activeRow?.sl);

    if (state !== "SIGNAL" || data.length < 2) {
      entrySeriesRef.current.setData([]);
      peSeriesRef.current.setData([]);
      tpSeriesRef.current.setData([]);
      slSeriesRef.current.setData([]);
      return;
    }

    entrySeriesRef.current.setData(buildShortLevelSeries(data, entry));
    peSeriesRef.current.setData(buildShortLevelSeries(data, parcial));
    tpSeriesRef.current.setData(buildShortLevelSeries(data, tp));
    slSeriesRef.current.setData(buildShortLevelSeries(data, sl));
  }, [activeRow, data]);

  return (
    <div
      style={{
        width: "100%",
        height: 520,
        position: "relative",
      }}
    >
      <div ref={ref} style={{ width: "100%", height: "100%" }} />

      {activeRow?.state === "SIGNAL" ? (
        <div
          style={{
            position: "absolute",
            right: 12,
            top: 12,
            display: "grid",
            gap: 6,
            zIndex: 5,
            pointerEvents: "none",
          }}
        >
          <MiniLevel label="ENTRY" value={activeRow?.entry} color={accent} />
          <MiniLevel label="PE" value={activeRow?.parcial ?? activeRow?.partial ?? activeRow?.tp1} color="#f0b35a" />
          <MiniLevel label="TP" value={activeRow?.tp} color="#63c787" />
          <MiniLevel label="SL" value={activeRow?.sl} color="#ff6b6b" />
        </div>
      ) : null}
    </div>
  );
}

function MiniLevel({ label, value, color }) {
  const show =
    value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(Number(value));

  if (!show) return null;

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        alignItems: "center",
        background: "rgba(10,14,20,0.78)",
        border: `1px solid ${color}55`,
        borderRadius: 10,
        padding: "6px 9px",
        color: "#eef3fb",
        fontSize: 11,
        fontWeight: 800,
        backdropFilter: "blur(6px)",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: color,
          display: "inline-block",
        }}
      />
      <span>{label}</span>
      <span style={{ opacity: 0.88 }}>{Number(value).toFixed(3)}</span>
    </div>
  );
}