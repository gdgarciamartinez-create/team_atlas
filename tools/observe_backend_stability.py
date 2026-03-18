from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fetch_json(base_url: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{query}"

    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def append_jsonl(path: Path, item: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(item, ensure_ascii=True) + "\n")


def summarize_samples(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    snapshot_prices = [s.get("snapshot_price") for s in samples]
    candle_times = [s.get("snapshot_candle_t") for s in samples]
    tail_pairs = [(s.get("tail_last_ts"), s.get("tail_last_event")) for s in samples]
    scan_pairs = [(s.get("scan_entries"), s.get("scan_setups"), s.get("scan_live")) for s in samples]

    return {
        "samples": len(samples),
        "snapshot_changes": len({v for v in snapshot_prices if v is not None}) > 1,
        "candle_time_changes": len({v for v in candle_times if v is not None}) > 1,
        "scan_changes": len(set(scan_pairs)) > 1,
        "tail_changes": len(set(tail_pairs)) > 1,
        "first_sample_at": samples[0].get("taken_at") if samples else None,
        "last_sample_at": samples[-1].get("taken_at") if samples else None,
    }


def collect_sample(base_url: str, world: str, atlas_mode: str, symbol: str, tail_limit: int) -> Dict[str, Any]:
    snap = fetch_json(
        base_url,
        "/api/snapshot",
        {"world": world, "atlas_mode": atlas_mode, "symbol": symbol},
    )
    scan = fetch_json(
        base_url,
        "/api/scan",
        {"world": world, "atlas_mode": atlas_mode},
    )
    tail = fetch_json(
        base_url,
        "/api/bitacora/tail",
        {"limit": tail_limit},
    )

    candles = snap.get("candles") or []
    row = ((snap.get("ui") or {}).get("rows") or [None])[0] or {}
    last_candle = candles[-1] if candles else {}
    tail_items = tail.get("items") or []
    tail_last = tail_items[-1] if tail_items else {}

    return {
        "taken_at": now_utc(),
        "snapshot_state": row.get("state"),
        "snapshot_updated_at": row.get("updated_at"),
        "snapshot_price": row.get("price"),
        "snapshot_candle_t": last_candle.get("t"),
        "snapshot_candle_c": last_candle.get("c"),
        "snapshot_candle_h": last_candle.get("h"),
        "snapshot_candle_l": last_candle.get("l"),
        "scan_entries": ((scan.get("summary") or {}).get("entries")),
        "scan_setups": ((scan.get("summary") or {}).get("setups")),
        "scan_live": ((scan.get("summary") or {}).get("live")),
        "scan_total_rows": ((scan.get("summary") or {}).get("total_rows")),
        "tail_last_ts": tail_last.get("ts"),
        "tail_last_event": tail_last.get("event"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe TEAM_ATLAS backend stability over time.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--world", default="ATLAS_IA")
    parser.add_argument("--atlas-mode", default="SCALPING_M5")
    parser.add_argument("--symbol", default="XAUUSDz")
    parser.add_argument("--interval-sec", type=int, default=300)
    parser.add_argument("--samples", type=int, default=12)
    parser.add_argument("--tail-limit", type=int, default=5)
    parser.add_argument(
        "--output",
        default="artifacts/backend_stability_observation.jsonl",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    samples: List[Dict[str, Any]] = []

    for index in range(args.samples):
        try:
            sample = collect_sample(
                base_url=args.base_url,
                world=args.world,
                atlas_mode=args.atlas_mode,
                symbol=args.symbol,
                tail_limit=args.tail_limit,
            )
            sample["sample"] = index + 1
            append_jsonl(output_path, sample)
            samples.append(sample)
            print(json.dumps(sample, ensure_ascii=True))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            error_item = {
                "taken_at": now_utc(),
                "sample": index + 1,
                "error": str(exc),
            }
            append_jsonl(output_path, error_item)
            print(json.dumps(error_item, ensure_ascii=True))

        if index < args.samples - 1:
            time.sleep(max(1, args.interval_sec))

    summary = summarize_samples(samples)
    append_jsonl(output_path, {"summary": summary, "taken_at": now_utc()})
    print(json.dumps({"summary": summary}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
