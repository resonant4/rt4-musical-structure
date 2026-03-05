#!/usr/bin/env python3
"""Independent verification of Golden Ratio Musical Quasicrystal claims."""

import numpy as np
from math import gcd, sqrt, log2
from collections import Counter
import json

PHI = (1 + sqrt(5)) / 2
results = {}

# ============================================================
# CLAIM 1: FFT of golden-ratio pitch sequences shows Fibonacci peaks
# ============================================================
print("=" * 60)
print("CLAIM 1: FFT Fibonacci peaks")
print("=" * 60)

FIBS = set()
a, b = 1, 1
while b < 100000:
    FIBS.add(b)
    a, b = b, a + b

def build_orbit(n, k):
    """Build RT4 orbit: positions visited by stepping k through n."""
    if gcd(n, k) != 1:
        return None
    orbit = []
    pos = 0
    for _ in range(n):
        orbit.append(pos)
        pos = (pos + k) % n
    return orbit

def orbit_to_pitches(orbit, n):
    """Map orbit positions to MIDI pitches (chromatic, mod 12)."""
    return [round(12 * p / n) % 12 for p in orbit]

def fft_fib_count(pitches, top=10):
    """Count how many of the top FFT peaks are at Fibonacci frequencies."""
    x = np.array(pitches, dtype=float)
    x = x - x.mean()
    ps = np.abs(np.fft.rfft(x))**2
    ps[0] = 0  # ignore DC
    top_freqs = np.argsort(ps)[::-1][:top]
    fib_count = sum(1 for f in top_freqs if f in FIBS)
    return fib_count, sorted(top_freqs.tolist())

# Test multiple n values and multiple constants
constants = {
    'phi': PHI,
    'pi': np.pi,
    'e': np.e,
    'sqrt2': sqrt(2),
}

claim1_results = {}
for n in [500, 1000, 2000, 5300]:
    claim1_results[n] = {}
    for name, c in constants.items():
        k = round(n / c)
        if gcd(n, k) != 1:
            # find nearest coprime
            for delta in range(1, 20):
                if gcd(n, k + delta) == 1:
                    k = k + delta
                    break
                if gcd(n, k - delta) == 1:
                    k = k - delta
                    break
        orbit = build_orbit(n, k)
        if orbit is None:
            claim1_results[n][name] = {'k': k, 'fib_count': 0, 'note': 'not coprime'}
            continue
        pitches = orbit_to_pitches(orbit, n)
        fc, top = fft_fib_count(pitches)
        claim1_results[n][name] = {'k': k, 'fib_count': fc, 'top_freqs': top}
        print(f"  n={n}, const={name}, k={k}, fib_in_top10={fc}, top={top[:5]}")
    
    # Also test k=499 (random coprime) for n=1000
    if n == 1000:
        k_rand = 499
        if gcd(n, k_rand) == 1:
            orbit = build_orbit(n, k_rand)
            pitches = orbit_to_pitches(orbit, n)
            fc, top = fft_fib_count(pitches)
            claim1_results[n]['random_499'] = {'k': k_rand, 'fib_count': fc, 'top_freqs': top}
            print(f"  n={n}, const=random_499, k={k_rand}, fib_in_top10={fc}")

print("\nClaim 1 summary:")
for n in claim1_results:
    line = f"  n={n}: "
    for name in claim1_results[n]:
        line += f"{name}={claim1_results[n][name]['fib_count']} "
    print(line)

results['claim1'] = claim1_results

# ============================================================
# CLAIM 2: Only perfect 5ths and minor 6ths
# ============================================================
print("\n" + "=" * 60)
print("CLAIM 2: Only intervals of 7 and 8 semitones")
print("=" * 60)

claim2_results = {}
for n in [100, 500, 1000, 2000, 5300]:
    k = round(n / PHI)
    if gcd(n, k) != 1:
        for delta in range(1, 20):
            if gcd(n, k + delta) == 1:
                k = k + delta
                break
            if gcd(n, k - delta) == 1:
                k = k - delta
                break
    orbit = build_orbit(n, k)
    pitches = orbit_to_pitches(orbit, n)
    intervals = [(pitches[i+1] - pitches[i]) % 12 for i in range(len(pitches)-1)]
    counter = Counter(intervals)
    claim2_results[n] = {'k': k, 'intervals': dict(counter)}
    print(f"  n={n}, k={k}: intervals={dict(counter)}")

