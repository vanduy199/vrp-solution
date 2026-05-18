#!/usr/bin/env bash
# =============================================================================
# run_local.sh — Khởi chạy VRP Solution trên máy local
# Cách dùng: chmod +x run_local.sh && ./run_local.sh [OPTIONS]
#
# OPTIONS:
#   --port PORT       API port (mặc định: 8000)
#   --no-reload       Tắt auto-reload (mặc định: bật)
#   --viz             Chạy thêm Streamlit visualization (port 8501)
#   --frontend        Alias cho --viz (legacy)
# =============================================================================

set -euo pipefail

# ── Màu sắc terminal ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log_info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${BOLD}══════════════════════════════════════════${NC}"; echo -e "${BOLD} $*${NC}"; echo -e "${BOLD}══════════════════════════════════════════${NC}"; }

# ── Defaults ──────────────────────────────────────────────────────────────────
API_PORT=8000
RELOAD_FLAG="--reload"
RUN_FRONTEND=false
RUN_VIZ=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Parse arguments ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)        API_PORT="$2"; shift 2 ;;
    --no-reload)   RELOAD_FLAG=""; shift ;;
    --viz)         RUN_VIZ=true; shift ;;
    --frontend)    RUN_FRONTEND=true; shift ;;
    -h|--help)
      echo "Cách dùng: $0 [--port PORT] [--no-reload] [--viz]"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

cd "$SCRIPT_DIR"

log_section "VRP Solution — Local Runner"

# ── 1. Kiểm tra Python ────────────────────────────────────────────────────────
log_info "Kiểm tra Python..."
if ! command -v python3 &>/dev/null; then
  log_error "python3 không tìm thấy. Vui lòng cài Python 3.11+."
  exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log_ok "Python ${PYTHON_VERSION} được tìm thấy."

# ── 2. Tạo / Kích hoạt virtual environment ────────────────────────────────────
log_info "Kiểm tra virtual environment..."
VENV_DIR=".venv"

if [[ ! -d "$VENV_DIR" ]]; then
  log_info "Tạo virtual environment tại ./${VENV_DIR} ..."
  python3 -m venv "$VENV_DIR"
  log_ok "Virtual environment đã được tạo."
else
  log_ok "Virtual environment đã tồn tại."
fi

# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"
log_ok "Virtual environment đã được kích hoạt."

# ── 3. Kiểm tra / tạo file .env ──────────────────────────────────────────────
log_info "Kiểm tra file .env ..."
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    log_warn ".env chưa tồn tại — đã copy từ .env.example."
    log_warn "Hãy kiểm tra lại .env và điền các giá trị cần thiết (DB, API keys, ...)."
  else
    log_error ".env và .env.example đều không tồn tại!"
    exit 1
  fi
else
  log_ok ".env đã tồn tại."
fi

# ── 5. Tạo thư mục logs nếu chưa có ─────────────────────────────────────────
if [[ ! -d "logs" ]]; then
  mkdir -p logs
  log_info "Tạo thư mục logs/."
fi

# ── 6. Kiểm tra port có đang được dùng không ─────────────────────────────────
log_info "Kiểm tra port ${API_PORT} ..."
if lsof -iTCP:"${API_PORT}" -sTCP:LISTEN -t &>/dev/null 2>&1; then
  log_warn "Port ${API_PORT} đang bị chiếm. Thử dùng: ./run_local.sh --port 8001"
fi

# ── 7. Khởi chạy FastAPI ──────────────────────────────────────────────────────
log_section "Khởi chạy API Server"
log_info "API docs : http://localhost:${API_PORT}/docs"
log_info "ReDoc    : http://localhost:${API_PORT}/redoc"
log_info "Health   : http://localhost:${API_PORT}/api/health"
echo ""

if [[ "$RUN_VIZ" == true ]] || [[ "$RUN_FRONTEND" == true ]]; then
  log_info "Chạy API + Streamlit visualization song song..."

  uvicorn main:app --host 0.0.0.0 --port "${API_PORT}" ${RELOAD_FLAG} &
  API_PID=$!
  log_ok "API đang chạy (PID: ${API_PID})"

  # Đợi API khởi động
  sleep 2

  log_section "Khởi chạy Streamlit Visualization"
  log_info "Visualization : http://localhost:8501"
  echo ""

  streamlit run app/dashboard/route_viz.py \
    --server.port 8501 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --server.headless true &
  VIZ_PID=$!
  log_ok "Streamlit đang chạy (PID: ${VIZ_PID})"

  log_info "Nhấn Ctrl+C để dừng tất cả."
  trap "log_info 'Đang dừng...'; kill ${API_PID} ${VIZ_PID} 2>/dev/null; exit 0" INT TERM

  wait
else
  exec uvicorn main:app \
    --host 0.0.0.0 \
    --port "${API_PORT}" \
    ${RELOAD_FLAG}
fi
