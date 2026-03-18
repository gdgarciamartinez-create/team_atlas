import React, { useEffect, useMemo, useRef } from "react";
import { createChart, LineStyle, CrosshairMode } from "lightweight-charts";

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

function normalizeStateKey(state) {
  const s = String(state || "").toUpperCase().trim();

  if (s === "WAIT" || s === "NO_DATA" || s === "UNKNOWN_MODE" || s === "UNKNOWN_WORLD") {
    return "SIN_SETUP";
  }

  if (s === "WAIT_GATILLO" || s === "SIGNAL" || s === "SETUP") {
    return "SET_UP";
  }

  if (s === "SIN_SETUP") return "SIN_SETUP";
  if (s === "SET_UP") return "SET_UP";
  if (s === "ENTRY") return "ENTRY";
  if (s === "IN_TRADE") return "IN_TRADE";
  if (s === "TP1") return "TP1";
  if (s === "TP2") return "TP2";
  if (s === "RUN") return "RUN";
  if (s === "CLOSED") return "CLOSED";

  return "SIN_SETUP";
}

function decimalsBySymbol(sym) {
  if (!sym) return 5;
  if (sym.startsWith("XAU")) return 2;
  if (sym.startsWith("BTC")) return 2;
  if (sym.startsWith("USTEC")) return 2;
  if (sym.startsWith("USOIL")) return 2;
  if (sym.includes("JPY")) return 3;
  return 5;
}

function minMoveByDigits(digits) {
  if (digits <= 0) return 1;
  return Number((1 / 10 ** digits).toFixed(digits));
}

function getRange(data) {
  if (!Array.isArray(data) || data.length < 2) return null;

  const lows = data.map((c) => c.low).filter(Number.isFinite);
  const highs = data.map((c) => c.high).filter(Number.isFinite);

  if (!lows.length || !highs.length) return null;

  const minLow = Math.min(...lows);
  const maxHigh = Math.max(...highs);
  const span = maxHigh - minLow;

  if (!Number.isFinite(span) || span <= 0) return null;

  return { minLow, maxHigh, span };
}

function isRenderableLevel(price, data) {
  const p = Number(price);
  if (!Number.isFinite(p) || p <= 0) return false;

  const range = getRange(data);
  if (!range) return true;

  const { minLow, maxHigh, span } = range;

  const lowerBound = minLow - span * 3.0;
  const upperBound = maxHigh + span * 3.0;

  return p >= lowerBound && p <= upperBound;
}

function resolveStartTime(activeRow) {
  return (
    toUnixSec(activeRow?.entry_ts) ??
    toUnixSec(activeRow?.entry_time) ??
    toUnixSec(activeRow?.entry_candle_time) ??
    toUnixSec(activeRow?.signal_candle_time) ??
    toUnixSec(activeRow?.updated_at) ??
    null
  );
}

function isFinitePrice(value) {
  const n = Number(value);
  return Number.isFinite(n) && n > 0;
}

function buildHorizontalSeries(data, price, startTime) {
  const p = Number(price);

  if (!Array.isArray(data) || data.length < 2) return [];
  if (!Number.isFinite(p) || p <= 0) return [];
  if (startTime == null) return [];

  const lastCandleTime = data[data.length - 1]?.time ?? null;
  const endTime =
    lastCandleTime != null
      ? Math.max(lastCandleTime, startTime + 1)
      : startTime + 1;

  if (endTime == null) return [];

  return [
    { time: startTime, value: p },
    { time: endTime, value: p },
  ];
}

function buildBaselineZoneSeries(data, level, startTime) {
  const lvl = Number(level);

  if (!Array.isArray(data) || data.length < 2) return [];
  if (!Number.isFinite(lvl) || lvl <= 0) return [];
  if (startTime == null) return [];

  const lastCandleTime = data[data.length - 1]?.time ?? null;
  const endTime =
    lastCandleTime != null
      ? Math.max(lastCandleTime, startTime + 1)
      : startTime + 1;

  if (endTime == null) return [];

  return [
    { time: startTime, value: lvl },
    { time: endTime, value: lvl },
  ];
}

function isOperativeState(state) {
  return ["ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"].includes(
    normalizeStateKey(state)
  );
}

function hasExactTradePayload(row) {
  if (!row) return false;

  const side = String(row?.side || "").toUpperCase().trim();
  const entry = Number(row?.entry);
  const sl = Number(row?.sl);
  const tp = Number(row?.tp2 ?? row?.tp ?? row?.parcial ?? row?.tp1 ?? row?.tp1_price);

  if (!["SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"].includes(normalizeStateKey(row?.state))) return false;
  if (!["BUY", "SELL"].includes(side)) return false;
  if (!isFinitePrice(entry) || !isFinitePrice(sl) || !isFinitePrice(tp)) return false;

  if (side === "BUY") return tp > entry;
  return tp < entry;
}

