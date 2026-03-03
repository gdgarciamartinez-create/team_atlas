import { useMemo, useState } from "react";
import { useSnapshot } from "../lib/useSnapshot.js";
import { postJSON } from "../lib/api.js";

function pillFromBool(v, goodText, badText){
  return v ? <span className="badge good">{goodText}</span> : <span className="badge">{badText}</span>;
}

export default function Dashboard(){
  const { snap, err } = useSnapshot(1500);
  const [busy, setBusy] = useState(false);

  const status = snap?.status ?? {};
  const candidates = snap?.candidates ?? [];
  const alerts = snap?.alerts ?? [];
  const lastDecision = snap?.last_decision ?? null;

  const top3 = useMemo(()=> candidates.slice(0, 8), [candidates]);

  async function act(endpoint, body={}){
    try{
      setBusy(true);
      await postJSON(endpoint, body);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="row">
      <section className="card">
        <div className="cardTitle">
          <div>
            <div className="small">Estado</div>
            <div className="mono">{status?.mode ?? "—"} · {status?.season ?? "—"} · {status?.now_local ?? "—"}</div>
          </div>
          <div className="badges">
            {pillFromBool(status?.running, "running", "paused")}
            {pillFromBool(status?.armed, "armed", "armed=false")}
            <span className="badge">{status?.window ?? "window: —"}</span>
          </div>
        </div>

        {err && <div className="notice">No conecta a /api/snapshot (backend caído o proxy). {String(err)}</div>}
        {!snap && !err && <div className="notice">Cargando snapshot…</div>}

        <div className="sep" />

        <div className="btnRow">
          <button className="btn primary" disabled={busy} onClick={()=>act("/api/control/play")}>Play</button>
          <button className="btn" disabled={busy} onClick={()=>act("/api/control/pause")}>Pause</button>
          <button className="btn good" disabled={busy} onClick={()=>act("/api/control/arm", { armed:true })}>Arm</button>
          <button className="btn bad" disabled={busy} onClick={()=>act("/api/control/arm", { armed:false })}>Disarm</button>
          <button className="btn" disabled={busy} onClick={()=>act("/api/control/reset")}>Reset</button>
        </div>

        <div className="sep" />

        <div className="small">Última decisión</div>
        <div className="mono" style={{marginTop:6, lineHeight:1.45}}>
          {lastDecision ? JSON.stringify(lastDecision, null, 2) : "—"}
        </div>
      </section>

      <section className="card">
        <div className="cardTitle">
          <div>
            <div className="small">Candidatos</div>
            <div className="mono">Top setups detectados</div>
          </div>
          <span className="badge">{candidates.length} total</span>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>Símbolo</th>
              <th>Tipo</th>
              <th>Score</th>
              <th>Zona</th>
            </tr>
          </thead>
          <tbody>
            {top3.map((c, i)=>(
              <tr key={i}>
                <td className="mono">{c.symbol ?? "—"}</td>
                <td>{c.kind ?? "—"}</td>
                <td className="mono">{(c.score ?? 0).toFixed ? (c.score ?? 0).toFixed(2) : (c.score ?? "—")}</td>
                <td className="mono">{c.zone ? `${c.zone.low}–${c.zone.high}` : "—"}</td>
              </tr>
            ))}
            {top3.length===0 && (
              <tr><td colSpan="4" className="small">Sin candidatos todavía.</td></tr>
            )}
          </tbody>
        </table>

        <div className="sep" />

        <div className="cardTitle">
          <div>
            <div className="small">Alertas</div>
            <div className="mono">Eventos recientes</div>
          </div>
          <span className="badge">{alerts.length}</span>
        </div>
        <div className="mono" style={{fontSize:12, lineHeight:1.6}}>
          {(alerts.slice(0,10)).map((a, idx)=>(
            <div key={idx}>• {typeof a === "string" ? a : JSON.stringify(a)}</div>
          ))}
          {alerts.length===0 && <div className="small">Sin alertas.</div>}
        </div>
      </section>
    </div>
  );
}