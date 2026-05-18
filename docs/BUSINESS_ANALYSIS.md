# Phân Tích Nghiệp Vụ — VRP Solution

> Cập nhật lần cuối: 2026-05-17

---

## 1. Tổng Quan Hệ Thống

Hệ thống tối ưu hoá lộ trình giao hàng (Vehicle Routing Problem) cho phép:
- Quản lý **kho hàng (Depot)**, **xe (Vehicle)**, **tài xế (Driver)**
- Nhập **điểm giao hàng (Location)** thủ công hoặc qua file manifest
- Chạy **thuật toán tối ưu** để phân công lộ trình tự động
- **Dispatch & tracking** lộ trình thời gian thực

**Stack:** FastAPI + SQLAlchemy + SQLite/PostgreSQL | React + TypeScript + Tailwind

---

## 2. Các Thực Thể Chính

| Thực thể | Bảng / Model | Mô tả |
|---|---|---|
| `User` | `user` | Người dùng hệ thống, có role |
| `Depot` | `depot` | Kho xuất phát của xe |
| `Vehicle` | `vehicle` | Xe tải, gắn với Depot |
| `Driver` | `driver` | Tài xế, gắn với Depot |
| `Location` | `location` | Điểm giao hàng (có tọa độ + demand_kg) |
| `OptimizationJob` | `optimization_job` | Một lần chạy thuật toán |
| `Route` | `route` | Lộ trình của 1 xe sau khi optimize |
| `RouteStop` | `route_stop` | Từng điểm dừng trong lộ trình |
| `ActiveRoute` | `active_route` | Trạng thái tracking realtime |
| `UserDepot` | `user_depot` | Mapping user ↔ depot (scope) |

---

## 3. Luồng Nghiệp Vụ Chính

### 3.1 Setup (Cấu hình ban đầu)

```
Admin đăng ký / đăng nhập
    → Tạo Depot (tên, địa chỉ, tọa độ)
    → Tạo Vehicle (biển số, tải trọng kg, chi phí/km, gắn Depot)
    → Tạo Driver (họ tên, SĐT, gắn Depot)
    → Gắn Driver vào Vehicle
```

### 3.2 Nhập Điểm Giao Hàng

```
Dispatcher nhập Location:
    Cách 1: Form thủ công (tên, địa chỉ, lat/lng, demand_kg, time_window)
             → Tìm kiếm địa chỉ qua Geocoding API (LocationIQ / Serper)
    Cách 2: Upload file manifest (CSV/JSON)
             → POST /api/v1/locations/upload-manifest
```

### 3.3 Tối Ưu Lộ Trình

```
Dispatcher chọn:
    - Danh sách vehicle_ids
    - Danh sách location_ids
    - Thuật toán (nearest_neighbor / genetic_algorithm)
    - Objective (minimize_distance / minimize_time / minimize_cost)
    - Constraints (strict_time_windows, respect_capacity, avoid_tolls)

→ POST /api/v1/optimize/run  →  Job tạo ra với status=CALCULATING
→ GET  /api/v1/optimize/job/{id}  (polling mỗi 2s)
→ Khi ready_at đến: materialize_job() chạy thuật toán
→ Job status → COMPLETED, tạo Route + RouteStop vào DB
```

**Thuật toán hiện có:**

| Tên | Enum | Thực thi |
|---|---|---|
| Nearest Neighbor / Sweep | `nearest_neighbor` | `solve_cvrp(..., algorithm="sweep")` |
| Genetic Algorithm | `genetic_algorithm` | `genetic_algorithm_vrp(...)` |
| Clarke-Wright Savings | `clarke_wright_savings` | *(enum có, chưa implement riêng — fallback sweep)* |

### 3.4 Dispatch & Tracking

```
Route status flow:
  PLANNED → DISPATCHED → IN_PROGRESS → COMPLETED
                                     ↘ CANCELLED

POST /routes/{id}/dispatch    → DISPATCHED
POST /routes/{id}/complete    → COMPLETED
POST /routes/{id}/status      → cập nhật bất kỳ
POST /routes/{id}/adjust      → điều chỉnh lộ trình
```

