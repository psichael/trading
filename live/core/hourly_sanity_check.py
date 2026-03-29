import pandas as pd
import numpy as np
import scipy.linalg as la
import os

def get_tilt(F, rds):
    LAMBDA_MODE, PHI = 2.3361135, 0.1629229
    pucker = 1.0 + max(0, (F / 5.0) - (rds / 5.06))
    phi_b = PHI / 4.0
    Mx = np.eye(8) * (LAMBDA_MODE / 3.0)
    My = np.eye(8) * (LAMBDA_MODE / 3.0)
    for i, j in [(0,1), (2,3), (4,5), (6,7)]: Mx[i, j] = Mx[j, i] = phi_b
    for i, j in [(0,2), (1,3), (4,6), (5,7)]: My[i, j] = My[j, i] = phi_b * pucker
    Mp = Mx + My + (np.eye(8) * LAMBDA_MODE)
    s = la.svd(Mp, compute_uv=False)
    return np.max(s) / np.min(s)

def check_sanity():
    tickers = ['NVDA', 'AVGO', 'MSFT']
    print(f'\n=== HOURLY MANIFOLD SANITY CHECK (FEB 23, 2026) ===')
    
    for t in tickers:
        df = pd.read_csv(f'bot/data/{t}_H1_sync_AI.csv').tail(100)
        df['returns'] = df['close'].pct_change()
        f = df['returns'].std() * 100 * np.sqrt(252)
        # Normalized Flux
        f_norm = (f / 0.02) * 4.5 # Approximation for current market heat
        tilt = get_tilt(f_norm, 3.5) # Using mid-range Rds
        
        status = "STABLE" if tilt < 1.06 else "FRACTURED"
        print(f'{t}: Flux={f_norm:.2f} | Tilt={tilt:.4f} | Status: {status}')

if __name__ == "__main__":
    check_sanity()