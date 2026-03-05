#!/usr/bin/env python3
"""
RT⁴ Real Musical Quality Metric and Scaling Laws
================================================
Post-red-team rebuild. The old entropy metric rewarded randomness.
This uses musicologically grounded sub-metrics.
"""

import numpy as np
from math import gcd, pi, log, sqrt
from collections import Counter
import json
import sys

# ─── RT⁴ Orbit Generation ───────────────────────────────────────────────

def build_pitch_orbit(n, k, omega=0, xi=0, psi=0.0, length=None):
    """
    Build RT⁴ orbit mapped to MIDI pitches.
    
    θ_t = 2π·k·t/n  → pitch class = floor(12·k·t/n) mod 12
    z_t = sin(2π·ω·t/n + ψ) → octave offset
    r_t = cos(2π·ξ·t/n) → velocity (not used for pitch quality)
    
    Returns list of MIDI note numbers.
    """
    if length is None:
        length = n // gcd(n, k)  # one full orbit
    
    orbit = []
    for t in range(length):
        # Pitch class from θ
        pc = int(12 * k * t / n) % 12
        
        # Octave from z
        if omega == 0:
            octave = 4  # middle octave
        else:
            phi = 2 * pi * omega * t / n + psi
            z = np.sin(phi)
            # Map z ∈ [-1, 1] to octave offset ∈ [-2, 2]
            octave = 4 + round(2 * z)
        
        midi = 12 * octave + pc
        orbit.append(midi)
    
    return orbit


def build_pitch_orbit_continuous(n, k, omega=0, psi=0.0, length=None):
    """
    Build orbit with continuous pitch (no scale snapping).
    Returns raw pitch values for crystallization analysis.
    """
    if length is None:
        length = n // gcd(n, k)
    
    pitches = []
    for t in range(length):
        theta = 2 * pi * k * t / n
        pc_continuous = (theta / (2 * pi)) * n  # position in n-EDO
        pc_quantized = round(pc_continuous) % n
        pitches.append(pc_quantized)
    
    return pitches


# ─── Musical Quality Sub-Metrics ────────────────────────────────────────

CONSONANT_INTERVALS = {0, 3, 4, 5, 7, 8, 9, 12}  # unison, m3, M3, P4, P5, m6, M6, octave

def stepwise_ratio(orbit):
    """Fraction of intervals that are stepwise (≤ 3 semitones)."""
    if len(orbit) < 2:
        return 0.0
    intervals = [abs(orbit[i+1] - orbit[i]) for i in range(len(orbit)-1)]
    if not intervals:
        return 0.0
    step_count = sum(1 for iv in intervals if iv <= 3)
    return step_count / len(intervals)


def leap_compensation_ratio(orbit):
    """Fraction of leaps (>3 semitones) followed by contrary-direction step (≤3)."""
    if len(orbit) < 3:
        return 0.0
    
    leaps = 0
    compensated = 0
    
    for i in range(len(orbit) - 2):
        iv1 = orbit[i+1] - orbit[i]
        iv2 = orbit[i+2] - orbit[i+1]
        
        if abs(iv1) > 3:  # it's a leap
            leaps += 1
            # Check: contrary direction AND stepwise
            if abs(iv2) <= 3 and iv1 * iv2 < 0:
                compensated += 1
    
    return compensated / leaps if leaps > 0 else 1.0  # no leaps = perfect


def range_score(orbit):
    """Score based on melodic range. 1.0 for ≤18 semitones, declining after."""
    if not orbit:
        return 0.0
    r = max(orbit) - min(orbit)
    if r <= 18:
        return 1.0
    elif r <= 36:
        return 1.0 - (r - 18) / 36  # linear decline
    else:
        return 0.0


def consonance_ratio(orbit):
    """Fraction of intervals (mod 12) that are consonant."""
    if len(orbit) < 2:
        return 0.0
    intervals = [abs(orbit[i+1] - orbit[i]) % 12 for i in range(len(orbit)-1)]
    if not intervals:
        return 0.0
    consonant_count = sum(1 for iv in intervals if iv in CONSONANT_INTERVALS)
    return consonant_count / len(intervals)


def contour_variety(orbit):
    """Entropy of up/down/same contour distribution. Normalized to [0,1]."""
    if len(orbit) < 2:
        return 0.0
    
    directions = []
    for i in range(len(orbit) - 1):
        diff = orbit[i+1] - orbit[i]
        if diff > 0:
            directions.append('up')
        elif diff < 0:
            directions.append('down')
        else:
            directions.append('same')
    
    counts = Counter(directions)
    total = len(directions)
    probs = [c / total for c in counts.values()]
    entropy = -sum(p * log(p + 1e-12) for p in probs)
    max_entropy = log(3)  # 3 categories
    
    return entropy / max_entropy if max_entropy > 0 else 0.0


