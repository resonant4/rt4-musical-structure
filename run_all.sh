#!/bin/bash
# Run all reproducibility scripts in paper order

set -e
cd "$(dirname "$0")"

SCRIPTS=(
  "scripts/sturmian_deep_dive.py"
  "scripts/atlas_compute.py"
  "scripts/golden_ratio_rt4.py"
  "scripts/verify_claims.py"
  "scripts/real_quality_metric.py"
  "scripts/scaling_laws.py"
  "scripts/duration_from_geometry.py"
  "scripts/microtonality.py"
  "scripts/verify_scaling.py"
)

for script in "${SCRIPTS[@]}"; do
  echo ""
  echo "════════════════════════════════════════"
  echo "  $script"
  echo "════════════════════════════════════════"
  python3 "$script"
done

echo ""
echo "Done."
