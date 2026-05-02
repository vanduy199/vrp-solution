# 🏗️ VRP Solution - Redesign Plan

> Tài liệu thiết kế lại toàn bộ backend VRP. Mục tiêu: chuẩn hoá schema (FK, kiểu dữ liệu), tách concerns, giảm trùng lắp.

---

## 1. Vấn đề hiện tại

| # | Vấn đề | Ảnh hưởng |
|---|---|---|
| 1 | `Route` và `RouteDetail` trùng lắp (cùng vehicle_id, distance, duration) | Dữ liệu không nhất quán |
| 2 | `Vehicle.depot_lat/depot_lon` denormalized thay vì FK `depot_id` | Không thể share depot, khó update |
| 3 | `ActiveRoute.driver_name` denormalized (không FK `User`) | Rename user không sync |
| 4 | `DriverStop` thiếu FK `route_id`, `point_id`, `sequence_index` | Không biết stop thuộc route nào, không có thứ tự |
| 5 | `Point.time_window_start/end` là `String` thay vì `Time` | Không validate, khó so sánh |
| 6 | `RouteDetail.stops` là JSON array các string id (không FK) | Không join được, không track status từng stop |
| 7 | PK không nhất quán: `id` / `vehicle_id` / `route_id` / `job_id` / `stop_id` | Khó dùng chung convention |
| 8 | `Vehicle.volumn_m3` (sai chính tả) | Code smell |
| 9 | `v1_controller.py` (54KB, 1471 dòng) | Khó maintain |
| 10 | Business logic nhồi trong controller (assignment, solver, materialization) | Không test được |
| 11 | Timezone không nhất quán (có chỗ là String, có chỗ DateTime) | Bug tiềm tàng |
| 12 | `create_all()` chạy mỗi lần khởi động, không có migration | Không thể evolve schema an toàn |

---

## 2. Schema mới (Normalized)

### 2.1 `users`
| Field | Type | Note |
|---|---|---|
| `id` | UUID PK | |
| `full_name` | String NOT NULL | |
| `role` | Enum(`admin`,`dispatcher`,`driver`) NOT NULL | |
| `email` | String UNIQUE | |
| `phone` | String | |
| `created_at` | DateTime(tz) NOT NULL | default now |
| `updated_at` | DateTime(tz) NOT NULL | auto-update |

### 2.2 `depots`
| Field | Type | Note |
|---|---|---|
| `id` | UUID PK | |
| `name` | String NOT NULL | |
| `lat` | Float NOT NULL | |
| `lng` | Float NOT NULL | |
| `address` | String | |
| `operating_windows` | JSON | `[{"start":"06:00","end":"18:00"}]` |
| `created_at` / `updated_at` | DateTime(tz) | |

### 2.3 `vehicles`
| Field | Type | Note |
|---|---|---|
| `id` | UUID PK | |
| `name` | String NOT NULL | |
| `license_plate` | String | |
| `status` | Enum(`available`,`in_use`,`maintenance`,`retired`) | default `available` |
| `capacity_kg` | Integer NOT NULL | |
| `volume_m3` | Float | ← fixed typo |
| `cost_per_km` | Float | |
| `cost_per_hour` | Float | |
| `max_shift_hours` | Integer | |
| `ev` | Boolean | default false |
| `depot_id` | FK → `depots.id` | NOT NULL |
| `driver_id` | FK → `users.id` NULLABLE | role=`driver` |
| `created_at` / `updated_at` | | |

### 2.4 `locations` (đổi tên từ `points`)
| Field | Type | Note |
|---|---|---|
| `id` | UUID PK | |
| `name` | String NOT NULL | |
| `address` | String | |
| `lat` | Float NOT NULL | |
| `lng` | Float NOT NULL | |
| `demand_kg` | Integer | default 0 |
| `priority` | Integer | default 0 |
| `phone` | String | |
| `time_window_start` | Time | |
| `time_window_end` | Time | |
| `service_time_mins` | Integer | default 0 |
| `created_at` / `updated_at` | | |

### 2.5 `optimization_jobs`
| Field | Type | Note |
|---|---|---|
| `id` | UUID PK | (thay `job_id`) |
| `project_id` | String NOT NULL | |
| `solver_algorithm` | Enum(`nearest_neighbor`,`genetic_algorithm`,`clarke_wright_savings`) | |
| `objective` | Enum(`minimize_distance`,`minimize_time`,`minimize_cost`) | |
| `status` | Enum(`pending`,`calculating`,`completed`,`failed`,`cancelled`) | |
| `vehicle_ids` | JSON array of UUID | snapshot |
| `location_ids` | JSON array of UUID | snapshot |
| `constraints` | JSON | |
| `estimated_time_seconds` | Float | |
| `result` | JSON | error/summary |
| `created_at` / `ready_at` / `completed_at` | | |