def monotony_penalty(orbit):
    """Penalty for long runs of the same note. Returns value in [0, 1]."""
    if len(orbit) < 2:
        return 0.0
    
    max_run = 1
    cur_run = 1
    for i in range(1, len(orbit)):
        if orbit[i] == orbit[i-1]:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 1
    
    # Penalize runs > 2 notes
    if max_run <= 2:
        return 0.0
    elif max_run <= 4:
        return (max_run - 2) / 4
    else:
        return min(1.0, (max_run - 2) / 6)


def musical_quality(orbit, weights=None):
    """
    Composite musical quality metric.
    Returns (total_score, sub_scores_dict).
    """
    if weights is None:
        weights = {'stepwise': 1.0, 'leap_comp': 1.0, 'range': 1.0,
                   'consonance': 1.0, 'contour': 1.0, 'monotony': 1.0}
    
    s = {
        'stepwise': stepwise_ratio(orbit),
        'leap_comp': leap_compensation_ratio(orbit),
        'range': range_score(orbit),
        'consonance': consonance_ratio(orbit),
        'contour': contour_variety(orbit),
        'monotony': monotony_penalty(orbit),
    }
    
    total = (weights['stepwise'] * s['stepwise']
           + weights['leap_comp'] * s['leap_comp']
           + weights['range'] * s['range']
           + weights['consonance'] * s['consonance']
           + weights['contour'] * s['contour']
           - weights['monotony'] * s['monotony'])
    
    # Normalize to [0, 1] range (max possible = 5, min = -1)
    total_norm = (total + 1) / 6
    
    return total_norm, s


# ─── SWEEP 1: k/n ratio vs quality ──────────────────────────────────────

