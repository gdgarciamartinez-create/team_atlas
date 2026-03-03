// src/atlas/frontend/src/AtlasChart.jsx
import React, { useEffect, useMemo, useRef } from "react";
import { createChart } from "lightweight-charts";

/**
 * AtlasChart
 * - Si no hay velas, el chart NO debe "correrse" a la derecha.
 * - Mostramos overlay y dejamos el timeScale fijo.
 *
 * Props esperadas:
 *  - candles: [{ time, open, high, low, close }]  (time en unix seconds)
 *  - height: number (opcional)
 */
export default function AtlasChart({ candles = [], height = 520 }) {
  const wrapRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const hasCandles = Array.isArray(candles) && candles.length > 1;

  // normalizamos por si vienen mal formadas
  const data = useMemo(() => {
    if (!Array.isArray(candles)) return [];
    return candles
      .map((c) => ({
        time: Number(c.time),
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
      }))
      .filter((c) => Number.isFinite(c.time));
  }, [candles]);

  useEffect(() => {
    if (!wrapRef.current) return;

    // Crear chart una sola vez
    if (!chartRef.current) {
      const chart = createChart(wrapRef.current, {
        width: wrapRef.current.clientWidth,
        height,
        layout: {
          background: { color: "rgba(15, 23, 42, 0.92)" },
          textColor: "rgba(226,232,240,0.9)",
          fontSize: 12,
        },
        grid: {
          vertLines: { color: "rgba(148,163,184,0.10)" },
          horzLines: { color: "rgba(148,163,184,0.10)" },
        },
        rightPriceScale: {
          borderColor: "rgba(255,255,255,0.10)",
        },
        timeScale: {
          borderColor: "rgba(255,255,255,0.10)",
          // Esto ayuda a que el chart no se corra raro
          rightOffset: 0,
          fixLeftEdge: true,
          fixRightEdge: true,
          lockVisibleTimeRangeOnResize: true,
        },
        crosshair: {
          vertLine: { color: "rgba(255,255,255,0.15)" },
          horzLine: { color: "rgba(255,255,255,0.15)" },
        },
      });

      const series = chart.addCandlestickSeries({
        // tus colores personalizados (no verde/rojo)
        upColor: "#4f46e5",
        downColor: "#fb7185",
        borderUpColor: "#4f46e5",
        borderDownColor: "#fb7185",
        wickUpColor: "#a5b4fc",
        wickDownColor: "#fecdd3",
      });

      chartRef.current = chart;
      seriesRef.current = series;

      // Resize
      const onResize = () => {
        if (!wrapRef.current || !chartRef.current) return;
        chartRef.current.applyOptions({
          width: wrapRef.current.clientWidth,
          height,
        });

        // si hay velas, re-encuadrar
        if (seriesRef.current && hasCandles) {
          chartRef.current.timeScale().fitContent();
        } else {
          // si NO hay velas, mantenemos el timeScale fijo
          chartRef.current.timeScale().applyOptions({
            rightOffset: 0,
            fixLeftEdge: true,
            fixRightEdge: true,
          });
        }
      };

      window.addEventListener("resize", onResize);
      return () => window.removeEventListener("resize", onResize);
    }
  }, [height, hasCandles]);

  useEffect(() => {
    const chart = chartRef.current;
    const series = seriesRef.current;
    if (!chart || !series) return;

    if (hasCandles) {
      series.setData(data);

      // encuadrar contenido
      chart.timeScale().fitContent();

      // mantenerlo estable
      chart.timeScale().applyOptions({
        rightOffset: 0,
        fixLeftEdge: true,
        fixRightEdge: true,
        lockVisibleTimeRangeOnResize: true,
      });
    } else {
      // No hay velas: no dejar que el timeScale "se vaya"
      series.setData([]);

      chart.timeScale().applyOptions({
        rightOffset: 0,
        fixLeftEdge: true,
        fixRightEdge: true,
        lockVisibleTimeRangeOnResize: true,
      });

      // Truco: fijar un rango lógico estable (aunque no haya data)
      // Esto evita el salto visual hacia la derecha.
      // Nota: algunos builds de lightweight-charts aceptan esto sin data.
      try {
        chart.timeScale().setVisibleLogicalRange({ from: -50, to: 50 });
      } catch {
        // si tu versión no lo soporta, igual el overlay resuelve lo visual
      }
    }
  }, [data, hasCandles]);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height,
        borderRadius: 14,
        overflow: "hidden",
        border: "1px solid rgba(255,255,255,0.10)",
      }}
    >
      <div ref={wrapRef} style={{ width: "100%", height: "100%" }} />

      {/* Overlay cuando no hay velas */}
      {!hasCandles ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "grid",
            placeItems: "center",
            pointerEvents: "none",
            background:
              "linear-gradient(180deg, rgba(15,23,42,0.55), rgba(15,23,42,0.35))",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div style={{ fontWeight: 900, fontSize: 14, opacity: 0.92 }}>
              Sin velas todavía
            </div>
            <div style={{ marginTop: 6, fontSize: 12, opacity: 0.75 }}>
              Esperando data_source / feed del mundo seleccionado
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}