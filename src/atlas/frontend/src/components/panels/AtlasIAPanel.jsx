// src/atlas/frontend/src/components/panels/AtlasIAPanel.jsx
import { Card, Field, Input, Btn, Select, Badge } from "../ui";
import { estimateLot, riskUsd, fmtPrice } from "../../utils/format";
import { useMemo, useState } from "react";

const GATILLOS = [
  "Toque directo (zona)",
  "Barrida + recuperación",
  "Ruptura + retest",
];

export default function AtlasIAPanel({ snapshot, symbol, atlasMode }) {
  const [entry, setEntry] = useState("");
  const [sl, setSl] = useState("");
  const [tp1, setTp1] = useState("");
  const [tfGatillo, setTfGatillo] = useState("M5");
  const [gatillo, setGatillo] = useState(GATILLOS[1]);
  const [riskPct, setRiskPct] = useState("1.0");
  const [armed, setArmed] = useState(false);

  const candles = Array.isArray(snapshot?.candles) ? snapshot.candles : [];
  const tone = candles.length ? "OK" : "WAIT";

  const equity = 10000;
  const riskUsdVal = riskUsd({ equity, riskPct: Number(riskPct) || 1.0 });
  const lot = estimateLot({ symbol, entry: Number(entry), sl: Number(sl), equity, riskPct: Number(riskPct) || 1.0 });

  const msg = useMemo(() => {
    // sin inventar: usamos note/state/bias si están
    const state = snapshot?.analysis?.logic?.state || "WAIT";
    const bias = snapshot?.analysis?.logic?.bias || "NEUTRAL";
    const note = snapshot?.analysis?.logic?.note || "—";
    return `${state} • ${bias} • ${note}`;
  }, [snapshot]);

  return (
    <Card
      title={`RESEÑA ATLAS IA (${atlasMode})`}
      subtitle="Cuenta base: 10k | Riesgo 1% o 1.5% (según tipo de trade)"
      right={<Badge tone={armed ? "WAIT" : tone} text={armed ? "RUN" : tone} />}
    >
      <Field label="Símbolo" value={symbol} />
      <Field label="Lectura" value={msg} />

      <div style={{ height: 10 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>TF gatillo esperado</div>
          <Select value={tfGatillo} onChange={setTfGatillo} options={["M1", "M3", "M5"]} />
        </div>
        <div>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>Gatillo esperado</div>
          <Select value={gatillo} onChange={setGatillo} options={GATILLOS} />
        </div>
      </div>

      <div style={{ height: 10 }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>Entry</div>
          <Input value={entry} onChange={setEntry} placeholder="—" />
        </div>
        <div>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>SL</div>
          <Input value={sl} onChange={setSl} placeholder="—" />
        </div>
        <div>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>TP1</div>
          <Input value={tp1} onChange={setTp1} placeholder="—" />
        </div>
        <div>
          <div style={{ fontSize: 12, opacity: 0.75, marginBottom: 6 }}>Riesgo %</div>
          <Select value={riskPct} onChange={setRiskPct} options={["1.0", "1.5"]} />
        </div>
      </div>

      <div style={{ height: 10 }} />
      <Field label="Riesgo USD" value={`$${riskUsdVal.toFixed(2)}`} />
      <Field label="Lotaje (estimado)" value={lot ? lot.toFixed(2) : "—"} />
      <Field label="Entry (formato)" value={entry ? fmtPrice(symbol, entry) : "—"} />
      <Field label="SL (formato)" value={sl ? fmtPrice(symbol, sl) : "—"} />
      <Field label="TP1 (formato)" value={tp1 ? fmtPrice(symbol, tp1) : "—"} />

      <div style={{ height: 10 }} />
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Btn tone={armed ? "red" : "green"} onClick={() => setArmed(!armed)}>
          {armed ? "SAFE (LAB)" : "RUN"}
        </Btn>
        <Btn tone="ghost" onClick={() => { setEntry(""); setSl(""); setTp1(""); }}>
          Limpiar parámetros
        </Btn>
      </div>
    </Card>
  );
}
