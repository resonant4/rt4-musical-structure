#!/usr/bin/env python3
"""
RT⁴ Duration from Geometry
--------------------------
Hypothesis: note durations should emerge from orbital geometry,
not be uniform. We derive durations from |dz/dt| and |dr/dt|
along the toroidal helix orbit.

Orbit equations:
  z(t) = h · sin(2π·ω·t/n + ψ)
  r(t) = R + a · cos(2π·ξ·t/n)

where ω = k (poloidal winds), ξ = 1 (toroidal), n = chromatic steps,
h = poloidal amplitude, a = toroidal amplitude, R = major radius.
"""

import numpy as np
from math import gcd

# ── Helpers ──────────────────────────────────────────────────────

def rt4_orbit(n, k, h=1.0, a=0.3, R=1.0, psi=0.0):
    """Compute pitch classes, z-velocity, r-velocity at each step."""
    omega = k
    xi = 1
    t = np.arange(n)
    
    # Pitch sequence (Bresenham / step-accumulate mod n)
    pitches = [(i * k) % n for i in range(n)]
    
    # Velocities (derivatives)
    dz = h * (2 * np.pi * omega / n) * np.cos(2 * np.pi * omega * t / n + psi)
    dr = -a * (2 * np.pi * xi / n) * np.sin(2 * np.pi * xi * t / n)
    
    # Speed (magnitude of tangent vector component)
    speed = np.sqrt(dz**2 + dr**2)
    
    return pitches, np.abs(dz), np.abs(dr), speed


def durations_inverse(speed, base=1.0, alpha=1.0):
    """Fast motion → short notes: dur = base / (1 + α·speed)"""
    return base / (1 + alpha * speed)


def durations_legato(speed, base=1.0, beta=1.0):
    """Fast motion → long notes: dur = base · (1 + β·speed)"""
    return base * (1 + beta * speed)


def normalize_ratios(durs):
    """Normalize to minimum = 1.0 for ratio display."""
    mn = durs.min()
    if mn > 0:
        return durs / mn
    return durs


def detect_swing(ratios):
    """Check if alternating long-short pattern exists (swing feel)."""
    if len(ratios) < 4:
        return False, 0
    pairs = ratios[:len(ratios) - len(ratios) % 2].reshape(-1, 2)
    # Check if consistently long-short or short-long
    diffs = pairs[:, 0] - pairs[:, 1]
    if np.all(diffs > 0.05) or np.all(diffs < -0.05):
        avg_ratio = np.mean(pairs[:, 0] / pairs[:, 1])
        return True, avg_ratio
    return False, 0


def detect_dotted(ratios, tol=0.1):
    """Check for ~3:1 or ~2:1 ratios (dotted rhythm signatures)."""
    found = []
    for i in range(len(ratios) - 1):
        r = ratios[i] / ratios[i + 1] if ratios[i + 1] > 0.01 else 0
        if abs(r - 3.0) < tol:
            found.append((i, '3:1 (dotted quarter)'))
        elif abs(r - 2.0) < tol:
            found.append((i, '2:1 (dotted eighth)'))
        elif abs(r - 1.5) < tol:
            found.append((i, '3:2 (hemiola)'))
    return found


def analyze_syncopation(ratios):
    """Simple syncopation metric: variance of duration ratios."""
    return float(np.std(ratios) / np.mean(ratios))  # CV


def find_nearest_musical(ratio):
    """Snap ratio to nearest common musical duration ratio."""
    musical = {
        1.0: '1', 1.5: '3/2 (dotted)', 2.0: '2', 3.0: '3 (dotted quarter)',
        0.5: '1/2', 0.667: '2/3 (triplet)', 0.75: '3/4',
        1.333: '4/3', 0.333: '1/3 (triplet)'
    }
    closest = min(musical.keys(), key=lambda x: abs(x - ratio))
    if abs(closest - ratio) < 0.15:
        return musical[closest]
    return f'{ratio:.2f}'


# ── Main Analysis ────────────────────────────────────────────────