# Test circle of fifths: n=12, k=7
orbit_cof = build_orbit(12, 7)
pitches_cof = orbit_to_pitches(orbit_cof, 12)
intervals_cof = [(pitches_cof[i+1] - pitches_cof[i]) % 12 for i in range(len(pitches_cof)-1)]
print(f"  Circle of fifths n=12, k=7: pitches={pitches_cof}, intervals={Counter(intervals_cof)}")
claim2_results['circle_of_fifths'] = {'intervals': dict(Counter(intervals_cof))}

# Three-distance theorem verification: raw gaps without pitch quantization
print("\n  Three-distance theorem check (raw gaps, no quantization):")
for n in [100, 1000]:
    k = round(n / PHI)
    if gcd(n, k) != 1:
        for delta in range(1, 20):
            if gcd(n, k + delta) == 1: k = k + delta; break
            if gcd(n, k - delta) == 1: k = k - delta; break
    orbit = build_orbit(n, k)
    # Raw theta values (not quantized)
    thetas = [2 * np.pi * p / n for p in orbit]
    # Map to continuous pitch: pitch = 12 * p / n (not rounded)
    raw_pitches = [12 * p / n for p in orbit]
    raw_intervals = [(raw_pitches[i+1] - raw_pitches[i]) % 12 for i in range(len(raw_pitches)-1)]
    unique_raw = set(round(iv, 6) for iv in raw_intervals)
    print(f"  n={n}: {len(unique_raw)} distinct raw intervals: {sorted(unique_raw)[:5]}")

results['claim2'] = claim2_results

# ============================================================
# CLAIM 3: Fibonacci pairs always coprime, 40% higher entropy
# ============================================================
print("\n" + "=" * 60)
print("CLAIM 3: Fibonacci coprimality + entropy advantage")
print("=" * 60)

# Verify gcd(F_n, F_{n+1}) = 1
fibs = [1, 1]
for _ in range(30):
    fibs.append(fibs[-1] + fibs[-2])
all_coprime = all(gcd(fibs[i], fibs[i+1]) == 1 for i in range(len(fibs)-1))
print(f"  gcd(F_n, F_{{n+1}}) = 1 for first 32 Fibonacci numbers: {all_coprime}")

def interval_entropy(pitches):
    intervals = [(pitches[i+1] - pitches[i]) % 12 for i in range(len(pitches)-1)]
    c = Counter(intervals)
    total = sum(c.values())
    probs = [v/total for v in c.values()]
    return -sum(p * log2(p) for p in probs if p > 0)

fib_pairs = [(21, 34), (55, 89), (144, 233), (610, 987), (1597, 2584)]
claim3_results = {}

for n, k in fib_pairs:
    orbit = build_orbit(n, k)
    pitches = orbit_to_pitches(orbit, n)
    fib_ent = interval_entropy(pitches)
    
    # Compare against 100 random coprime pairs of similar size
    rng = np.random.RandomState(42)
    random_ents = []
    for _ in range(100):
        rk = rng.randint(2, n-1)
        while gcd(n, rk) != 1:
            rk = rng.randint(2, n-1)
        rorbit = build_orbit(n, rk)
        rpitches = orbit_to_pitches(rorbit, n)
        random_ents.append(interval_entropy(rpitches))
    
    rand_mean = np.mean(random_ents)
    rand_std = np.std(random_ents)
    advantage = (fib_ent - rand_mean) / rand_mean * 100
    claim3_results[(n, k)] = {
        'fib_entropy': round(fib_ent, 4),
        'rand_mean': round(rand_mean, 4),
        'rand_std': round(rand_std, 4),
        'advantage_pct': round(advantage, 1)
    }
    print(f"  ({n},{k}): fib_ent={fib_ent:.4f}, rand_mean={rand_mean:.4f}±{rand_std:.4f}, advantage={advantage:.1f}%")

results['claim3'] = {str(k): v for k, v in claim3_results.items()}

# ============================================================
# CLAIM 4: Triple golden spontaneously selects 6-note scale
# ============================================================
print("\n" + "=" * 60)
print("CLAIM 4: Triple golden selects 6-note scale")
print("=" * 60)

