// src/atlas/frontend/src/Charts.jsx
import React, { useEffect, useRef } from "react";
import { createChart } from "lightweight-charts";

/**
 * Normaliza candles para Lightweight Charts:
 * - garantiza time en SEGUNDOS (int)
 * - deduplica por time (si hay repetidos, se queda con el último)
 * - ordena ascendente por time
 * - elimina items inválidos
 */
function normalizeCandles(raw) {
  if (!Array.isArray(raw)) return [];

  const byTime = new Map();

  for (const c of raw) {
    if (!c) continue;

    // soporta formatos: {time, open, high, low, close} o {t, o, h, l, c}
    const t0 = c.time ?? c.t ?? c.timestamp ?? c.ts ?? null;
    const o = c.open ?? c.o;
    const h = c.high ?? c.h;
    const l = c.low ?? c.l;
    const cl = c.close ?? c.c;

    if (t0 == null) continue;

    let t = Number(t0);
    if (!Number.isFinite(t)) continue;

    // Si viene en ms (13 dígitos típico), lo pasamos a segundos
    if (t > 2_000_000_000_000) t = Math.floor(t / 1000);

    t = Math.floor(t);

    const oo = Number(o);
    const hh = Number(h);
    const ll = Number(l);
    const cc = Number(cl);

    if (![oo, hh, ll, cc].every((x) => Number.isFinite(x))) continue;

    // dedupe: si se repite el time, la última gana
    byTime.set(t, { time: t, open: oo, high: hh, low: ll, close: cc });
  }

  const out = Array.from(byTime.values()).sort((a, b) => a.time - b.time);

  // safety extra: garantiza strictly increasing (por si algo raro coló)
  const cleaned = [];
  let lastT = null;
  for (const x of out) {
    if (lastT == null || x.time > lastT) {
      cleaned.push(x);
      lastT = x.time;
    }
  }

  return cleaned;
}

export default function Charts({ candles = [] }) {
  const ref = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  useEffect(() => {
    if (!ref.current) return;

    // crear chart
    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 520,
      layout: { background: { color: "transparent" }, textColor: "#e9eef5" },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.06)" },
        horzLines: { color: "rgba(255,255,255,0.06)" },
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.12)" },
      timeScale: { borderColor: "rgba(255,255,255,0.12)" },
      crosshair: { mode: 1 },
    });

    const series = chart.addCandlestickSeries({
      // (no tocamos colores acá, los tuyos ya están definidos en tu proyecto)
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const onResize = () => {
      if (!ref.current || !chartRef.current) return;
      chartRef.current.applyOptions({ width: ref.current.clientWidth });
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current;
    const chart = chartRef.current;
    if (!series || !chart) return;

    const normalized = normalizeCandles(candles);

    // setData exige time asc y sin duplicados
    series.setData(normalized);

    // opcional: autoscale al final si hay datos
    if (normalized.length > 5) {
      chart.timeScale().fitContent();
    }
  }, [candles]);

  return <div ref={ref} style={{ width: "100%", height: 520 }} />;
}