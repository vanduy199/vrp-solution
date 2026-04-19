#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEMO_DIR="$ROOT_DIR/scripts/demo_kafka"
LOG_DIR="$DEMO_DIR/logs"
PID_DIR="$DEMO_DIR/pids"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
KAFKA_COMPOSE_FILE="$ROOT_DIR/docker-compose.kafka.yml"

mkdir -p "$LOG_DIR" "$PID_DIR"

start_kafka() {
  echo "[1/5] Starting Kafka stack..."
  sudo docker compose -f "$KAFKA_COMPOSE_FILE" up -d
}

start_consumer() {
  local name="$1"
  local script_path="$2"
  local log_file="$LOG_DIR/${name}.log"
  local pid_file="$PID_DIR/${name}.pid"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[SKIP] $name already running (pid $(cat "$pid_file"))"
    return
  fi

  echo "[2/5] Starting $name ..."
  nohup "$VENV_PYTHON" -u "$script_path" >"$log_file" 2>&1 &
  echo $! > "$pid_file"
  echo "[OK] $name pid=$(cat "$pid_file") log=$log_file"
}

check_api() {
  echo "[3/5] Checking API..."
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/test" || true)
  if [[ "$code" != "200" ]]; then
    echo "[WARN] API check failed at $API_BASE/api/test (HTTP $code)."
    echo "       Start API first: uvicorn main:app --reload"
  else
    echo "[OK] API is reachable."
  fi
}

send_order() {
  local customer="${1:-Demo Customer}"
  local phone="${2:-0909000000}"
  local address="${3:-123 Demo Street}"

  echo "[4/5] Sending one fake order to Kafka endpoint..."
  curl -s -X POST "$API_BASE/api/demo/kafka/orders" \
    -H "Content-Type: application/json" \
    -d "{\"customer_name\":\"$customer\",\"phone\":\"$phone\",\"address\":\"$address\"}" || true
  echo
}

show_status() {
  echo "[5/5] Status"
  echo "- Kafka containers:"
  sudo docker compose -f "$KAFKA_COMPOSE_FILE" ps || true

  for name in vrp notification audit; do
    local pid_file="$PID_DIR/${name}.pid"
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      echo "- $name consumer: running (pid $(cat "$pid_file"))"
    else
      echo "- $name consumer: stopped"
    fi
  done

  echo "- Logs directory: $LOG_DIR"
}

stop_consumers() {
  echo "Stopping consumers..."
  for name in vrp notification audit; do
    local pid_file="$PID_DIR/${name}.pid"
    if [[ -f "$pid_file" ]]; then
      local pid
      pid="$(cat "$pid_file")"
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" || true
        echo "- Stopped $name (pid $pid)"
      fi
      rm -f "$pid_file"
    fi
  done
}

logs_tail() {
  local lines="${1:-30}"
  for name in vrp notification audit; do
    local log_file="$LOG_DIR/${name}.log"
    echo "===== $name.log ====="
    if [[ -f "$log_file" ]]; then
      tail -n "$lines" "$log_file"
    else
      echo "(no log yet)"
    fi
  done

  echo "===== audit_raw_orders.txt (latest) ====="
  if [[ -f "$DEMO_DIR/audit_raw_orders.txt" ]]; then
    tail -n 10 "$DEMO_DIR/audit_raw_orders.txt"
  else
    echo "(no audit records yet)"
  fi
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0") start
  $(basename "$0") send [customer] [phone] [address]
  $(basename "$0") status
  $(basename "$0") logs [lines]
  $(basename "$0") stop

Examples:
  $(basename "$0") start
  $(basename "$0") send "Tran Thi B" "0909123123" "45 Hai Ba Trung"
  $(basename "$0") logs 50

Environment override:
  API_BASE=http://127.0.0.1:8000 $(basename "$0") start
EOF
}

cmd="${1:-}"
case "$cmd" in
  start)
    start_kafka
    start_consumer "vrp" "$DEMO_DIR/consumer_vrp_solver.py"
    start_consumer "notification" "$DEMO_DIR/consumer_notification.py"
    start_consumer "audit" "$DEMO_DIR/consumer_audit.py"
    check_api
    show_status
    ;;
  send)
    shift
    send_order "${1:-Demo Customer}" "${2:-0909000000}" "${3:-123 Demo Street}"
    ;;
  status)
    show_status
    ;;
  logs)
    shift
    logs_tail "${1:-30}"
    ;;
  stop)
    stop_consumers
    ;;
  *)
    usage
    exit 1
    ;;
esac
