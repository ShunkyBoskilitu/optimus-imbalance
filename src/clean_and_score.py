"""clean_and_score.py: Clean Quidax LOB snapshots and score the Depth Imbalance Rule."""
import json, math, collections, os
from datetime import datetime

DATA_PATH = os.environ.get("OPTIMUS_DATA_PATH", "/Users/MAC/Desktop/}/Optimus/order_books_structured.jsonl")

def run_analysis(path=DATA_PATH):
    if not os.path.exists(path):
        print(f"Data file not found at {path}. Please set OPTIMUS_DATA_PATH.")
        return

    books = collections.defaultdict(list)
    drop = collections.Counter()
    for line in open(path):
        try:
            r = json.loads(line)
            s = r["security"]
            bids = [(float(q), float(p)) for q, p in r["bids"]]
            asks = [(float(q), float(p)) for q, p in r["offers"]]
            if not bids or not asks: drop["empty"] += 1; continue
            bb, bo = float(r["best_bid"]), float(r["best_offer"])
            if abs(bids[0][1] - bb) > 1e-9 or abs(asks[0][1] - bo) > 1e-9: drop["top_mismatch"] += 1; continue
            if bb >= bo: drop["crossed"] += 1; continue
            t = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")).timestamp()
            books[s].append((t, bids, asks))
        except Exception:
            drop["bad"] += 1

    def iobi(b, a):
        B = sum(int(q) for q, p in b if int(q) > 0)
        A = sum(int(q) for q, p in a if int(q) > 0)
        return None if B + A == 0 else (B - A) / (B + A)

    def wilson(k, n, z=1.96):
        p = k / n; d = 1 + z*z/n; c = p + z*z/(2*n); h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))
        return (c-h)/d, (c+h)/d

    MAXGAP = 5.0
    tot = [0, 0, 0] # [moved, correct, fired]
    per = collections.defaultdict(lambda: [0, 0])

    for s, rows in sorted(books.items()):
        rows.sort(key=lambda x: x[0])
        gaps = [rows[i+1][0] - rows[i][0] for i in range(len(rows) - 1)]
        mids = [(b[0][1] + a[0][1]) / 2 for _, b, a in rows]
        for i in range(len(rows) - 1):
            if gaps[i] > MAXGAP: continue
            dm = mids[i+1] - mids[i]
            x = iobi(rows[i][1], rows[i][2])
            if x is None or abs(x) <= 0.6: continue
            tot[2] += 1
            if dm == 0: continue
            tot[0] += 1
            correct = ((dm > 0) == (x > 0))
            if correct: tot[1] += 1
            per[s][0] += 1
            if correct: per[s][1] += 1

    n, k, fired = tot
    lo, hi = wilson(k, n)
    print(f"Cleaned Snapshots: {sum(len(v) for v in books.values())} | Dropped: {dict(drop)}")
    print(f"Rule Fired: {fired} times | Mid Moved: {n} ({100*n/fired:.1f}%)")
    print(f"Directional Accuracy: {k/n:.3f} [{lo:.3f}, {hi:.3f}] (Wilson 95% CI)")
    print("\nPer-Market Results (Horizon h=1):")
    for s, (mn, mk) in sorted(per.items()):
        print(f"  {s:8}: {mn:5d} moves | Accuracy: {mk/mn:.3f}")

if __name__ == '__main__':
    run_analysis()
