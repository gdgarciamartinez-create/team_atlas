import { useState } from "react";
import { postJSON } from "../lib/api.js";
import { useSnapshot } from "../lib/useSnapshot.js";

export default function Config(){
  const { snap } = useSnapshot(2000);
  const [busy, setBusy] = useState(false);

  const cfg = snap?.config ?? { season:"winter", mode:"lab" };

  async function setConfig(patch){
    try{
      setBusy(true);
      await postJSON("/api/control/config", patch);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="cardTitle">
        <div>
          <div className="small">Configuración</div>
          <div className="mono">Invierno/Verano + modo laboratorio</div>
        </div>
        <span className="badge">Config live</span>
      </div>

      <div className="sep" />

      <div className="btnRow">
        <button className="btn primary" disabled={busy} onClick={()=>setConfig({ season:"winter" })}>Invierno (Chile)</button>
        <button className="btn primary" disabled={busy} onClick={()=>setConfig({ season:"summer" })}>Verano (Chile)</button>
        <button className="btn" disabled={busy} onClick={()=>setConfig({ mode:"lab" })}>Modo LAB</button>
      </div>

      <div className="sep" />
      <div className="small">Actual</div>
      <div className="mono" style={{marginTop:6}}>{JSON.stringify(cfg, null, 2)}</div>

      <div className="sep" />
      <div className="notice">
        Nota: no se agregan reglas nuevas acá. Solo UI real para controlar estado.
      </div>
    </div>
  );
}