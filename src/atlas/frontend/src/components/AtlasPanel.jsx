import React from "react";

export default function AtlasPanel({ snapshot }) {
  return (
    <div className="atlas-card">
      <div className="atlas-card-title">Atlas Panel</div>

      <pre className="atlas-pre" style={{ maxHeight: 220 }}>
        {JSON.stringify(
          {
            world: snapshot?.world,
            atlas_mode: snapshot?.atlas_mode,
            symbol: snapshot?.symbol,
            tf: snapshot?.tf,
            count: snapshot?.count,
            ok: snapshot?.ok,
            error: snapshot?.error ?? null,
          },
          null,
          2
        )}
      </pre>
    </div>
  );
}
