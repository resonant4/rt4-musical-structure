"""
Interval Pair Atlas Computation Engine

For every (n, k) with n ∈ [4, 500], k ∈ [1, n-1], gcd(n,k)=1:
Computes the interval pair from Theorem 3 (Paper IV) and scores consonance.

Key insight: alpha = 12k/n → two interval types (floor and ceil semitones).
The fractional part of alpha gives the proportion of "large" vs "small" intervals.
"""

import math
import json
import sys
from collections import defaultdict

# Consonance ratings: semitone → consonance score
CONSONANCE = {
    0:  1.0,   # P1  Perfect unison
    1:  0.1,   # m2  Minor 2nd
    2:  0.3,   # M2  Major 2nd
    3:  0.7,   # m3  Minor 3rd
    4:  0.8,   # M3  Major 3rd
    5:  0.9,   # P4  Perfect 4th
    6:  0.2,   # TT  Tritone
    7:  1.0,   # P5  Perfect 5th
    8:  0.7,   # m6  Minor 6th
    9:  0.8,   # M6  Major 6th
    10: 0.4,   # m7  Minor 7th
    11: 0.2,   # M7  Major 7th
}

# Music names for interval display
INTERVAL_NAMES = {
    0:  "P1",
    1:  "m2",
    2:  "M2",
    3:  "m3",
    4:  "M3",
    5:  "P4",
    6:  "TT",
    7:  "P5",
    8:  "m6",
    9:  "M6",
    10: "m7",
    11: "M7",
}


def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def compute_orbit_length(n, k):
    """Orbit length = n / gcd(n, k) - for gcd=1 cells, this is always n."""
    return n // gcd(n, k)


def compute_cell(n, k):
    """Compute interval pair and consonance for cell (n, k)."""
    g = gcd(n, k)
    alpha = 12.0 * k / n

    # Theorem 3: non-integer alpha → exactly TWO interval types
    int_alpha = int(alpha)
    frac = alpha - int_alpha

    if abs(frac) < 1e-10:
        # Integer alpha → single interval type (degenerate: only one interval)
        interval_small = int_alpha % 12
        interval_large = int_alpha % 12
        frac = 0.0
    else:
        interval_small = math.floor(alpha) % 12
        interval_large = math.ceil(alpha) % 12

    # Weighted consonance: frac = proportion of large intervals
    cons_small = CONSONANCE[interval_small]
    cons_large = CONSONANCE[interval_large]
    consonance = frac * cons_large + (1.0 - frac) * cons_small

    orbit_length = compute_orbit_length(n, k)

    return {
        "n": n,
        "k": k,
        "gcd": g,
        "orbitLength": orbit_length,
        "alpha": round(alpha, 8),
        "intervalSmall": interval_small,
        "intervalLarge": interval_large,
        "fracLarge": round(frac, 8),
        "consonance": round(consonance, 6),
    }


def compute_atlas(n_min=4, n_max=500, gcd_filter=1, verbose=True):
    """Compute atlas data for all (n, k) with gcd(n,k) == gcd_filter."""
    data = []
    pair_counts = defaultdict(int)

    for n in range(n_min, n_max + 1):
        if verbose and n % 50 == 0:
            print(f"  Processing n={n}...", file=sys.stderr)
        for k in range(1, n):
            g = gcd(n, k)
            if g != gcd_filter:
                continue
            cell = compute_cell(n, k)
            data.append(cell)
            pair_key = (cell["intervalSmall"], cell["intervalLarge"])
            pair_counts[pair_key] += 1

    return data, dict(pair_counts)


