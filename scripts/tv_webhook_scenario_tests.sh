#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ENDPOINT="${BASE_URL%/}/webhook/tradingview"
SYMBOL="${SYMBOL:-HBARUSDT.P}"

declare -A SCENARIO_STATUS

run_scenario() {
  local name="$1"
  local command="$2"
  local code_field="$3"
  local side="$4"
  local quantity="$5"
  local tp_pct="${6:-}"

  local tp_json="null"
  if [[ -n "${tp_pct}" ]]; then
    tp_json="${tp_pct}"
  fi

  read -r -d '' payload <<JSON
{
  "command": "${command}",
  "symbol": "${SYMBOL}",
  "side": "${side}",
  "entry_type": "market",
  "entry_price": 0.1234,
  "quantity": ${quantity},
  "stop_loss": null,
  "take_profits": null,
  "routing_profile": "default",
  "leverage": 10,
  "strategy_name": "TV Scenario Test",
  "code": "${code_field}",
  "tp_close_pct": ${tp_json}
}
JSON

  echo "=== ${name} ==="
  echo "Payload:"
  echo "${payload}"

  local response_file
  response_file="$(mktemp)"
  local http_code
  http_code=$(curl -s -o "${response_file}" -w "%{http_code}" \
    -X POST "${ENDPOINT}" \
    -H "Content-Type: application/json" \
    --data "${payload}" || true)

  echo "HTTP status: ${http_code}"
  SCENARIO_STATUS["${name}"]="${http_code}"

  if [[ "${http_code}" != "200" ]]; then
    echo "Response body:"
    cat "${response_file}" || true
  fi
  echo
  rm -f "${response_file}"
  sleep 1
}

run_scenario "S1: ENTER_LONG full open" "ENTER" "long entry" "buy" 100
run_scenario "S2: EXIT_LONG partial" "EXIT" "long exit" "sell" 40 40
run_scenario "S3: EXIT_LONG full close" "EXIT" "long exit" "sell" 60
run_scenario "S4: ENTER_SHORT full open" "ENTER" "short entry" "sell" 80
run_scenario "S5: EXIT_SHORT partial" "EXIT" "short exit" "buy" 35 35
run_scenario "S6: EXIT_SHORT full close" "EXIT" "short exit" "buy" 45

echo "=== Scenario summary ==="
for scenario in "${!SCENARIO_STATUS[@]}"; do
  printf "%s -> %s\n" "${scenario}" "${SCENARIO_STATUS[${scenario}]}"
done

