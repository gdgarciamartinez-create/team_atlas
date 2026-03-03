import { useState, useEffect } from "react";

export function useSnapshot(ms=1500){
  const [snap, setSnap] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(()=>{
    let alive=true;
    async function tick(){
      try{
        const r = await fetch("/api/snapshot");
        if(!r.ok) throw new Error(`snapshot ${r.status}`);
        const j = await r.json();
        if(alive){ setSnap(j); setErr(null); }
      } catch(e){
        if(alive) setErr(e);
      }
    }
    tick();
    const id = setInterval(tick, ms);
    return ()=>{ alive=false; clearInterval(id); };
  }, [ms]);

  return { snap, err };
}