def compute_summary(data, pair_counts):
    """Compute summary statistics."""
    # Unique interval pairs
    unique_pairs = len(pair_counts)

    # Most common pairs (top 20)
    sorted_pairs = sorted(pair_counts.items(), key=lambda x: -x[1])
    top_pairs = [
        {
            "intervalSmall": p[0],
            "intervalLarge": p[1],
            "nameSmall": INTERVAL_NAMES[p[0]],
            "nameLarge": INTERVAL_NAMES[p[1]],
            "count": c,
        }
        for (p, c) in sorted_pairs[:20]
    ]

    # Top-20 most consonant gcd=1 cells for n ≤ 100
    small_n_cells = [d for d in data if d["n"] <= 100]
    small_n_cells.sort(key=lambda x: -x["consonance"])
    top_consonant = []
    seen = set()
    for cell in small_n_cells:
        key = (cell["n"], cell["k"])
        if key not in seen:
            seen.add(key)
            top_consonant.append({
                "n": cell["n"],
                "k": cell["k"],
                "alpha": cell["alpha"],
                "intervalSmall": cell["intervalSmall"],
                "intervalLarge": cell["intervalLarge"],
                "pairName": f"{INTERVAL_NAMES[cell['intervalSmall']]} + {INTERVAL_NAMES[cell['intervalLarge']]}",
                "fracLarge": cell["fracLarge"],
                "consonance": cell["consonance"],
                "orbitLength": cell["orbitLength"],
            })
            if len(top_consonant) >= 20:
                break

    # Count high-consonance cells (>0.7)
    high_cons = sum(1 for d in data if d["consonance"] > 0.7)
    total = len(data)
    pct_high = round(100.0 * high_cons / total, 2) if total > 0 else 0

    # Consonance histogram
    histogram = defaultdict(int)
    for d in data:
        bucket = round(d["consonance"] * 10) / 10  # round to 0.1
        histogram[str(round(bucket, 1))] += 1

    return {
        "totalCells": total,
        "uniqueIntervalPairs": unique_pairs,
        "highConsonanceCount": high_cons,
        "highConsonancePct": pct_high,
        "topPairs": top_pairs,
        "top20Consonant_n100": top_consonant,
        "consonanceHistogram": dict(sorted(histogram.items())),
    }


def main():
    out_path = "/Users/solo/r4rpi/arcs/ARC-2026-034/research/atlas_data.json"

    print("Computing Interval Pair Atlas (gcd=1 cells, n=4..500)...", file=sys.stderr)
    data, pair_counts = compute_atlas(n_min=4, n_max=500, gcd_filter=1, verbose=True)
    print(f"Computed {len(data)} cells.", file=sys.stderr)

    print("Computing summary statistics...", file=sys.stderr)
    summary = compute_summary(data, pair_counts)

    print(f"  Total gcd=1 cells: {summary['totalCells']}", file=sys.stderr)
    print(f"  Unique interval pairs: {summary['uniqueIntervalPairs']}", file=sys.stderr)
    print(f"  High-consonance (>0.7): {summary['highConsonanceCount']} ({summary['highConsonancePct']}%)", file=sys.stderr)

    print("\n  Top 10 most common interval pairs:", file=sys.stderr)
    for p in summary["topPairs"][:10]:
        print(f"    {p['nameSmall']} + {p['nameLarge']}: {p['count']} cells", file=sys.stderr)

    print("\n  Top 20 most consonant cells (n≤100):", file=sys.stderr)
    for c in summary["top20Consonant_n100"]:
        print(f"    n={c['n']:3d} k={c['k']:3d} {c['pairName']:12s} cons={c['consonance']:.4f}  frac={c['fracLarge']:.4f}", file=sys.stderr)

    output = {
        "meta": {
            "generated": "2026-03-01",
            "description": "Interval Pair Atlas: gcd=1 cells, n=4..500",
            "nMin": 4,
            "nMax": 500,
        },
        "summary": summary,
        "data": data,
    }

    with open(out_path, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    size_kb = len(json.dumps(output)) / 1024
    print(f"\nWritten to {out_path} ({size_kb:.1f} KB)", file=sys.stderr)

    return output


if __name__ == "__main__":
    main()
