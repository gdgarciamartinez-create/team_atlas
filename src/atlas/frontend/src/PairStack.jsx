import React from "react";

function dotTone(tone) {
  // green / yellow / red
  if (tone === "green") return "bg-emerald-400";
  if (tone === "yellow") return "bg-amber-400";
  return "bg-rose-400";
}

function chipTone(tone) {
  if (tone === "green") return "bg-emerald-500/15 text-emerald-200 border-emerald-400/20";
  if (tone === "yellow") return "bg-amber-500/15 text-amber-200 border-amber-400/20";
  return "bg-rose-500/15 text-rose-200 border-rose-400/20";
}

export default function PairStack({
  title = "Pares",
  pairs = [],
  statusBySymbol = {},
  onSelect,
  selectedSymbol,
  compact = false,
}) {
  return (
    <div className="rounded-2xl bg-white/5 border border-white/10 p-4">
      <div className="text-sm font-semibold mb-3">{title}</div>

      <div className={`flex flex-col ${compact ? "gap-1" : "gap-2"}`}>
        {pairs.map((sym) => {
          const st = statusBySymbol[sym] || {
            tone: "red",
            label: "NO SETUP",
            hint: "",
          };

          const isSelected = sym === selectedSymbol;

          return (
            <button
              key={sym}
              onClick={() => onSelect?.(sym)}
              className={[
                "w-full text-left rounded-xl border transition",
                isSelected
                  ? "bg-sky-500/15 border-sky-400/30"
                  : "bg-slate-900/50 border-white/10 hover:bg-white/5",
                compact ? "px-2 py-1" : "px-3 py-2",
              ].join(" ")}
            >
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${dotTone(st.tone)}`} />
                <div className="font-semibold text-sm">{sym}</div>

                <span
                  className={[
                    "ml-auto text-[11px] px-2 py-0.5 rounded-full border",
                    chipTone(st.tone),
                  ].join(" ")}
                >
                  {st.label}
                </span>
              </div>

              {st.hint ? (
                <div className="mt-1 text-[11px] text-slate-400">
                  {st.hint}
                </div>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}
