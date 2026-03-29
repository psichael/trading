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
    pass # Obsolete block bypassed in simulation