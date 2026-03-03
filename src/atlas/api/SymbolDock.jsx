export default function SymbolDock({ symbols=[], active, onPick, mapState }){
  return (
    <div className="dock">
      {symbols.map(sym=>{
        const st = mapState(sym); // {state, mode, note}
        const lightClass = st.state === "red" ? "red" : st.state === "green" ? "green" : "none";
        return (
          <div
            key={sym}
            className={"sym" + (sym===active ? " active" : "")}
            onClick={()=>onPick(sym)}
          >
            <div className="symTop">
              <div className="symName">{sym}</div>
              <span className={"light " + lightClass} />
            </div>
            <div className="symMeta">
              {st.mode ? st.mode : "—"} · {st.note ? st.note : "nada"}
            </div>
          </div>
        );
      })}
      {symbols.length===0 && <div className="small">Sin universo</div>}
    </div>
  );
}