claim4_results = {}
for n in [500, 1000, 2000]:
    k = round(n / PHI)
    omega = round(n / PHI**2)
    xi = round(n / PHI**3)
    
    # Ensure coprime
    if gcd(n, k) != 1:
        for d in range(1, 20):
            if gcd(n, k+d) == 1: k = k+d; break
            if gcd(n, k-d) == 1: k = k-d; break
    
    # Build orbit with triple modulation
    # The report says triple golden "concentrates pitches onto 6-note subset"
    # Need to figure out how triple golden works. 
    # Interpretation: position evolves as pos_t = (k*t + omega*sin(2pi*xi*t/n)) mod n
    # Or: three coupled orbits. Let me try the simplest: additive combination
    
    # Method 1: Combined orbit position = (k*t + omega*floor(t*xi/n)) mod n
    # Method 2: pitch = round(12 * ((k*t/n + omega*t/n^2 + xi*t/n^3) mod 1)) % 12
    # Method 3: The report mentions k, omega, xi as three parameters 
    # Let me try: pitch at step t = round(12 * (k*t/n)) % 12, modulated by omega and xi
    
    # Actually, the simplest interpretation matching RT4:
    # pos(t) = (k*t) mod n  (basic orbit)
    # pitch(t) = round(12 * pos(t) / n + omega * sin(2*pi*xi*t/n)) % 12
    
    # Let me try multiple interpretations
    
    # Interpretation A: Simple additive modulation on pitch
    pitches_a = []
    for t in range(n):
        pos = (k * t) % n
        base_pitch = 12 * pos / n
        mod = omega/n * np.sin(2 * np.pi * xi * t / n)
        pitch = round(base_pitch + mod) % 12
        pitches_a.append(pitch)
    pcs_a = len(set(pitches_a))
    
    # Interpretation B: Three orbit combination
    pitches_b = []
    for t in range(n):
        val = (k * t + omega * (t % max(1,xi))) % n
        pitch = round(12 * val / n) % 12
        pitches_b.append(pitch)
    pcs_b = len(set(pitches_b))
    
    # Interpretation C: pitch = round(12 * (k*t mod n) / n) with amplitude modulation
    # where amplitude = xi/n * sin(2pi * omega * t / n)
    pitches_c = []
    for t in range(n):
        pos = (k * t) % n
        base = 12 * pos / n
        amp = (12/n) * xi * np.sin(2 * np.pi * omega * t / n)
        pitch = round(base + amp) % 12
        pitches_c.append(pitch)
    pcs_c = len(set(pitches_c))
    
    # Without any modulation (baseline)
    pitches_base = [round(12 * ((k*t) % n) / n) % 12 for t in range(n)]
    pcs_base = len(set(pitches_base))
    
    claim4_results[n] = {
        'k': k, 'omega': omega, 'xi': xi,
        'pcs_interp_a': pcs_a,
        'pcs_interp_b': pcs_b, 
        'pcs_interp_c': pcs_c,
        'pcs_baseline': pcs_base,
    }
    print(f"  n={n}: k={k}, ω={omega}, ξ={xi}")
    print(f"    Interp A (sin mod): {pcs_a} PCs")
    print(f"    Interp B (combined orbit): {pcs_b} PCs")
    print(f"    Interp C (amp mod): {pcs_c} PCs")
    print(f"    Baseline (no mod): {pcs_base} PCs")

results['claim4'] = {str(k): v for k, v in claim4_results.items()}

# ============================================================
# CLAIM 5: ψ_crit ≈ 0.06 rad, n-independent
# ============================================================
print("\n" + "=" * 60)
print("CLAIM 5: ψ_crit ≈ 0.06, n-independent")
print("=" * 60)

claim5_results = {}
for n in [12, 24, 53, 100, 500, 1000, 5300]:
    k = round(n / PHI)
    if gcd(n, k) != 1:
        for d in range(1, 20):
            if gcd(n, k+d) == 1: k = k+d; break
            if gcd(n, k-d) == 1: k = k-d; break
    
    orbit = build_orbit(n, k)
    if orbit is None:
        claim5_results[n] = {'psi_crit': None, 'note': 'not coprime'}
        continue
    
    # Raw pitches (continuous)
    raw = np.array([12 * p / n for p in orbit])
    
    psi_crit = None
    # Sweep psi from 0 to 1.0
    for psi_idx in range(1001):
        psi = psi_idx / 1000.0
        if psi == 0:
            snapped = np.round(raw) % 12
        else:
            # Crystallization: snap towards nearest scale tone with strength psi
            # Interpretation: quantize to grid of size (12*psi), then mod 12
            # Or: add psi * (round(p) - p) to each pitch
            snapped = raw + psi * (np.round(raw) - raw)
            snapped = np.round(snapped) % 12
        
        unique_pcs = len(set(snapped.astype(int)))
        if unique_pcs < 5 and psi_crit is None:
            psi_crit = psi
            break
    
    claim5_results[n] = {'k': k, 'psi_crit': psi_crit}
    print(f"  n={n}, k={k}: ψ_crit={psi_crit}")

