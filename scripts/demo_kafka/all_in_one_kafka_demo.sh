#!/usr/bin/env bash
set -euo pipefail

# All-in-one Kafka Fan-out Demo Script
#
# Quick usage:
#   ./scripts/demo_kafka/all_in_one_kafka_demo.sh demo
#
# Commands:
#   ./scripts/demo_kafka/all_in_one_kafka_demo.sh demo
#     - Start Kafka + API + 3 consumers, send one fake order, then show logs.
#
#   ./scripts/demo_kafka/all_in_one_kafka_demo.sh start
#     - Start Kafka + API + 3 consumers only.
#
#   ./scripts/demo_kafka/all_in_one_kafka_demo.sh send "Tran Thi B" "0909123123" "45 Hai Ba Trung"
#     - Send one fake order event to /api/demo/kafka/orders.
#
#   ./scripts/demo_kafka/all_in_one_kafka_demo.sh logs 50
#     - Show latest logs from API/consumers and latest audit records.
#
#   ./scripts/demo_kafka/all_in_one_kafka_demo.sh status
#     - Show Kafka container status and local process status.
#
#   ./scripts/demo_kafka/all_in_one_kafka_demo.sh stop
#     - Stop local API/consumers and stop Kafka containers.
#
# Optional env vars:
#   API_PORT=8000
#   API_BASE=http://127.0.0.1:8000

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT_DIR="$ROOT_DIR/scripts/demo_kafka"
LOG_DIR="$SCRIPT_DIR/logs_all_in_one"
PID_DIR="$SCRIPT_DIR/pids_all_in_one"
API_PORT="${API_PORT:-8000}"
API_BASE="${API_BASE:-http://127.0.0.1:${API_PORT}}"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
COMPOSE_FILE="$ROOT_DIR/docker-compose.kafka.yml"

mkdir -p "$LOG_DIR" "$PID_DIR"

API_PID_FILE="$PID_DIR/api.pid"
VRP_PID_FILE="$PID_DIR/vrp.pid"
NOTI_PID_FILE="$PID_DIR/notification.pid"
AUDIT_PID_FILE="$PID_DIR/audit.pid"

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] Missing command: $cmd"
    exit 1
  fi
}

start_kafka() {
  echo "[Step 1] Start Kafka stack"
  require_cmd sudo
  require_cmd docker
  sudo docker compose -f "$COMPOSE_FILE" up -d
}

api_is_up() {
  local code
  code="$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE/api/test" || true)"
  [[ "$code" == "200" ]]
}

start_api() {
  echo "[Step 2] Start API"
  if api_is_up; then
    echo "[OK] API already running at $API_BASE"
    return
  fi

  if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "[ERROR] Python venv not found at $VENV_PYTHON"
    exit 1
  fi

  nohup "$VENV_PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "$API_PORT" >"$LOG_DIR/api.log" 2>&1 &
  echo $! > "$API_PID_FILE"

  for _ in $(seq 1 30); do
    if api_is_up; then
      echo "[OK] API started at $API_BASE"
      return
    fi
    sleep 1
  done

  echo "[ERROR] API did not become ready. Check $LOG_DIR/api.log"
  exit 1
}

start_one_consumer() {
  local name="$1"
  local script="$2"
  local pid_file="$3"
  local log_file="$LOG_DIR/${name}.log"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "[SKIP] $name consumer already running"
    return
  fi

  nohup "$VENV_PYTHON" -u "$script" >"$log_file" 2>&1 &
  echo $! > "$pid_file"
  echo "[OK] $name consumer started (pid $(cat "$pid_file"))"
}

start_consumers() {
  echo "[Step 3] Start 3 consumer groups"
  start_one_consumer "vrp" "$SCRIPT_DIR/consumer_vrp_solver.py" "$VRP_PID_FILE"
  start_one_consumer "notification" "$SCRIPT_DIR/consumer_notification.py" "$NOTI_PID_FILE"
  start_one_consumer "audit" "$SCRIPT_DIR/consumer_audit.py" "$AUDIT_PID_FILE"
}

send_order() {
  local customer="${1:-Demo Customer}"
  local phone="${2:-0909000000}"
  local address="${3:-123 Demo Street}"

  echo "[Step 4] Send one fake order"
  curl -s -X POST "$API_BASE/api/demo/kafka/orders" \
    -H "Content-Type: application/json" \
    -d "{\"customer_name\":\"$customer\",\"phone\":\"$phone\",\"address\":\"$address\"}"
  echo
}

show_logs() {
  local lines="${1:-40}"
  echo "[Step 5] Show logs (last $lines lines)"

  for name in api vrp notification audit; do
    echo "===== ${name}.log ====="
    if [[ -f "$LOG_DIR/${name}.log" ]]; then
      tail -n "$lines" "$LOG_DIR/${name}.log"
    else
      echo "(no log yet)"
    fi
  done

  echo "===== audit_raw_orders.txt (latest) ====="
  if [[ -f "$SCRIPT_DIR/audit_raw_orders.txt" ]]; then
    tail -n 10 "$SCRIPT_DIR/audit_raw_orders.txt"
  else
    echo "(no audit records yet)"
  fi
}

show_status() {
  echo "Kafka containers:"
  sudo docker compose -f "$COMPOSE_FILE" ps || true

  for pair in \
    "api:$API_PID_FILE" \
    "vrp:$VRP_PID_FILE" \
    "notification:$NOTI_PID_FILE" \
    "audit:$AUDIT_PID_FILE"; do
    local name="${pair%%:*}"
    local pid_file="${pair#*:}"
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      echo "- $name: running (pid $(cat "$pid_file"))"
    else
      echo "- $name: stopped"
    fi
  done
}

stop_by_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
    fi
    rm -f "$pid_file"
  fi
}

stop_all() {
  echo "Stopping local processes..."
  stop_by_pid_file "$VRP_PID_FILE"
  stop_by_pid_file "$NOTI_PID_FILE"
  stop_by_pid_file "$AUDIT_PID_FILE"
  stop_by_pid_file "$API_PID_FILE"

  echo "Stopping Kafka containers..."
  sudo docker compose -f "$COMPOSE_FILE" down || true
}

usage() {
  cat <<EOF
All-in-one Kafka Fan-out Demo

Usage:
  $(basename "$0") demo [customer] [phone] [address]
  $(basename "$0") start
  $(basename "$0") send [customer] [phone] [address]
  $(basename "$0") logs [lines]
  $(basename "$0") status
  $(basename "$0") stop

Examples:
  $(basename "$0") demo
  $(basename "$0") demo "Tran Thi B" "0909123123" "45 Hai Ba Trung"
  $(basename "$0") start
  $(basename "$0") send "Nguyen Van A" "0909000001" "1 Le Loi"

Optional env:
  API_PORT=8000 API_BASE=http://127.0.0.1:8000
EOF
}

cmd="${1:-demo}"
case "$cmd" in
  demo)
    shift
    start_kafka
    start_api
    start_consumers
    sleep 1
    send_order "${1:-Demo Customer}" "${2:-0909000000}" "${3:-123 Demo Street}"
    sleep 2
    show_logs 40
    ;;
  start)
    start_kafka
    start_api
    start_consumers
    show_status
    ;;
  send)
    shift
    send_order "${1:-Demo Customer}" "${2:-0909000000}" "${3:-123 Demo Street}"
    ;;
  logs)
    shift
    show_logs "${1:-40}"
    ;;
  status)
    show_status
    ;;
  stop)
    stop_all
    ;;
  *)
    usage
    exit 1
    ;;
esac
