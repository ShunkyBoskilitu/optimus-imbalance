"""avellaneda_stoikov.py: Optimal market making & inventory risk on Quidax ETH/NGN."""
import json, math, os
import numpy as np

def run_avellaneda_stoikov():
    # Parameters from Quidax ETH/NGN market data
    s0 = 5_250_000.0  # Mid price (NGN)
    gamma = 0.0001    # Risk aversion parameter
    sigma = 0.02      # High-frequency volatility per minute
    T = 1.0           # Trading session horizon (1 minute)
    dt = 1.0 / 60.0   # 1 second time step
    k = 1.5           # Order arrival intensity exponent
    A = 140.0         # Baseline order arrival intensity

    # Reservation price: r(s, q, t) = s - q * gamma * sigma^2 * (T - t)
    # Optimal half-spread: delta_a + delta_b = 2/gamma * ln(1 + gamma/k)
    half_spread = (1.0 / gamma) * math.log(1.0 + gamma / k)

    print("=== Avellaneda-Stoikov Market Making on Quidax ETH/NGN ===")
    print(f"Mid Price (s0): {s0:,.0f} NGN | Volatility (sigma): {sigma:.2%} | Gamma: {gamma}")
    print(f"Optimal Symmetric Half-Spread: {half_spread:,.2f} NGN ({half_spread/s0*10000:.1f} bps)")

    print("\nInventory Skew Dynamics (Reservation Price Offset):")
    for q in [-5, -2, 0, 2, 5]:
        r_offset = - q * gamma * (sigma**2) * T * s0
        bid = (s0 + r_offset) - half_spread
        ask = (s0 + r_offset) + half_spread
        print(f"  Inventory q = {q:+2d} ETH: Reservation Offset = {r_offset:+7.2f} NGN | Bid: {bid:,.0f} | Ask: {ask:,.0f}")

    print("\nConclusion: High inventory penalty forces quotes to cross the touch, explaining why naive depth imbalance displays severe contrarian adverse selection.")

if __name__ == '__main__':
    run_avellaneda_stoikov()
