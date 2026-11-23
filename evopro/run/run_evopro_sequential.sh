set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"
RUNS="${RUNS:-10}"
PREFIX="${PREFIX:-outputs}"
: "${CUDA_VISIBLE_DEVICES:=0}"

RUN_SCRIPT="$SCRIPT_DIR/run_evopro.py"
CONFIG_TEMPLATE="${CONFIG_TEMPLATE:-$SCRIPT_DIR/configs/evopro.yaml}"
BASE_OUT="$SCRIPT_DIR"  # donde se crearán outputs_01, outputs_02, ...

# Comprobaciones
[[ -f "$RUN_SCRIPT" ]] || { echo "❌ No encuentro $RUN_SCRIPT"; exit 1; }
[[ -f "$CONFIG_TEMPLATE" ]] || { echo "❌ No encuentro $CONFIG_TEMPLATE"; exit 1; }
if ! "$PYTHON_BIN" -c "import yaml" >/dev/null 2>&1; then
  echo "❌ Falta PyYAML en el entorno de '$PYTHON_BIN'. Instala con:"
  echo "   $PYTHON_BIN -m pip install pyyaml"
  exit 1
fi

echo "Config template : $CONFIG_TEMPLATE"
echo "Python          : $PYTHON_BIN"
echo "GPU(s)          : $CUDA_VISIBLE_DEVICES"
echo "Runs            : $RUNS"
echo "---------------------------------------------"

for i in $(seq 1 "$RUNS"); do
  PADDED="$(printf '%02d' "$i")"
  RUN_DIR="${BASE_OUT}/${PREFIX}_${PADDED}/"
  mkdir -p "$RUN_DIR"

  CONFIG_RUN="${RUN_DIR}/evopro_${PREFIX}_${PADDED}.yaml"

  # Escribir YAML por corrida con flags.run_dir y seed
  "$PYTHON_BIN" - <<PY > /dev/null
import os, yaml
template = r"""$CONFIG_TEMPLATE"""
out_path = r"""$CONFIG_RUN"""
run_dir = r"""$RUN_DIR"""
seed = $i
with open(template, "r") as f:
    data = yaml.safe_load(f)
flags = data.get("flags", {})
flags["run_dir"] = run_dir if run_dir.endswith(os.sep) else run_dir + os.sep
flags["random_seed"] = seed
data["flags"] = flags
with open(out_path, "w") as f:
    yaml.safe_dump(data, f, sort_keys=False)
PY

  LOG="${RUN_DIR}/run.log"
  echo "[$(date +%H:%M:%S)] ▶️  Run $i/$RUNS -> ${PREFIX}_${PADDED}"
  (
    export CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"
    set -x
    "$PYTHON_BIN" "$RUN_SCRIPT" --config_file "$CONFIG_RUN" >"$LOG" 2>&1
  )
  status=$?
  if [[ $status -eq 0 ]]; then
    echo "[$(date +%H:%M:%S)] ✅  Run $i ok. Log: $LOG"
  else
    echo "[$(date +%H:%M:%S)] ❌  Run $i falló (exit $status). Ver: $LOG"
  fi
  sleep 0.2
done

echo "---------------------------------------------"
echo "Listo. Revisa $(realpath "$BASE_OUT")/${PREFIX}_01 .. ${PREFIX}_$(printf '%02d' "$RUNS")"