def analyze_case(n, k, label=""):
    print(f"\n{'='*60}")
    print(f"  {label}n={n}, k={k}  |  gcd={gcd(n,k)}  |  pitch classes: {n // gcd(n,k)}")
    print(f"{'='*60}")
    
    pitches, abs_dz, abs_dr, speed = rt4_orbit(n, k)
    
    print(f"\nPitch sequence: {pitches}")
    print(f"|dz/dt|: {np.round(abs_dz, 3)}")
    print(f"|dr/dt|: {np.round(abs_dr, 3)}")
    print(f"speed:   {np.round(speed, 3)}")
    
    results = {}
    
    for mode_name, dur_fn, param_name, param_val in [
        ("INVERSE (fast=short)", durations_inverse, "α", 1.0),
        ("INVERSE (α=2)", durations_inverse, "α", 2.0),
        ("LEGATO (fast=long)", durations_legato, "β", 1.0),
    ]:
        if "INVERSE" in mode_name:
            durs = dur_fn(speed, alpha=param_val)
        else:
            durs = dur_fn(speed, beta=param_val)
        
        ratios = normalize_ratios(durs)
        musical = [find_nearest_musical(r) for r in ratios]
        
        swing, swing_ratio = detect_swing(ratios)
        dotted = detect_dotted(ratios)
        sync_cv = analyze_syncopation(ratios)
        
        print(f"\n  ── {mode_name} ({param_name}={param_val}) ──")
        print(f"  Duration ratios: {np.round(ratios, 3)}")
        print(f"  Musical approx:  {musical}")
        print(f"  Swing detected:  {swing} (ratio: {swing_ratio:.3f})" if swing else f"  Swing: No")
        print(f"  Dotted patterns: {dotted}" if dotted else "  Dotted: None")
        print(f"  Syncopation CV:  {sync_cv:.4f}")
        print(f"  Duration range:  {ratios.min():.3f} – {ratios.max():.3f} ({ratios.max()/ratios.min():.2f}x)")
        
        results[mode_name] = {
            'ratios': ratios, 'musical': musical, 'swing': swing,
            'swing_ratio': swing_ratio, 'dotted': dotted, 'sync_cv': sync_cv
        }
    
    return results


if __name__ == "__main__":
    print("RT⁴ Duration from Geometry - Research")
    print("=" * 60)
    
    cases = [
        (12, 7, "Diatonic: "),
        (60, 23, "Microtonal 60-TET: "),
        (24, 7, "Quarter-tone: "),
    ]
    
    all_results = {}
    for n, k, label in cases:
        all_results[(n, k)] = analyze_case(n, k, label)
    
    # ── Cross-case comparison ──
    print(f"\n\n{'='*60}")
    print("  CROSS-CASE COMPARISON")
    print(f"{'='*60}")
    
    for (n, k), results in all_results.items():
        inv = results["INVERSE (fast=short)"]
        print(f"\n  n={n}, k={k}:")
        print(f"    Inverse sync CV: {inv['sync_cv']:.4f}")
        print(f"    Swing: {inv['swing']} | Dotted count: {len(inv['dotted'])}")
        print(f"    Unique ratio clusters: {len(set(np.round(inv['ratios'], 2)))}")
    
    # ── Key insight: relationship between k/n and rhythm complexity ──
    print(f"\n\n{'='*60}")
    print("  KEY FINDINGS")
    print(f"{'='*60}")
    print("""
    The orbital velocity varies sinusoidally with frequency ω=k,
    creating k peaks and k troughs per cycle of n steps.
    
    This means:
    - n=12, k=7: 7 fast/slow cycles in 12 steps → complex phase
    - n=60, k=23: 23 cycles in 60 steps → very fine rhythm variation  
    - n=24, k=7: 7 cycles in 24 steps → moderate complexity
    
    The ratio k/n determines the rhythm's "grain":
    - k/n ≈ 0.583 (12,7): pentatonic-like rhythm density
    - k/n ≈ 0.383 (60,23): finer but fewer peaks per step
    - k/n ≈ 0.292 (24,7): sparser rhythm accents
    """)