function resolveChartTradeRow(snapshot, activeRow) {
  const snapshotRows = Array.isArray(snapshot?.ui?.rows) ? snapshot.ui.rows : [];
  const snapshotSymbol = snapshot?.symbol;
  const snapshotRow =
    snapshotRows.find((r) => r?.symbol === snapshotSymbol) || snapshotRows[0] || null;

  if (hasExactTradePayload(snapshotRow)) return snapshotRow;
  if (hasExactTradePayload(activeRow)) return activeRow;
  return null;
}

function buildVisibleTradeLines(tradeRow, data) {
  const state = normalizeStateKey(tradeRow?.state);
  const showTradeLines = ["SET_UP", "ENTRY", "IN_TRADE", "TP1", "TP2", "RUN"].includes(state);

  if (!showTradeLines || !Array.isArray(data) || data.length < 2) {
    return {
      entry: null,
      sl: null,
      tp: null,
      entryData: [],
      slData: [],
      tpData: [],
      profitAboveData: [],
      profitBelowData: [],
      lossAboveData: [],
      lossBelowData: [],
      hasValidTrade: false,
    };
  }

  const startTime = resolveStartTime(tradeRow) ?? data[0]?.time ?? null;

  const entry = Number(tradeRow?.entry);
  const sl = Number(tradeRow?.sl);
  const tp = Number(tradeRow?.tp2 ?? tradeRow?.tp ?? tradeRow?.parcial ?? tradeRow?.tp1 ?? tradeRow?.tp1_price);
  const side = String(tradeRow?.side || "").toUpperCase().trim();

  const entryOk = isRenderableLevel(entry, data);
  const slOk = isRenderableLevel(sl, data);
  const tpOk = isRenderableLevel(tp, data);

  const geometryOk =
    side === "BUY" ? tp > entry :
    side === "SELL" ? tp < entry :
    false;

  if (!entryOk || !slOk || !tpOk || startTime == null || !geometryOk) {
    return {
      entry: null,
      sl: null,
      tp: null,
      entryData: [],
      slData: [],
      tpData: [],
      profitAboveData: [],
      profitBelowData: [],
      lossAboveData: [],
      lossBelowData: [],
      hasValidTrade: false,
    };
  }

  const entryData = buildHorizontalSeries(data, entry, startTime);
  const slData = buildHorizontalSeries(data, sl, startTime);
  const tpData = buildHorizontalSeries(data, tp, startTime);

  const profitAboveData = [];
  const profitBelowData = [];
  const lossAboveData = [];
  const lossBelowData = [];

  if (tp > entry) {
    profitAboveData.push(...buildBaselineZoneSeries(data, tp, startTime));
  } else if (tp < entry) {
    profitBelowData.push(...buildBaselineZoneSeries(data, tp, startTime));
  }

  if (sl > entry) {
    lossAboveData.push(...buildBaselineZoneSeries(data, sl, startTime));
  } else if (sl < entry) {
    lossBelowData.push(...buildBaselineZoneSeries(data, sl, startTime));
  }

  return {
    entry,
    sl,
    tp,
    side,
    startTime,
    entryData,
    slData,
    tpData,
    profitAboveData,
    profitBelowData,
    lossAboveData,
    lossBelowData,
    hasValidTrade: true,
  };
}

function stableTradeSignature(trade) {
  try {
    return JSON.stringify({
      valid: trade.hasValidTrade,
      side: trade.side,
      startTime: trade.startTime,
      entry: trade.entryData,
      sl: trade.slData,
      tp: trade.tpData,
      pa: trade.profitAboveData,
      pb: trade.profitBelowData,
      la: trade.lossAboveData,
      lb: trade.lossBelowData,
      entryBase: trade.entry,
    });
  } catch {
    return "";
  }
}

function clearTradeSeries({
  entrySeriesRef,
  slSeriesRef,
  tpSeriesRef,
  profitAboveRef,
  profitBelowRef,
  lossAboveRef,
  lossBelowRef,
}) {
  try {
    entrySeriesRef.current?.setData([]);
    slSeriesRef.current?.setData([]);
    tpSeriesRef.current?.setData([]);
    profitAboveRef.current?.setData([]);
    profitBelowRef.current?.setData([]);
    lossAboveRef.current?.setData([]);
    lossBelowRef.current?.setData([]);
  } catch {}
}

