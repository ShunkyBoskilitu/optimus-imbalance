# optimus-imbalance: Empirical Limit Order Book Imbalance Analysis on Quidax

**Author**: Christian Akolade Adegboyega (Ricardian Corp / Bells University of Technology)  
**Repository**: `github.com/ShunkyBoskilitu/optimus-imbalance`  
**Dataset**: 121,758 Level-2 order book snapshots across 9 crypto-naira markets on Quidax (BTC, ETH, XRP, USDT, LTC, TRX, DASH, QDX, cNGN).

---

## 1. Repository Structure & Scripts

| Path | Description |
|---|---|
| [`src/optimus_orderbook.py`](src/optimus_orderbook.py) | Level-2 streaming order book collector for Quidax WebSocket API |
| [`src/clean_and_score.py`](src/clean_and_score.py) | Data cleaning, crossed-book filtering, and depth imbalance evaluation |
| [`src/block_bootstrap.py`](src/block_bootstrap.py) | Stationary block bootstrap (60s blocks) correcting for book state autocorrelation |
| [`src/brier_baseline.py`](src/brier_baseline.py) | Probabilistic forecast scoring, calibration curves, and Brier skill score computation |
| [`src/avellaneda_stoikov.py`](src/avellaneda_stoikov.py) | Avellaneda-Stoikov market-making model and arrival intensity calibration on ETH/NGN |
| [`src/decentralized_mesh.py`](src/decentralized_mesh.py) | Peer-to-peer liquidity mesh simulation and gossip communication overhead profiling |
| [`data/results_summary.json`](data/results_summary.json) | Disaggregated empirical results, sample sizes, and confidence intervals across 9 pairs |

---

## 2. Key Finding: The Inverted Depth Imbalance Signal
We evaluated a canonical high-frequency order book depth imbalance indicator:
$$\rho = \frac{V_{\text{bid}} - V_{\text{ask}}}{V_{\text{bid}} + V_{\text{ask}}}$$
where an imbalance $\rho > 0.60$ issues a buy call (predicting an upward mid-price movement) and $\rho < -0.60$ issues a sell call.

Across **104,196 clean snapshots** (after filtering 15,181 crossed books and 1,368 empty books), the rule fired **5,138 times**. In the **1,696 instances** where the mid-price subsequently moved within 5 seconds ($h=1$ step):
- **Directional Accuracy**: **21.1%** ($k = 358 / 1,696$)
- **Wilson 95% Confidence Interval**: **[19.2%, 23.1%]**
- **Block Bootstrap 95% CI (60s blocks)**: **[19.4%, 22.9%]**
- **Forecast Quality**: Brier Score = 0.7889 vs. Base-rate Prior = 0.2461 (Brier Skill Score: **-2.21**)

The signal is **reliably and statistically significantly inverted** ($p < 10^{-15}$). Rather than predicting continuation, large visible queue depth on an emerging market order book signals adverse selection and queue depletion.

---

## 3. Per-Market Breakdown (Horizon $h=1$)
| Market | Firings with Move | Directional Accuracy | Interpretation |
|---|:---:|:---:|---|
| **ETH/NGN** | 461 | **36.4%** | Relatively liquid; less inverted |
| **BTC/NGN** | 135 | **28.9%** | Moderate liquidity |
| **XRP/NGN** | 280 | **27.5%** | Moderate liquidity |
| **LTC/NGN** | 328 | **11.0%** | Heavily inverted; thin touch |
| **TRX/NGN** | 374 | **9.1%** | Heavily inverted; wide spreads |
| **DASH/NGN** | 9 | **11.1%** | Extremely illiquid |
| **QDX/NGN** | 109 | **2.8%** | Native exchange token; complete adverse selection |

---

## 4. Deliberate Non-Claims (Scientific Restraint)
1. **No Trading P&L Claimed**: We evaluated purely directional mid-price movements. Because the touch is thin and spreads on these books range from 15 to 120 bps, a directional prediction does not imply an executable trading strategy. Simulating P&L without modeling fill probabilities and queue priority would report an empirical counting exercise as money.
2. **No Claim of General Market Law**: The inversion is heavily concentrated in illiquid books where quote updates are slow ($>2$ seconds). Pooling all markets creates an aggregation artifact.

---

## 5. Replication
```bash
# Clone the repository
git clone https://github.com/ShunkyBoskilitu/optimus-imbalance.git
cd optimus-imbalance

# Run cleaning and scoring pipeline
python3 src/clean_and_score.py

# Run temporal block bootstrap (stationary 60s blocks)
python3 src/block_bootstrap.py

# Run probabilistic forecast verification and Brier skill score calibration
python3 src/brier_baseline.py

# Run Avellaneda-Stoikov inventory skew and arrival intensity calibration
python3 src/avellaneda_stoikov.py

# Run decentralized liquidity mesh consensus simulation
python3 src/decentralized_mesh.py
```

<!-- verified for replication -->
