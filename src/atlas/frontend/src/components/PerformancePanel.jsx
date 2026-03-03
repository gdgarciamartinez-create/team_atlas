// src/atlas/frontend/src/components/PerformancePanel.jsx
import React from "react";

function fmtPct(x) {
  if (x === null || x === undefined) return "—";
  return `${(x * 100).toFixed(1)}%`;
}

function fmtNum(x, d = 2) {
  if (x === null || x === undefined) return "—";
  return Number(x).toFixed(d);
}

export default function PerformancePanel({ perf }) {
  const matrix = perf?.matrix;

  if (!matrix || matrix?.message) {
    return (
      <div className="rounded-xl bg-slate-900/60 border border-white/10 p-3">
        <div className="text-xs text-slate-400">Performance</div>
        <div className="text-sm text-slate-200 mt-1">No data todavía 🧪</div>
      </div>
    );
  }

  const symbols = Object.keys(matrix);
  if (!symbols.length) {
    return (
      <div className="rounded-xl bg-slate-900/60 border border-white/10 p-3">
        <div className="text-xs text-slate-400">Performance</div>
        <div className="text-sm text-slate-200 mt-1">No data todavía 🧪</div>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-slate-900/60 border border-white/10 p-3">
      <div className="text-xs text-slate-400 mb-2">Performance (Activo → Estado)</div>

      <div className="space-y-3">
        {symbols.map((sym) => {
          const states = matrix[sym] || {};
          return (
            <div key={sym} className="rounded-xl bg-white/5 border border-white/10 p-3">
              <div className="text-sm font-semibold">{sym}</div>

              <div className="mt-2 space-y-2">
                {Object.entries(states).map(([stateName, s]) => (
                  <div key={stateName} className="rounded-xl bg-slate-950/40 border border-white/10 p-2">
                    <div className="text-xs font-semibold text-slate-200">{stateName}</div>

                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-300">
                      <div>
                        <div className="text-slate-500">Trades</div>
                        <div className="text-slate-100 font-semibold">{s.trades ?? "—"}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">TP1</div>
                        <div className="text-slate-100 font-semibold">{fmtPct(s.winrate_tp1)}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">SL</div>
                        <div className="text-slate-100 font-semibold">{fmtPct(s.sl_rate)}</div>
                      </div>

                      <div>
                        <div className="text-slate-500">Avg R</div>
                        <div className="text-slate-100 font-semibold">{fmtNum(s.avg_R, 2)}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Med R</div>
                        <div className="text-slate-100 font-semibold">{fmtNum(s.median_R, 2)}</div>
                      </div>
                      <div>
                        <div className="text-slate-500">Min a TP1</div>
                        <div className="text-slate-100 font-semibold">{fmtNum(s.avg_time_to_tp1, 1)}</div>
                      </div>
                    </div>
                  </div>
                ))}

                {Object.keys(states).length === 0 ? (
                  <div className="text-xs text-slate-400">No data en este activo.</div>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