# Try alternative crystallization model: scale snapping
print("\n  Alternative: pentatonic snap strength")
for n in [12, 24, 53, 100, 500, 1000, 5300]:
    k = round(n / PHI)
    if gcd(n, k) != 1:
        for d in range(1, 20):
            if gcd(n, k+d) == 1: k = k+d; break
            if gcd(n, k-d) == 1: k = k-d; break
    orbit = build_orbit(n, k)
    if orbit is None: continue
    
    raw = np.array([12 * p / n for p in orbit])
    
    # Pentatonic: {0, 2, 4, 7, 9}
    penta = np.array([0, 2, 4, 7, 9])
    
    psi_crit2 = None
    for psi_idx in range(1001):
        psi = psi_idx / 1000.0
        # Snap towards nearest pentatonic note with strength psi
        snapped = []
        for p in raw:
            p12 = p % 12
            dists = np.abs(penta - p12)
            dists = np.minimum(dists, 12 - dists)
            nearest_penta = penta[np.argmin(dists)]
            diff = nearest_penta - p12
            if abs(diff) > 6:
                diff = diff - 12 * np.sign(diff)
            new_p = p12 + psi * diff
            snapped.append(round(new_p) % 12)
        
        unique_pcs = len(set(snapped))
        if unique_pcs <= 5 and psi_crit2 is None:
            psi_crit2 = psi
    
    print(f"  n={n}: penta_snap ψ_crit={psi_crit2}")

results['claim5'] = {str(k): v for k, v in claim5_results.items()}

# ============================================================
# CLAIM 6: ω = n/24 keeps ~4 phrase boundaries per 4 bars
# ============================================================
print("\n" + "=" * 60)
print("CLAIM 6: ω = n/24 gives ~4 phrase boundaries per 48 steps")
print("=" * 60)

claim6_results = {}
for n in [12, 60, 120, 500, 1000, 5300]:
    k = round(n / PHI)
    if gcd(n, k) != 1:
        for d in range(1, 20):
            if gcd(n, k+d) == 1: k = k+d; break
            if gcd(n, k-d) == 1: k = k-d; break
    
    omega = n / 24.0
    
    # Build orbit with z-modulation: z(t) = sin(2π * ω * t / n)
    # dz/dt ≈ z(t+1) - z(t)
    # Phrase boundary = local minimum of |dz/dt| (or zero crossing of dz/dt)
    
    num_steps = max(192, n)  # at least 4 segments of 48
    z = np.array([np.sin(2 * np.pi * omega * t / n) for t in range(num_steps)])
    dz = np.diff(z)
    
    # Find minima of z (phrase boundaries = where melody "resets")
    boundaries = []
    for t in range(1, len(z) - 1):
        if z[t] < z[t-1] and z[t] < z[t+1]:
            boundaries.append(t)
    
    # Count per 48-step segment
    num_segments = num_steps // 48
    counts = []
    for seg in range(num_segments):
        start = seg * 48
        end = start + 48
        c = sum(1 for b in boundaries if start <= b < end)
        counts.append(c)
    
    avg_boundaries = np.mean(counts) if counts else 0
    claim6_results[n] = {
        'k': k, 'omega': round(omega, 2),
        'avg_boundaries_per_48': round(avg_boundaries, 2),
        'segment_counts': counts[:8]
    }
    print(f"  n={n}, ω={omega:.1f}: avg={avg_boundaries:.2f} boundaries/48steps, segments={counts[:8]}")

results['claim6'] = {str(k): v for k, v in claim6_results.items()}

# Save raw results
with open('/Users/solo/r4rpi/initiatives/ARC-2026-034/research/verify_raw.json', 'w') as f:
    json.dump(results, f, indent=2, default=str)

print("\n\nDone. Results saved.")