### 2.6 `routes` (gộp `Route` + `RouteDetail`)
| Field | Type | Note |
|---|---|---|
| `id` | UUID PK | |
| `job_id` | FK → `optimization_jobs.id` | NULL nếu manual |
| `vehicle_id` | FK → `vehicles.id` NOT NULL | |
| `depot_id` | FK → `depots.id` NOT NULL | |
| `status` | Enum(`planned`,`dispatched`,`in_progress`,`completed`,`cancelled`) | default `planned` |
| `status_note` | Text | |
| `total_distance_km` | Float | |
| `total_duration_mins` | Float | |
| `total_cost` | Float | |
| `load_kg` | Integer | |
| `utilization_pct` | Float | |
| `created_at` / `updated_at` / `dispatched_at` / `completed_at` | | |

### 2.7 `route_stops` (thay cho `RouteDetail.stops` JSON)
| Field | Type | Note |
|---|---|---|
| `id` | UUID PK | |
| `route_id` | FK → `routes.id` ON DELETE CASCADE | |
| `location_id` | FK → `locations.id` | |
| `sequence_index` | Integer NOT NULL | thứ tự trong route |
| `status` | Enum(`pending`,`en_route`,`arrived`,`completed`,`failed`,`skipped`) | default `pending` |
| `planned_eta` | DateTime(tz) | |
| `actual_arrived_at` | DateTime(tz) | |
| `actual_completed_at` | DateTime(tz) | |
| `proof_of_delivery_url` | String | |
| `notes` | Text | |
| UNIQUE(`route_id`, `sequence_index`) | | |

### 2.8 `active_routes` (tracking realtime)
| Field | Type | Note |
|---|---|---|
| `route_id` | FK → `routes.id` PK | 1:1 với route |
| `progress_percentage` | Float | |
| `current_lat` / `current_lng` | Float | |
| `current_stop_id` | FK → `route_stops.id` NULLABLE | stop đang xử lý |
| `next_stop_id` | FK → `route_stops.id` NULLABLE | |
| `delay_mins` | Integer | default 0 |
| `tracking_status` | Enum(`on_time`,`delayed`,`off_route`) | |
| `updated_at` | | |

### 2.9 ER tóm tắt
```
users ─┬─< vehicles >── depots
       └─< (driver)
depots ──< routes
vehicles ──< routes ──> optimization_jobs
routes ──< route_stops >── locations
routes ──1:1── active_routes
```

---

## 3. Cấu trúc thư mục mới

```
app/
├── core/
│   ├── config.py              # settings (env)
│   ├── database.py            # engine, SessionLocal, get_db
│   ├── logger.py
│   └── enums.py               # UserRole, VehicleStatus, RouteStatus, ...
├── models/                     # SQLAlchemy ORM
│   ├── __init__.py            # export all models
│   ├── base.py                # Base, TimestampMixin
│   ├── user.py
│   ├── depot.py
│   ├── vehicle.py
│   ├── location.py
│   ├── optimization_job.py
│   ├── route.py
│   ├── route_stop.py
│   └── active_route.py
├── schemas/                    # Pydantic DTO (đổi từ dto/)
│   ├── __init__.py
│   ├── common.py              # Coordinates, Pagination, TimeWindow
│   ├── user.py
│   ├── depot.py
│   ├── vehicle.py
│   ├── location.py
│   ├── optimization.py
│   ├── route.py
│   └── driver.py
├── repositories/               # Data access (1 file / model)
│   ├── base.py                # BaseRepository[T]
│   ├── user_repo.py
│   ├── depot_repo.py
│   ├── vehicle_repo.py
│   ├── location_repo.py
│   ├── optimization_job_repo.py
│   ├── route_repo.py
│   └── route_stop_repo.py
├── services/                   # Business logic
│   ├── vehicle_service.py
│   ├── location_service.py
│   ├── optimization_service.py  # orchestrate solver
│   ├── route_service.py         # dispatch, complete, adjust
│   ├── driver_service.py        # manifest, stop status update
│   ├── metrics_service.py       # KPIs
│   ├── manifest_service.py      # CSV/Excel upload
│   └── kafka_service.py
├── algorithms/                 # Pure algorithm logic
│   ├── distance.py            # haversine, matrix builder
│   ├── nearest_neighbor.py
│   ├── genetic_algorithm.py
│   └── assignment.py          # greedy capacity assignment
├── api/
│   ├── deps.py                # common dependencies
│   ├── v1/
│   │   ├── __init__.py        # v1 router aggregator
│   │   ├── fleet.py           # /v1/fleet/*
│   │   ├── locations.py       # /v1/locations/*
│   │   ├── optimize.py        # /v1/optimize/*
│   │   ├── routes.py          # /v1/routes/*
│   │   ├── driver.py          # /v1/driver/*
│   │   ├── metrics.py         # /v1/metrics/*
│   │   ├── users.py           # /v1/users/*
│   │   └── depots.py          # /v1/locations/depots/*
│   └── router.py              # include v1 router
├── utils/
│   ├── validators.py
│   └── time.py                # as_utc, parse_time_window
└── main.py (giữ ở root)
```

