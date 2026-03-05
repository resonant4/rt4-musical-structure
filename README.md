# RT⁴ Musical Structure - Reproducibility Code

Computational scripts for:

**Musical Structure as Torus Geometry**  
*Cyclic Permutations on 𝕋³ as a Generative Framework for Phrase Closure, Polyphony, and Scale Selection*  
Egils Jakovels and Solo - v1.0

---

## Structure

| Script | Paper Section | What it computes |
|--------|--------------|-----------------|
| `scripts/sturmian_deep_dive.py` | §4 | Three-Distance Theorem applied to RT⁴ orbits; verifies two-interval theorem computationally |
| `scripts/atlas_compute.py` | §4.5, §5.6 | Interval Pair Atlas - consonance scores for all coprime (n, k) up to n=500 |
| `scripts/golden_ratio_rt4.py` | §5 | Golden ratio × RT⁴: Fibonacci peaks in FFT, φ and 12-TET, continued fraction convergents |
| `scripts/verify_claims.py` | §5 | Independent numerical verification of all golden ratio claims |
| `scripts/real_quality_metric.py` | §6.1 | Melodic quality metric (musicologically grounded sub-metrics) |
| `scripts/scaling_laws.py` | §6.2–6.4 | Optimal winding ratio k/n → 1/4, contour frequency ω/n ≈ 0.2 |
| `scripts/duration_from_geometry.py` | §7 | Duration from orbital velocity; dotted rhythms from cosine quantization |
| `scripts/microtonality.py` | §8 | ψ crystallization mechanism; JI approximation via RT⁴ orbits |
| `scripts/verify_scaling.py` | §6–7 | Adversarial verification of duration geometry and scaling law claims |

## Requirements

```
pip install -r requirements.txt
```

Python 3.9+ required. No exotic dependencies - NumPy and standard library only.

## Run all

```bash
bash run_all.sh
```

Each script prints its results to stdout. Expected outputs match the figures and tables in the paper.

## License

CC BY 4.0 International - same license as the paper.  
© 2026 Egils Jakovels and Solo.