**Stop status flow:**
```
PENDING → EN_ROUTE → ARRIVED → COMPLETED
                             ↘ FAILED / SKIPPED
```

**ActiveRoute** lưu tracking realtime:
- `current_lat / current_lng` — vị trí xe
- `tracking_status` — on_time / delayed / off_route
- `progress_percentage` — % hoàn thành
- `delay_mins` — số phút trễ
- `next_stop_id` — điểm dừng tiếp theo

### 3.5 Export

```
GET /routes/{id}/export?format=json   → JSON chi tiết
GET /routes/{id}/export?format=xlsx   → Tab-separated file
GET /routes/{id}/export?format=pdf    → Text-based PDF
GET /routes/{id}/manifest             → Danh sách stops đơn giản
```

---

## 4. Phân Quyền (Scope)

| Role | Quyền |
|---|---|
| `admin` | Toàn quyền, thấy tất cả Depot |
| `dispatcher` | Chỉ thấy Depot được assign qua `user_depot` |
| `driver` | Chỉ xem lộ trình của mình qua `/driver/` endpoints |

**Logic scope:** `get_user_depot_ids(db, user)` — nếu là admin trả tất cả, ngược lại trả depot_ids từ bảng `user_depot`.

---

## 5. Geocoding / Map Provider

| Provider | Kích hoạt qua | Đặc điểm |
|---|---|---|
| `locationiq` | `MAP_PROVIDER=locationiq` | OSM-based, autocomplete / reverse |
| `serper` | `MAP_PROVIDER=serper` | Google Maps data, có `gmap_url`, force VN |

**Serper VN filter:** Query tự động append `, Việt Nam` + params `gl=vn, hl=vi, location=Vietnam`.

**`gmap_url` flow:**
```
autocomplete API → PlaceSuggestion.gmap_url
    → Frontend dropdown: icon ExternalLink mở tab Google Maps
    → Sau khi chọn: icon MapPin trên input → ExternalLink (link tới địa điểm đã chọn)
```

---

## 6. Optimization Job — Lifecycle Chi Tiết

```
create_job()
    estimated_time = max(1.5, min(30.0, n_locations * 0.5))  giây
    ready_at = now + estimated_time
    status = CALCULATING

materialize_job()  [gọi mỗi khi GET job hoặc GET routes]
    if status != CALCULATING → skip
    if now < ready_at → skip (vẫn đang "tính")
    else:
        1. Load vehicles + locations từ DB
        2. Validate: phải có depot, vehicle tồn tại, location tồn tại
        3. Build Customer[] + Vehicle[] data structures
        4. Chạy VRP solver → VRPSolution
        5. Tạo Route + RouteStop records
        6. status → COMPLETED, lưu result JSON
```

**VRPSolution result JSON:**
```json
{
  "project_id": "...",
  "objective": "minimize_distance",
  "solver_algorithm": "nearest_neighbor",
  "total_distance_km": 42.5,
  "total_duration_mins": 120.3,
  "vehicles_used": 3,
  "routes": [
    {
      "route_id": "route-job-xxx-1",
      "vehicle_id": "...",
      "stop_count": 8,
      "load_kg": 450,
      "capacity_kg": 500,
      "utilization_pct": 90.0,
      "distance_km": 14.2,
      "duration_mins": 38.1,
      "total_cost": 71.0
    }
  ],
  "unassigned_customers": [],
  "unassigned_count": 0
}
```

---

## 7. API Endpoints Tóm Tắt

