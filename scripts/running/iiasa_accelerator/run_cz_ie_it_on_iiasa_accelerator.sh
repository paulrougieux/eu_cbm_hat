#!/usr/bin/env bash
set -euo pipefail

# --- Config (container paths!) ---
EU_CBM_DATA="${EU_CBM_DATA:-/app/local_data/eu_cbm_data}"
EU_CBM_AIDB="${EU_CBM_AIDB:-/app/local_data/eu_cbm_aidb}"
COUNTRY="${COUNTRY:-ZZ}"
COMBO="${COMBO:-reference}"
TIMESTEPS="${TIMESTEPS:-30}"

echo "[INFO] EU_CBM_DATA=${EU_CBM_DATA}"
echo "[INFO] EU_CBM_AIDB=${EU_CBM_AIDB}"
echo "[INFO] COUNTRY=${COUNTRY}  COMBO=${COMBO}  TIMESTEPS=${TIMESTEPS}"

# Clone the AIDB
git clone --depth 1 https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_aidb.git /app/local_data/eu_cbm_aidb

# Ensure output dir exists so post-processing never fails even on early exit
mkdir -p "${EU_CBM_DATA}/output"

echo "[DEBUG] Listing /app/local_data"
ls -lah /app/local_data || true
echo "[DEBUG] Listing ${EU_CBM_DATA}"
ls -lah "${EU_CBM_DATA}" || true
echo "[DEBUG] Listing ${EU_CBM_AIDB}"
ls -lah "${EU_CBM_AIDB}" || true

# Hard-fail if required mounts are missing (this is your recurring error!)
[[ -d "${EU_CBM_DATA}" ]] || { echo "FATAL: ${EU_CBM_DATA} not mounted"; exit 2; }
[[ -d "${EU_CBM_AIDB}" ]] || { echo "FATAL: ${EU_CBM_AIDB} not mounted"; exit 3; }

# Install runtime deps (inside the container)
python -m pip install --no-cache-dir --upgrade pip
python -m pip install --no-cache-dir \
  eu-cbm-hat \
  https://github.com/cat-cfs/libcbm_py/archive/refs/heads/main.tar.gz

# Run CBM for the ZZ country
python run_cz_ie_it_on_iiasa_accelerator.py


