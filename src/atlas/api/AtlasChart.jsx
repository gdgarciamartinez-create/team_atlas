import React, { useEffect, useMemo, useRef } from "react";
import { createChart } from "lightweight-charts";

/**
 * AtlasChart
 * - Renderiza SOLO con snapshot.candles
 * - Acepta candles en formato:
 *   - {t,o,h,l,c,v}
 *   - {time,open,high,low,close,volume}
 * - Si no hay velas: limpia y deja canvas vacío.
 */
export default function AtlasChart({
  snapshot,
  height = 520,
  title = "",
}) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef(null);

  const candles = useMemo(() => {
    const arr = snapshot?.candles;
    if (!Array.isArray(arr) || arr.length === 0) return [];

    const normalized = [];
    for (const c of arr) {
      if (!c || typeof c !== "object") continue;

      const t = c.t ?? c.time;
      const o = c.o ?? c.open;
      const h = c.h ?? c.high;
      const l = c.l ?? c.low;
      const cl = c.c ?? c.close;

      if (t == null || o == null || h == null || l == null || cl == null) continue;

      normalized.push({
        time: Number(t),        // lightweight-charts usa "time"
        open: Number(o),
        high: Number(h),
        low: Number(l),
        close: Number(cl),
      });
    }
    return normalized;
  }, [snapshot]);

  // Init chart
  useEffect(() => {
    if (!containerRef.current) return;

    // destroy previo
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
      seriesRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      height,
      width: containerRef.current.clientWidth,
      layout: {
        background: { color: "transparent" },
        textColor: "rgba(255,255,255,0.85)",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.06)" },
        horzLines: { color: "rgba(255,255,255,0.06)" },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
      },
      crosshair: {
        vertLine: { color: "rgba(255,255,255,0.18)" },
        horzLine: { color: "rgba(255,255,255,0.18)" },
      },
    });

    const series = chart.addCandlestickSeries({
      // NO definimos colores específicos (tu proyecto ya setea custom en otra capa si quiere),
      // pero dejamos defaults del chart.
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const onResize = () => {
      if (!containerRef.current || !chartRef.current) return;
      chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
    };
  }, [height]);

  // Update data
  useEffect(() => {
    if (!seriesRef.current) return;

    if (!candles || candles.length === 0) {
      // Limpia serie
      seriesRef.current.setData([]);
      return;
    }

    // Importante: ordenar por time por si MT5 manda raro
    const sorted = [...candles].sort((a, b) => a.time - b.time);

    seriesRef.current.setData(sorted);

    // Ajustar vista al contenido
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent();
    }
  }, [candles]);

  const label = title || `${snapshot?.symbol ?? "-"} (${snapshot?.tf ?? "-"})`;

  return (
    <div style={{ width: "100%" }}>
      <div style={{ padding: "6px 10px", color: "rgba(255,255,255,0.75)", fontSize: 13 }}>
        <div style={{ fontWeight: 700 }}>{label}</div>
        <div style={{ fontSize: 12, opacity: 0.8 }}>
          Dibuja SOLO con snapshot.candles. Si no hay velas, limpia.
        </div>
      </div>

      <div
        ref={containerRef}
        style={{
          width: "100%",
          height,
          borderRadius: 14,
          background: "rgba(0,0,0,0.12)",
          overflow: "hidden",
        }}
      />
    </div>
  );
}