---

## 4. API mapping (Old → New)

Tất cả endpoints giữ path cũ (backward compatible) nhưng organize lại:

| Path | File mới |
|---|---|
| `GET /api/` (health) | `api/v1/__init__.py` hoặc root |
| `GET|POST|PUT|DELETE /api/v1/fleet/vehicles[...]` | `api/v1/fleet.py` |
| `GET|POST|PUT|DELETE /api/v1/locations[...]` | `api/v1/locations.py` |
| `POST /api/v1/locations/depots` + CRUD | `api/v1/depots.py` |
| `POST /api/v1/locations/upload-manifest` | `api/v1/locations.py` |
| `POST /api/v1/optimize/run` | `api/v1/optimize.py` |
| `GET /api/v1/optimize/jobs`, `/job/{id}`, `/job/{id}/result`, `/job/{id}/cancel` | `api/v1/optimize.py` |
| `GET /api/v1/routes`, `/routes/{id}`, `/routes/active` | `api/v1/routes.py` |
| `POST /api/v1/routes/{id}/dispatch|complete|adjust|status` | `api/v1/routes.py` |
| `DELETE /api/v1/routes/{id}` | `api/v1/routes.py` |
| `GET /api/v1/routes/{id}/manifest` | `api/v1/routes.py` |
| `GET /api/v1/driver/manifest` | `api/v1/driver.py` |
| `PUT /api/v1/driver/stops/{id}/status` | `api/v1/driver.py` |
| `GET /api/v1/metrics/dashboard`, `/metrics/routes/{id}` | `api/v1/metrics.py` |
| `POST /api/v1/users` + CRUD | `api/v1/users.py` |
| Legacy `POST /api/optimize/nearest-neighbor`, `/genetic-algorithm` | ❌ Xoá (gộp vào `/v1/optimize/run`) |
| Legacy `GET|POST|PUT|DELETE /api/points` | ❌ Xoá (dùng `/v1/locations`) |
| `GET /api/test` (kafka demo) | Di chuyển vào internal / dev-only |

---

## 5. Migration Strategy

Do schema thay đổi lớn (đổi tên bảng `points` → `locations`, gộp `routes`+`route_details`, thêm FK), cần **reset DB** hoặc viết migration script.

**Tùy chọn:**

1. **Reset DB (nhanh nhất, cho dev)** — drop toàn bộ bảng, `create_all()` lại. Mất dữ liệu cũ.
2. **Alembic migration** — giữ data, viết migration chuyển đổi. Tốn thời gian.

Đề xuất: **reset DB cho lần đầu** (vì đang ở giai đoạn dev), sau đó setup Alembic cho các thay đổi tiếp theo.

---

## 6. Kế hoạch triển khai (theo thứ tự)

1. ✅ Design doc (file này)
2. `core/` (config, database, enums)
3. `models/` mới + relationships
4. `schemas/` Pydantic
5. `repositories/`
6. `services/`
7. `api/v1/` routers
8. `main.py` update (include router mới)
9. Xoá code cũ (`controllers/`, `dto/`, `database/models.py`, `database/repositories.py`)
10. Reset DB + test endpoints

---

## 7. Breaking changes với frontend

- `Vehicle.depot_lat/depot_lon` → `depot_id` + nested `depot: {lat, lng}` trong response.
- `DriverStop.stop_id` giờ là UUID thật, thuộc về 1 route cụ thể.
- `/routes/{id}.stops` trả về array object `{location_id, sequence, status, eta, ...}` thay vì array string id.
- Time windows: trả về format `"HH:MM:SS"` nhất quán (parseable thành `Time`).
- Tất cả ID sẽ là UUID thay vì string tuỳ ý (nhưng vẫn nhận được user-supplied id khi tạo).

Frontend cần adapt theo những thay đổi này.
