#!/usr/bin/env python3
"""
optimus_orderbook.py – ultra-fast Quidax book streamer (Python 3.9+)

Produces two rolling logs:
  • order_books.jsonl              (raw bids/asks)
  • order_books_structured.jsonl   (snapshots Optimus consumes)
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union

import aiohttp

# ──────────────────────── configuration ──────────────────────────
MARKETS: List[str] = [
    "btcngn", "ethngn", "qdxngn", "xrpngn", "dashngn",
    "ltcngn", "usdtngn", "trxngn", "cngnngn",
]
API_BASE = "https://app.quidax.io/api/v1"
DOMAINS = [API_BASE]
BIDS_LIMIT, ASK_LIMIT = 20, 20
ROUND_TIME = 0.5       # seconds for one full batch
HTTP_TIMEOUT = 8       # per-request timeout
MAX_BACKOFF = 4.0      # when everything fails
RATE_LIMIT = 4         # max requests per second
# ─────────────────────────────────────────────────────────────────


def utc_iso() -> str:
    ts = datetime.now(timezone.utc)
    return f"{ts:%Y-%m-%dT%H:%M:%S}.{ts.microsecond:06d}Z"


def _norm(levels: Any) -> List[List[str]]:
    """convert Quidax level formats → [[qty, price], …]"""
    out: List[List[str]] = []
    for lv in levels:
        try:
            if isinstance(lv, list) and len(lv) >= 2:            # [price, qty]
                price, qty = str(lv[0]), str(lv[1])
            elif isinstance(lv, dict):                           # {"price": …}
                price = lv.get("price") or lv.get("rate") or lv.get("p")
                qty   = lv.get("quantity") or lv.get("volume") or lv.get("amount")
                if price is None or qty is None:
                    continue
                price, qty = str(price), str(qty)
            else:
                continue
            if float(price) > 0 and float(qty) > 0:
                out.append([qty, price])
        except Exception:
            continue
    return out


REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)


async def fetch_one(session: aiohttp.ClientSession,
                    market: str) -> Dict[str, Any]:
    params = {"bids_limit": BIDS_LIMIT, "ask_limit": ASK_LIMIT}
    last_exc: Exception | None = None
    for base in DOMAINS:
        url = f"{base}/markets/{market}/order_book"
        try:
            async with session.get(url, params=params,
                                   timeout=REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                data = (await resp.json())["data"]
                return {
                    "security": market.upper(),
                    "bids": _norm(data.get("bids", [])),
                    "offers": _norm(data.get("asks", [])),
                }
        except Exception as exc:
            last_exc = exc
    raise last_exc if last_exc else RuntimeError("all domains failed")


# gather() may return BaseException, so use this alias
Result = Union[Dict[str, Any], BaseException]


async def stream(out_dir: Path, do_fsync: bool, token: str) -> None:
    raw_fp = (out_dir / "order_books.jsonl").open("a", buffering=1)
    str_fp = (out_dir / "order_books_structured.jsonl").open("a", buffering=1)

    backoff = 0.4
    connector = aiohttp.TCPConnector(limit=RATE_LIMIT,
                                     ttl_dns_cache=300, ssl=False)
    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession(connector=connector,
                                     headers=headers) as session:
        while True:
            t0 = time.perf_counter()

            tasks = [fetch_one(session, m) for m in MARKETS]
            results: List[Result] = await asyncio.gather(
                *tasks, return_exceptions=True)

            any_ok = False
            for market, res in zip(MARKETS, results):
                if isinstance(res, BaseException):
                    sys.stderr.write(f"[Error] {market}: {res}\n")
                    continue

                any_ok = True
                # raw log
                raw_fp.write(json.dumps({"bids": res["bids"],
                                         "offers": res["offers"]},
                                        separators=(",", ":")) + "\n")

                snap: Dict[str, Any] = {
                    "timestamp": utc_iso(),
                    **res,
                }
                if res["bids"]:
                    snap["best_bid"] = res["bids"][0][1]
                if res["offers"]:
                    snap["best_offer"] = res["offers"][0][1]

                str_fp.write(json.dumps(snap, separators=(",", ":")) + "\n")

            if any_ok:
                raw_fp.flush(); str_fp.flush()
                if do_fsync:
                    os.fsync(raw_fp.fileno()); os.fsync(str_fp.fileno())
                backoff = 0.4
            else:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, MAX_BACKOFF)

            # throttle to RATE_LIMIT req/sec
            await asyncio.sleep(max(0.0, ROUND_TIME - (time.perf_counter() - t0)))

    raw_fp.close(); str_fp.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Async Quidax book streamer")
    ap.add_argument("--out-dir", default=os.getcwd(),
                    help="directory for *.jsonl files (default: CWD)")
    ap.add_argument("--fsync", action="store_true",
                    help="fsync after each batch (safer, slower)")
    args = ap.parse_args()

    token = os.getenv("QUIDAX_API_SECRET", "").strip()
    if not token:
        print("Error: please set QUIDAX_API_SECRET in your environment", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(stream(Path(args.out_dir), args.fsync, token))
    except KeyboardInterrupt:
        print("\n[optimus_orderbook] stopped by user")


if __name__ == "__main__":
    main()