### Auth
| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/v1/auth/login` | Đăng nhập → JWT |
| POST | `/api/v1/auth/register` | Đăng ký |
| GET  | `/api/v1/auth/me` | Thông tin user hiện tại |
| POST | `/api/v1/auth/change-password` | Đổi mật khẩu |

### Depot
| Method | Path | Mô tả |
|---|---|---|
| GET    | `/api/v1/locations/depots` | Danh sách depot (theo scope) |
| POST   | `/api/v1/locations/depots` | Tạo depot |
| PUT    | `/api/v1/locations/depots/{id}` | Cập nhật |
| DELETE | `/api/v1/locations/depots/{id}` | Xoá |

### Fleet (Vehicle)
| Method | Path | Mô tả |
|---|---|---|
| GET    | `/api/v1/fleet/vehicles` | Danh sách xe (theo scope) |
| POST   | `/api/v1/fleet/vehicles` | Thêm xe |
| PUT    | `/api/v1/fleet/vehicles/{id}` | Cập nhật |
| DELETE | `/api/v1/fleet/vehicles/{id}` | Xoá |

### Driver
| Method | Path | Mô tả |
|---|---|---|
| GET    | `/api/v1/drivers` | Danh sách tài xế |
| POST   | `/api/v1/drivers` | Thêm tài xế |
| PUT    | `/api/v1/drivers/{id}` | Cập nhật |
| DELETE | `/api/v1/drivers/{id}` | Xoá |

### Location (Điểm giao)
| Method | Path | Mô tả |
|---|---|---|
| GET    | `/api/v1/locations/demand` | Tất cả điểm giao |
| POST   | `/api/v1/locations` | Thêm điểm |
| PUT    | `/api/v1/locations/{id}` | Cập nhật |
| DELETE | `/api/v1/locations/{id}` | Xoá |
| POST   | `/api/v1/locations/upload-manifest` | Upload hàng loạt |

### Optimization
| Method | Path | Mô tả |
|---|---|---|
| POST | `/api/v1/optimize/run` | Chạy thuật toán (202) |
| GET  | `/api/v1/optimize/jobs` | Danh sách jobs |
| GET  | `/api/v1/optimize/job/{id}` | Chi tiết job |
| GET  | `/api/v1/optimize/job/{id}/result` | Kết quả (chỉ khi COMPLETED) |
| POST | `/api/v1/optimize/job/{id}/cancel` | Huỷ job |

### Route
| Method | Path | Mô tả |
|---|---|---|
| GET    | `/api/v1/routes` | Danh sách lộ trình |
| GET    | `/api/v1/routes/active` | Lộ trình đang chạy |
| GET    | `/api/v1/routes/{id}` | Chi tiết |
| GET    | `/api/v1/routes/{id}/manifest` | Danh sách stops |
| GET    | `/api/v1/routes/{id}/export` | Export (json/xlsx/pdf) |
| POST   | `/api/v1/routes/{id}/dispatch` | Dispatch |
| POST   | `/api/v1/routes/{id}/complete` | Hoàn tất |
| POST   | `/api/v1/routes/{id}/status` | Cập nhật status |
| POST   | `/api/v1/routes/{id}/adjust` | Điều chỉnh lộ trình |
| DELETE | `/api/v1/routes/{id}` | Xoá |

### Geocoding
| Method | Path | Mô tả |
|---|---|---|
| GET | `/api/v1/geocode/autocomplete?q=&limit=` | Gợi ý địa chỉ |
| GET | `/api/v1/geocode/place/{place_id}` | Chi tiết địa điểm |
| GET | `/api/v1/geocode/forward?address=` | Address → tọa độ |
| GET | `/api/v1/geocode/reverse?lat=&lng=` | Tọa độ → address |

---

## 8. Các Điểm Cần Chú Ý / Known Issues

- **`clarke_wright_savings`** có trong enum nhưng không có implementation riêng — fallback sang `sweep`.
- **Export xlsx** hiện thực tế trả tab-separated `.txt`, không phải `.xlsx` thực sự.
- **Export pdf** trả plain text, không phải binary PDF.
- **`materialize_job`** chạy đồng bộ khi có GET request, không phải background task thực sự — có thể gây timeout với bộ dữ liệu lớn.
- **Kafka** được tích hợp nhưng chỉ dùng cho `test` endpoint, chưa áp dụng vào luồng chính.
