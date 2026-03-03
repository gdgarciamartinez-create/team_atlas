import { useSnapshot } from "../lib/useSnapshot.js";

export default function Logs(){
  const { snap } = useSnapshot(1500);
  const logs = snap?.logs ?? [];

  return (
    <div className="card">
      <div className="cardTitle">
        <div>
          <div className="small">Logs</div>
          <div className="mono">Trazabilidad del bot</div>
        </div>
        <span className="badge">{logs.length}</span>
      </div>

      <div className="sep" />

      <div className="mono" style={{fontSize:12, lineHeight:1.65, whiteSpace:"pre-wrap"}}>
        {logs.slice(0,200).map((l, i)=>(
          <div key={i}>• {typeof l === "string" ? l : JSON.stringify(l)}</div>
        ))}
        {logs.length===0 && <div className="small">Sin logs todavía.</div>}
      </div>
    </div>
  );
}