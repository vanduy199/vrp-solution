#!/usr/bin/env bash
set -u

# Usage:
#   ./run_test_api_50.sh
#   ./run_test_api_50.sh 50
#   ./run_test_api_50.sh 100 http://127.0.0.1:8000/api/test
#   ./run_test_api_50.sh 1000 http://127.0.0.1:8000/api/test parallel 1000
#   ./run_test_api_50.sh 200 http://127.0.0.1:8000/api/test parallel 200 15

TOTAL_RUNS="${1:-50}"
API_URL="${2:-http://127.0.0.1:8000/api/test_1}"
MODE="${3:-sequential}"
CONCURRENCY="${4:-10}"
REQUEST_TIMEOUT="${5:-10}"

if ! [[ "$TOTAL_RUNS" =~ ^[0-9]+$ ]] || [ "$TOTAL_RUNS" -le 0 ]; then
  echo "[ERROR] TOTAL_RUNS must be a positive integer. Got: $TOTAL_RUNS"
  exit 1
fi

if [[ "$MODE" != "sequential" && "$MODE" != "parallel" ]]; then
  echo "[ERROR] MODE must be either 'sequential' or 'parallel'. Got: $MODE"
  exit 1
fi

if ! [[ "$CONCURRENCY" =~ ^[0-9]+$ ]] || [ "$CONCURRENCY" -le 0 ]; then
  echo "[ERROR] CONCURRENCY must be a positive integer. Got: $CONCURRENCY"
  exit 1
fi

if ! [[ "$REQUEST_TIMEOUT" =~ ^[0-9]+$ ]] || [ "$REQUEST_TIMEOUT" -le 0 ]; then
  echo "[ERROR] REQUEST_TIMEOUT must be a positive integer (seconds). Got: $REQUEST_TIMEOUT"
  exit 1
fi

success_count=0
fail_count=0

echo "Calling $API_URL $TOTAL_RUNS times in $MODE mode (timeout=${REQUEST_TIMEOUT}s)..."

if [ "$MODE" = "sequential" ]; then
  for i in $(seq 1 "$TOTAL_RUNS"); do
    # Capture status code + response time while hiding body.
    result=$(curl -sS --max-time "$REQUEST_TIMEOUT" -o /dev/null -w "%{http_code} %{time_total}" "$API_URL")
    status_code="${result%% *}"
    response_time="${result##* }"

    if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 300 ]; then
      success_count=$((success_count + 1))
      echo "[$i/$TOTAL_RUNS] OK - HTTP $status_code - ${response_time}s"
    else
      fail_count=$((fail_count + 1))
      echo "[$i/$TOTAL_RUNS] FAIL - HTTP $status_code - ${response_time}s"
    fi
  done
else
  tmp_result_file="$(mktemp)"
  trap 'rm -f "$tmp_result_file"' EXIT

  seq 1 "$TOTAL_RUNS" | xargs -I {} -P "$CONCURRENCY" bash -c '
    i="$1"
    total="$2"
    url="$3"
    out_file="$4"
    timeout="$5"

    result=$(curl -sS --max-time "$timeout" -o /dev/null -w "%{http_code} %{time_total}" "$url")
    status_code="${result%% *}"
    response_time="${result##* }"
    if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 300 ]; then
      echo "OK" >> "$out_file"
      echo "[$i/$total] OK - HTTP $status_code - ${response_time}s"
    else
      echo "FAIL" >> "$out_file"
      echo "[$i/$total] FAIL - HTTP $status_code - ${response_time}s"
    fi
  ' _ {} "$TOTAL_RUNS" "$API_URL" "$tmp_result_file" "$REQUEST_TIMEOUT"

  success_count=$(grep -c '^OK$' "$tmp_result_file" || true)
  fail_count=$(grep -c '^FAIL$' "$tmp_result_file" || true)
fi

echo ""
echo "Done. Success: $success_count | Fail: $fail_count | Total: $TOTAL_RUNS"