function candlesSignatureOf(data) {
  if (!Array.isArray(data) || !data.length) return "[]";
  const first = data[0];
  const last = data[data.length - 1];
  return `${data.length}|${first.time}|${first.open}|${first.high}|${first.low}|${first.close}|${last.time}|${last.open}|${last.high}|${last.low}|${last.close}`;
}

export default function Charts({ snapshot, activeRow, accent = "#ff2fb3" }) {
  const containerRef = useRef(null);

  const chartRef = useRef(null);
  const resizeObserverRef = useRef(null);

  const candleSeriesRef = useRef(null);
  const entrySeriesRef = useRef(null);
  const slSeriesRef = useRef(null);
  const tpSeriesRef = useRef(null);
  const profitAboveRef = useRef(null);
  const profitBelowRef = useRef(null);
  const lossAboveRef = useRef(null);
  const lossBelowRef = useRef(null);

  const hasFittedRef = useRef(false);
  const lastCandlesSignatureRef = useRef("");
  const lastTradeSignatureRef = useRef("");
  const lastGoodCandlesRef = useRef([]);
  const resizeRafRef = useRef(null);

  const symbolKey = snapshot?.symbol || activeRow?.symbol || "UNKNOWN";
  const tfKey = snapshot?.tf || activeRow?.tf || "UNKNOWN";
  const chartKey = `${symbolKey}__${tfKey}`;
  const digits = decimalsBySymbol(symbolKey);
  const minMove = minMoveByDigits(digits);

  const incomingData = useMemo(() => {
    const source = snapshot?.candles || [];
    return normalizeCandles(source).slice(-120);
  }, [snapshot?.candles, snapshot?.symbol, snapshot?.tf]);

  const data = useMemo(() => {
    if (incomingData.length >= 2) return incomingData;
    return lastGoodCandlesRef.current || [];
  }, [incomingData]);

  const candlesSignature = useMemo(() => candlesSignatureOf(data), [data]);

  const chartTradeRow = useMemo(() => {
    return resolveChartTradeRow(snapshot, activeRow);
  }, [snapshot, activeRow]);

  const tradeLines = useMemo(() => {
    return buildVisibleTradeLines(chartTradeRow, data);
  }, [
    chartTradeRow?.state,
    chartTradeRow?.side,
    chartTradeRow?.entry,
    chartTradeRow?.sl,
    chartTradeRow?.tp,
    chartTradeRow?.tp2,
    chartTradeRow?.entry_candle_time,
    chartTradeRow?.entry_time,
    chartTradeRow?.entry_ts,
    data,
  ]);

  const tradeSignature = useMemo(() => stableTradeSignature(tradeLines), [tradeLines]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    hasFittedRef.current = false;
    lastCandlesSignatureRef.current = "";
    lastTradeSignatureRef.current = "";

    try {
      resizeObserverRef.current?.disconnect();
    } catch {}

    if (resizeRafRef.current) {
      cancelAnimationFrame(resizeRafRef.current);
      resizeRafRef.current = null;
    }

    try {
      chartRef.current?.remove();
    } catch {}

    chartRef.current = null;
    candleSeriesRef.current = null;
    entrySeriesRef.current = null;
    slSeriesRef.current = null;
    tpSeriesRef.current = null;
    profitAboveRef.current = null;
    profitBelowRef.current = null;
    lossAboveRef.current = null;
    lossBelowRef.current = null;

    try {
      const chart = createChart(el, {
        width: el.clientWidth || 1200,
        height: 520,
        layout: {
          background: { color: "#0b0f14" },
          textColor: "#d8e6ff",
          fontSize: 12,
        },
        localization: {
          priceFormatter: (price) => Number(price).toFixed(digits),
        },
        grid: {
          vertLines: { color: "rgba(255,255,255,0.035)" },
          horzLines: { color: "rgba(255,255,255,0.035)" },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
          vertLine: {
            visible: false,
            labelVisible: false,
          },
          horzLine: {
            visible: true,
            labelVisible: true,
          },
        },
        rightPriceScale: {
          visible: true,
          autoScale: true,
          borderColor: "rgba(255,255,255,0.10)",
          scaleMargins: {
            top: 0.08,
            bottom: 0.08,
          },
          entireTextOnly: false,
        },
        leftPriceScale: {
          visible: false,
        },
        timeScale: {
          borderColor: "rgba(255,255,255,0.10)",
          timeVisible: true,
          secondsVisible: false,
          rightOffset: 10,
          barSpacing: 8,
          minBarSpacing: 5,
          fixLeftEdge: false,
          fixRightEdge: false,
          lockVisibleTimeRangeOnResize: false,
        },
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
          horzTouchDrag: true,
          vertTouchDrag: false,
        },
        handleScale: {
          axisPressedMouseMove: true,
          mouseWheel: true,
          pinch: true,
        },
      });

      const commonPriceFormat = {
        type: "price",
        precision: digits,
        minMove,
      };

      const candleSeries = chart.addCandlestickSeries({
        upColor: "#f2ede4",
        downColor: "#8f877a",
        borderUpColor: "#f2ede4",
        borderDownColor: "#8f877a",
        wickUpColor: "#f2ede4",
        wickDownColor: "#8f877a",
        priceLineVisible: false,
        lastValueVisible: true,
        priceFormat: commonPriceFormat,
      });

      const profitAbove = chart.addBaselineSeries({
        baseValue: { type: "price", price: 1 },
        topFillColor1: "rgba(99, 199, 135, 0.22)",
        topFillColor2: "rgba(99, 199, 135, 0.08)",
        topLineColor: "rgba(99, 199, 135, 0)",
        bottomFillColor1: "rgba(99, 199, 135, 0)",
        bottomFillColor2: "rgba(99, 199, 135, 0)",
        bottomLineColor: "rgba(99, 199, 135, 0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        lastPriceAnimation: 0,
        priceFormat: commonPriceFormat,
      });

      const profitBelow = chart.addBaselineSeries({
        baseValue: { type: "price", price: 1 },
        topFillColor1: "rgba(99, 199, 135, 0)",
        topFillColor2: "rgba(99, 199, 135, 0)",
        topLineColor: "rgba(99, 199, 135, 0)",
        bottomFillColor1: "rgba(99, 199, 135, 0.22)",
        bottomFillColor2: "rgba(99, 199, 135, 0.08)",
        bottomLineColor: "rgba(99, 199, 135, 0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        lastPriceAnimation: 0,
        priceFormat: commonPriceFormat,
      });

      const lossAbove = chart.addBaselineSeries({
        baseValue: { type: "price", price: 1 },
        topFillColor1: "rgba(255, 107, 107, 0.20)",
        topFillColor2: "rgba(255, 107, 107, 0.07)",
        topLineColor: "rgba(255, 107, 107, 0)",
        bottomFillColor1: "rgba(255, 107, 107, 0)",
        bottomFillColor2: "rgba(255, 107, 107, 0)",
        bottomLineColor: "rgba(255, 107, 107, 0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        lastPriceAnimation: 0,
        priceFormat: commonPriceFormat,
      });

      const lossBelow = chart.addBaselineSeries({
        baseValue: { type: "price", price: 1 },
        topFillColor1: "rgba(255, 107, 107, 0)",
        topFillColor2: "rgba(255, 107, 107, 0)",
        topLineColor: "rgba(255, 107, 107, 0)",
        bottomFillColor1: "rgba(255, 107, 107, 0.20)",
        bottomFillColor2: "rgba(255, 107, 107, 0.07)",
        bottomLineColor: "rgba(255, 107, 107, 0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        lastPriceAnimation: 0,
        priceFormat: commonPriceFormat,
      });

      const entrySeries = chart.addLineSeries({
        color: accent,
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        lastPriceAnimation: 0,
        priceFormat: commonPriceFormat,
      });

      const slSeries = chart.addLineSeries({
        color: "#ff6b6b",
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        lastPriceAnimation: 0,
        priceFormat: commonPriceFormat,
      });

      const tpSeries = chart.addLineSeries({
        color: "#63c787",
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
        lastPriceAnimation: 0,
        priceFormat: commonPriceFormat,
      });

      chartRef.current = chart;
      candleSeriesRef.current = candleSeries;
      entrySeriesRef.current = entrySeries;
      slSeriesRef.current = slSeries;
      tpSeriesRef.current = tpSeries;
      profitAboveRef.current = profitAbove;
      profitBelowRef.current = profitBelow;
      lossAboveRef.current = lossAbove;
      lossBelowRef.current = lossBelow;

      const onResize = () => {
        if (!containerRef.current || !chartRef.current) return;
        const width = containerRef.current.clientWidth || 0;
        if (width < 50) return;

        if (resizeRafRef.current) cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = requestAnimationFrame(() => {
          try {
            chartRef.current?.applyOptions({
              width,
              height: 520,
            });
          } catch {}
        });
      };

      const resizeObserver = new ResizeObserver(onResize);
      resizeObserver.observe(el);
      resizeObserverRef.current = resizeObserver;
    } catch (err) {
      console.error("Charts init error:", err);
    }

    return () => {
      try {
        resizeObserverRef.current?.disconnect();
      } catch {}

      if (resizeRafRef.current) {
        cancelAnimationFrame(resizeRafRef.current);
        resizeRafRef.current = null;
      }

      try {
        chartRef.current?.remove();
      } catch {}

      resizeObserverRef.current = null;
      chartRef.current = null;
      candleSeriesRef.current = null;
      entrySeriesRef.current = null;
      slSeriesRef.current = null;
      tpSeriesRef.current = null;
      profitAboveRef.current = null;
      profitBelowRef.current = null;
      lossAboveRef.current = null;
      lossBelowRef.current = null;
    };
  }, [chartKey, digits, minMove, accent]);

  useEffect(() => {
    if (!chartRef.current) return;

    try {
      chartRef.current.applyOptions({
        localization: {
          priceFormatter: (price) => Number(price).toFixed(digits),
        },
      });

      const priceFormat = {
        type: "price",
        precision: digits,
        minMove,
      };

      candleSeriesRef.current?.applyOptions({ priceFormat });
      entrySeriesRef.current?.applyOptions({ color: accent, priceFormat });
      slSeriesRef.current?.applyOptions({ priceFormat });
      tpSeriesRef.current?.applyOptions({ priceFormat });
      profitAboveRef.current?.applyOptions({ priceFormat });
      profitBelowRef.current?.applyOptions({ priceFormat });
      lossAboveRef.current?.applyOptions({ priceFormat });
      lossBelowRef.current?.applyOptions({ priceFormat });
    } catch {}
  }, [digits, minMove, accent]);

  useEffect(() => {
    if (!candleSeriesRef.current || !chartRef.current) return;

    if (data && data.length >= 2) {
      lastGoodCandlesRef.current = data;
    }

    const safeData = data && data.length >= 2 ? data : lastGoodCandlesRef.current;

    if (!safeData || safeData.length < 2) {
      return;
    }

    const safeSignature = candlesSignatureOf(safeData);
    if (lastCandlesSignatureRef.current === safeSignature && hasFittedRef.current) return;

    lastCandlesSignatureRef.current = safeSignature;

    try {
      candleSeriesRef.current.setData(safeData);

      if (!hasFittedRef.current) {
        hasFittedRef.current = true;
        requestAnimationFrame(() => {
          try {
            chartRef.current?.timeScale().fitContent();
          } catch {}
        });
      }
    } catch (err) {
      console.error("Charts setData error:", err);
    }
  }, [data, candlesSignature]);

  useEffect(() => {
    if (
      !entrySeriesRef.current ||
      !slSeriesRef.current ||
      !tpSeriesRef.current ||
      !profitAboveRef.current ||
      !profitBelowRef.current ||
      !lossAboveRef.current ||
      !lossBelowRef.current
    ) {
      return;
    }

    if (lastTradeSignatureRef.current === tradeSignature) return;
    lastTradeSignatureRef.current = tradeSignature;

    try {
      if (!tradeLines.hasValidTrade) {
        clearTradeSeries({
          entrySeriesRef,
          slSeriesRef,
          tpSeriesRef,
          profitAboveRef,
          profitBelowRef,
          lossAboveRef,
          lossBelowRef,
        });
        return;
      }

      const entryBase = tradeLines.entry;

      entrySeriesRef.current.setData(tradeLines.entryData);
      slSeriesRef.current.setData(tradeLines.slData);
      tpSeriesRef.current.setData(tradeLines.tpData);

      profitAboveRef.current.applyOptions({
        baseValue: { type: "price", price: entryBase },
      });
      profitBelowRef.current.applyOptions({
        baseValue: { type: "price", price: entryBase },
      });
      lossAboveRef.current.applyOptions({
        baseValue: { type: "price", price: entryBase },
      });
      lossBelowRef.current.applyOptions({
        baseValue: { type: "price", price: entryBase },
      });

      profitAboveRef.current.setData(tradeLines.profitAboveData);
      profitBelowRef.current.setData(tradeLines.profitBelowData);
      lossAboveRef.current.setData(tradeLines.lossAboveData);
      lossBelowRef.current.setData(tradeLines.lossBelowData);
    } catch (err) {
      console.error("Charts trade lines error:", err);
      clearTradeSeries({
        entrySeriesRef,
        slSeriesRef,
        tpSeriesRef,
        profitAboveRef,
        profitBelowRef,
        lossAboveRef,
        lossBelowRef,
      });
    }
  }, [tradeLines, tradeSignature]);

  return (
    <div
      style={{
        width: "100%",
        height: 520,
        position: "relative",
        background: "#0b0f14",
      }}
    >
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: "100%",
        }}
      />
    </div>
  );
}