def sweep_k_ratio(ns=None):
    """For each n, sweep all coprime k values, compute quality."""
    if ns is None:
        ns = [12, 24, 36, 48, 60, 120, 240, 500, 1000]
    
    results = {}
    
    for n in ns:
        print(f"\n=== n = {n} ===")
        best_k = None
        best_score = -1
        records = []
        
        for k in range(1, n // 2 + 1):
            if gcd(n, k) != 1:
                continue  # only coprime k for single-voice melodies
            
            orbit = build_pitch_orbit(n, k, omega=0)
            score, subs = musical_quality(orbit)
            ratio = k / n
            
            records.append({
                'k': k, 'ratio': round(ratio, 6), 'score': round(score, 4),
                **{key: round(v, 4) for key, v in subs.items()}
            })
            
            if score > best_score:
                best_score = score
                best_k = k
        
        # Sort by score descending
        records.sort(key=lambda r: -r['score'])
        
        results[n] = {
            'best_k': best_k,
            'best_ratio': round(best_k / n, 6),
            'best_score': round(best_score, 4),
            'top_10': records[:10],
            'bottom_5': records[-5:],
            'total_coprime': len(records),
        }
        
        print(f"  Best k={best_k}, k/n={best_k/n:.4f}, score={best_score:.4f}")
        print(f"  Top 5 ratios: {[r['ratio'] for r in records[:5]]}")
    
    return results


# ─── SWEEP 2: ω direction changes ───────────────────────────────────────

def count_direction_changes(orbit):
    """Count direction changes in the pitch contour."""
    if len(orbit) < 3:
        return 0
    changes = 0
    for i in range(1, len(orbit) - 1):
        d1 = orbit[i] - orbit[i-1]
        d2 = orbit[i+1] - orbit[i]
        if d1 * d2 < 0:  # sign change
            changes += 1
    return changes


def sweep_omega(ns=None):
    """For each n, sweep ω and measure direction changes per 16-note phrase."""
    if ns is None:
        ns = [12, 60, 120, 500, 1000, 5000]
    
    results = {}
    
    for n in ns:
        print(f"\n=== ω sweep for n = {n} ===")
        # Use a good k (closest coprime to n * golden_ratio_frac)
        # For now, use k = nearest coprime to n/phi
        k = 1
        for candidate in range(1, n):
            if gcd(n, candidate) == 1:
                k = candidate
                break
        # Actually, pick k that gives best quality from sweep 1 logic
        # Use k=1 for simplicity (chromatic, always coprime)
        k = 1
        
        records = []
        for omega in range(1, n // 2 + 1):
            orbit = build_pitch_orbit(n, k, omega=omega, psi=0.0)
            
            # Direction changes per 16-note segment
            if len(orbit) >= 16:
                changes_per_16 = []
                for start in range(0, len(orbit) - 15, 16):
                    segment = orbit[start:start+16]
                    changes_per_16.append(count_direction_changes(segment))
                avg_changes = np.mean(changes_per_16) if changes_per_16 else 0
            else:
                avg_changes = count_direction_changes(orbit)
            
            records.append({
                'omega': omega,
                'omega_over_n': round(omega / n, 6),
                'dir_changes_per_16': round(avg_changes, 2),
                'orbit_len': len(orbit),
            })
        
        # Find ω values giving 4-8 direction changes per 16 notes
        good = [r for r in records if 4 <= r['dir_changes_per_16'] <= 8]
        
        results[n] = {
            'total_tested': len(records),
            'good_omega_count': len(good),
            'good_omega_ratios': [r['omega_over_n'] for r in good[:20]],
            'sample': records[:20],  # first 20 for the report
        }
        
        if good:
            ratios = [r['omega_over_n'] for r in good]
            print(f"  Good ω/n range: [{min(ratios):.4f}, {max(ratios):.4f}]")
            print(f"  Mean good ω/n: {np.mean(ratios):.4f}")
        else:
            print(f"  No ω gave 4-8 direction changes per 16 notes")
    
    return results


# ─── SWEEP 3: ψ crystallization ─────────────────────────────────────────

def sweep_psi_crystallization(ns=None, psi_steps=10000):
    """Sweep ψ and count unique pitch classes for each n."""
    if ns is None:
        ns = [12, 53, 120, 500, 1000]
    
    results = {}
    
    for n in ns:
        print(f"\n=== ψ crystallization for n = {n} ===")
        k = 1  # simplest coprime
        omega_values = [1, n // 4, n // 3, n // 2 - 1]  # a few representative ω
        
        for omega in omega_values:
            if omega < 1 or omega >= n:
                continue
            
            psi_vals = np.linspace(0, 2 * pi, psi_steps, endpoint=False)
            unique_counts = []
            
            for psi in psi_vals:
                orbit = build_pitch_orbit(n, k, omega=omega, psi=psi)
                pcs = set(o % 12 for o in orbit)
                unique_counts.append(len(pcs))
            
            unique_arr = np.array(unique_counts)
            
            # Find distinct plateaus
            unique_levels = sorted(set(unique_counts))
            level_fractions = {lvl: np.mean(unique_arr == lvl) for lvl in unique_levels}
            
            key = f"n={n},ω={omega}"
            results[key] = {
                'n': n, 'omega': omega,
                'min_unique': int(unique_arr.min()),
                'max_unique': int(unique_arr.max()),
                'mean_unique': round(float(unique_arr.mean()), 2),
                'levels': {str(k): round(v, 4) for k, v in level_fractions.items()},
            }
            
            print(f"  ω={omega}: unique PCs range [{unique_arr.min()}, {unique_arr.max()}], "
                  f"mean={unique_arr.mean():.1f}")
    
    return results


# ─── SWEEP 4: Full quality with ω ───────────────────────────────────────

def sweep_full_quality(ns=None):
    """Find best (k, ω) combination for each n."""
    if ns is None:
        ns = [12, 24, 60, 120, 500]
    
    results = {}
    
    for n in ns:
        print(f"\n=== Full quality sweep for n = {n} ===")
        best = {'score': -1}
        
        # Test coprime k values (sample if too many)
        k_values = [k for k in range(1, n // 2 + 1) if gcd(n, k) == 1]
        if len(k_values) > 50:
            # Sample: include boundary values + evenly spaced
            indices = np.linspace(0, len(k_values) - 1, 50, dtype=int)
            k_values = [k_values[i] for i in indices]
        
        # Sample ω values
        omega_values = list(range(1, min(n // 2 + 1, 100)))
        if n > 200:
            omega_values = [int(x) for x in np.linspace(1, n // 2, 100)]
        
        records = []
        for k in k_values:
            for omega in omega_values:
                orbit = build_pitch_orbit(n, k, omega=omega)
                score, subs = musical_quality(orbit)
                records.append({
                    'k': k, 'omega': omega,
                    'k_over_n': round(k / n, 6),
                    'omega_over_n': round(omega / n, 6),
                    'score': round(score, 4),
                })
                if score > best['score']:
                    best = {'k': k, 'omega': omega, 'score': round(score, 4),
                            'k_over_n': round(k / n, 6), 'omega_over_n': round(omega / n, 6),
                            'subs': {key: round(v, 4) for key, v in subs.items()}}
        
        records.sort(key=lambda r: -r['score'])
        
        results[n] = {
            'best': best,
            'top_20': records[:20],
        }
        
        print(f"  Best: k={best.get('k')}, ω={best.get('omega')}, "
              f"k/n={best.get('k_over_n')}, ω/n={best.get('omega_over_n')}, "
              f"score={best.get('score')}")
    
    return results


# ─── Main ────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("RT⁴ REAL MUSICAL QUALITY ANALYSIS")
    print("=" * 70)
    
    # 1. k/n ratio sweep
    print("\n\n" + "=" * 70)
    print("SWEEP 1: k/n ratio vs musical quality (ω=0, single octave)")
    print("=" * 70)
    k_results = sweep_k_ratio()
    
    # 2. ω direction changes
    print("\n\n" + "=" * 70)
    print("SWEEP 2: ω and direction changes per 16-note phrase")
    print("=" * 70)
    omega_results = sweep_omega()
    
    # 3. ψ crystallization
    print("\n\n" + "=" * 70)
    print("SWEEP 3: ψ crystallization (unique pitch classes vs ψ)")
    print("=" * 70)
    psi_results = sweep_psi_crystallization()
    
    # 4. Full quality sweep
    print("\n\n" + "=" * 70)
    print("SWEEP 4: Full quality (k × ω grid)")
    print("=" * 70)
    full_results = sweep_full_quality()
    
    # Save all results
    all_results = {
        'k_ratio_sweep': {str(k): v for k, v in k_results.items()},
        'omega_sweep': {str(k): v for k, v in omega_results.items()},
        'psi_crystallization': psi_results,
        'full_quality': {str(k): v for k, v in full_results.items()},
    }
    
    out_path = '/Users/solo/r4rpi/initiatives/ARC-2026-034/research/real_quality_results.json'
    with open(out_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n\nResults saved to {out_path}")
    
    # Generate report
    generate_report(k_results, omega_results, psi_results, full_results)


def generate_report(k_results, omega_results, psi_results, full_results):
    """Generate the markdown report."""
    
    lines = []
    lines.append("# REAL SCALING REPORT: What Actually Controls Musical Quality in RT⁴")
    lines.append("")
    lines.append("**Generated:** 2026-02-20")
    lines.append("**Status:** Post-red-team empirical analysis")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("The old quality metric (interval entropy) was **wrong** - it rewarded randomness.")
    lines.append("This analysis uses a musicologically grounded composite metric:")
    lines.append("")
    lines.append("```")
    lines.append("quality = stepwise_ratio        # fraction of intervals ≤ 3 semitones")
    lines.append("        + leap_compensation     # leaps followed by contrary step")
    lines.append("        + range_score           # penalty for range > 18 semitones")
    lines.append("        + consonance_ratio      # fraction of consonant intervals")
    lines.append("        + contour_variety        # up/down/same entropy")
    lines.append("        - monotony_penalty       # penalty for long same-note runs")
    lines.append("```")
    lines.append("")
    lines.append("All weights = 1.0 (equal). Score normalized to [0, 1].")
    lines.append("")
    
    # Section 1: k/n ratio
    lines.append("---")
    lines.append("")
    lines.append("## 1. What k/n Ratio Maximizes Musical Quality?")
    lines.append("")
    lines.append("**Setup:** For each n, sweep all coprime k from 1 to n/2. ω=0 (single octave).")
    lines.append("This isolates the pure interval structure from register effects.")
    lines.append("")
    
    lines.append("### Best k/n ratios by n")
    lines.append("")
    lines.append("| n | Best k | k/n | Score | Stepwise | Leap Comp | Consonance | Contour | Monotony |")
    lines.append("|---|--------|-----|-------|----------|-----------|------------|---------|----------|")
    
    for n in sorted(k_results.keys()):
        r = k_results[n]
        top = r['top_10'][0]
        lines.append(f"| {n} | {top['k']} | {top['ratio']:.4f} | {top['score']:.4f} | "
                     f"{top['stepwise']:.3f} | {top['leap_comp']:.3f} | {top['consonance']:.3f} | "
                     f"{top['contour']:.3f} | {top['monotony']:.3f} |")
    
    lines.append("")
    lines.append("### Top 5 k/n ratios for each n")
    lines.append("")
    for n in sorted(k_results.keys()):
        r = k_results[n]
        lines.append(f"**n = {n}** ({r['total_coprime']} coprime values tested)")
        lines.append("")
        lines.append("| Rank | k | k/n | Score |")
        lines.append("|------|---|-----|-------|")
        for i, rec in enumerate(r['top_10'][:5]):
            lines.append(f"| {i+1} | {rec['k']} | {rec['ratio']:.4f} | {rec['score']:.4f} |")
        lines.append("")
    
    # Analyze: what ratios keep appearing?
    lines.append("### Analysis: Recurring optimal ratios")
    lines.append("")
    all_best_ratios = [k_results[n]['best_ratio'] for n in sorted(k_results.keys())]
    lines.append(f"Best ratios across all n: {[round(r, 4) for r in all_best_ratios]}")
    lines.append("")
    
    # Section 2: ω
    lines.append("---")
    lines.append("")
    lines.append("## 2. ω Scaling: Direction Changes per 16-Note Phrase")
    lines.append("")
    lines.append("**Target:** 4-8 direction changes per 16 notes (natural melodic contour).")
    lines.append("")
    
    for n_key in sorted(omega_results.keys(), key=lambda x: int(x)):
        r = omega_results[int(n_key)]
        lines.append(f"**n = {n_key}**: {r['good_omega_count']}/{r['total_tested']} ω values in target range")
        if r['good_omega_ratios']:
            lines.append(f"  - Good ω/n range: [{min(r['good_omega_ratios']):.4f}, {max(r['good_omega_ratios']):.4f}]")
            lines.append(f"  - Mean good ω/n: {np.mean(r['good_omega_ratios']):.4f}")
        lines.append("")
    
    # Section 3: ψ crystallization
    lines.append("---")
    lines.append("")
    lines.append("## 3. ψ Crystallization")
    lines.append("")
    lines.append("**Setup:** Sweep ψ from 0 to 2π in 10000 steps, count unique pitch classes.")
    lines.append("")
    
    lines.append("| n | ω | Min PCs | Max PCs | Mean PCs | Distinct Levels |")
    lines.append("|---|---|---------|---------|----------|-----------------|")
    for key in sorted(psi_results.keys()):
        r = psi_results[key]
        levels_str = ", ".join(f"{k}:{v}" for k, v in sorted(r['levels'].items(), key=lambda x: int(x[0])))
        lines.append(f"| {r['n']} | {r['omega']} | {r['min_unique']} | {r['max_unique']} | "
                     f"{r['mean_unique']} | {levels_str} |")
    lines.append("")
    
    # Section 4: Full quality
    lines.append("---")
    lines.append("")
    lines.append("## 4. Best (k, ω) Combinations")
    lines.append("")
    
    lines.append("| n | Best k | Best ω | k/n | ω/n | Score |")
    lines.append("|---|--------|--------|-----|-----|-------|")
    for n in sorted(full_results.keys()):
        b = full_results[n]['best']
        lines.append(f"| {n} | {b.get('k','-')} | {b.get('omega','-')} | "
                     f"{b.get('k_over_n','-')} | {b.get('omega_over_n','-')} | {b.get('score','-')} |")
    lines.append("")
    
    if full_results:
        lines.append("### Sub-metric breakdown of best parameters")
        lines.append("")
        for n in sorted(full_results.keys()):
            b = full_results[n]['best']
            if 'subs' in b:
                lines.append(f"**n = {n}**: {b['subs']}")
        lines.append("")
    
    # Section 5: Proposed scaling laws
    lines.append("---")
    lines.append("")
    lines.append("## 5. Proposed Scaling Laws")
    lines.append("")
    lines.append("Based on empirical data above:")
    lines.append("")
    
    # Extract patterns
    k_ratios = []
    omega_ratios = []
    for n in sorted(full_results.keys()):
        b = full_results[n]['best']
        if 'k_over_n' in b and b['k_over_n'] != '-':
            k_ratios.append((n, b['k_over_n']))
        if 'omega_over_n' in b and b['omega_over_n'] != '-':
            omega_ratios.append((n, b['omega_over_n']))
    
    lines.append("### k(n) - Pitch interval structure")
    lines.append("")
    for n, r in k_ratios:
        lines.append(f"- n={n}: optimal k/n = {r}")
    lines.append("")
    
    lines.append("### ω(n) - Contour frequency")
    lines.append("")
    for n, r in omega_ratios:
        lines.append(f"- n={n}: optimal ω/n = {r}")
    lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("## 6. Key Findings")
    lines.append("")
    lines.append("*(Populated after data analysis - see raw numbers above)*")
    lines.append("")
    
    report_path = '/Users/solo/r4rpi/initiatives/ARC-2026-034/research/REAL_SCALING_REPORT.md'
    with open(report_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"\nReport saved to {report_path}")


if __name__ == '__main__':
    main()
