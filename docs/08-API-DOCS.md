# VRP Solver API — Tài liệu API

> Base URL: `http://localhost:8000/api`  
> Swagger UI: `http://localhost:8000/docs`  
> Phiên bản: 1.0.0

> 🔐 **Xác thực:** Tất cả endpoints (trừ `/auth/login` và `/auth/register`) yêu cầu header:  
> `Authorization: Bearer <access_token>`

---

## Mục lục

1. [Health Check](#1-health-check)
2. [Auth — Xác thực](#2-auth--xác-thực)
3. [Depot — Quản lý Kho bãi](#3-depot--quản-lý-kho-bãi)
4. [Users — Quản lý Người dùng](#4-users--quản-lý-người-dùng)
5. [Fleet — Quản lý Đội xe](#5-fleet--quản-lý-đội-xe)
6. [Locations — Quản lý Điểm giao hàng](#6-locations--quản-lý-điểm-giao-hàng)
7. [Optimize — Tối ưu hoá lộ trình](#7-optimize--tối-ưu-hoá-lộ-trình)
8. [Routes — Quản lý Lộ trình](#8-routes--quản-lý-lộ-trình)
9. [Driver — Ứng dụng Tài xế](#9-driver--ứng-dụng-tài-xế)
10. [Metrics — Thống kê](#10-metrics--thống-kê)
11. [Enums](#11-enums)
12. [Luồng nghiệp vụ đầy đủ](#12-luồng-nghiệp-vụ-đầy-đủ)

---

## 1. Health Check

### `GET /api/`
Kiểm tra API đang hoạt động.

**Response**
```json
{
  "status": "ok",
  "message": "VRP Solver API is running"
}
```

---

## 2. Auth — Xác thực

> Prefix: `/api/v1/auth`  
> Các endpoint trong section này **không yêu cầu** token.

---

### `POST /api/v1/auth/register`
Đăng ký tài khoản mới. Role mặc định là `dispatcher`.

**Request Body**
```json
{
  "full_name": "Nguyễn Văn A",
  "email": "user@company.com",
  "password": "Secret123!",
  "phone": "0901234567"
}
```

**Response** `201`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "user-3f2a1b9c",
    "full_name": "Nguyễn Văn A",
    "role": "dispatcher",
    "email": "user@company.com",
    "phone": "0901234567",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

**Errors**
- `409` — Email đã được đăng ký

---

### `POST /api/v1/auth/login`
Đăng nhập, lấy access token.

**Request Body**
```json
{
  "email": "user@company.com",
  "password": "Secret123!"
}
```

**Response** `200` — Giống `/register` ở trên.

**Errors**
- `401` — Sai email hoặc mật khẩu

---

### `GET /api/v1/auth/me`
🔐 Xem thông tin user đang đăng nhập.

**Response** `200` — `UserResponse`

---

### `POST /api/v1/auth/change-password`
🔐 Đổi mật khẩu.

**Request Body**
```json
{
  "old_password": "Secret123!",
  "new_password": "NewSecret456!"
}
```

**Response** `204` — No Content  
**Errors**
- `401` — Mật khẩu cũ không đúng

---

## 3. Depot — Quản lý Kho bãi

> Prefix: `/api/v1/locations/depots`

Depot là **điểm xuất phát và kết thúc** của mọi lộ trình xe. Mỗi xe phải thuộc về 1 depot.

---

### `GET /api/v1/locations/depots`
Lấy danh sách tất cả depot.

**Response** `200`
```json
[
  {
    "id": "depot-3f2a1b9c",
    "name": "Kho Tổng Miền Bắc",
    "coordinates": { "lat": 21.0285, "lng": 105.8542 },
    "address": "Số 1 Hà Nội",
    "operating_windows": ["06:00-18:00"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### `POST /api/v1/locations/depots`
Tạo depot mới.

**Request Body**
```json
{
  "id": "depot-hanoi",
  "name": "Kho Tổng Miền Bắc",
  "coordinates": { "lat": 21.0285, "lng": 105.8542 },
  "address": "Số 1 Hà Nội",
  "operating_windows": ["06:00-18:00"]
}
```
> `id` là tuỳ chọn — nếu bỏ trống sẽ tự sinh.

**Response** `201` — Depot vừa tạo.

---

### `GET /api/v1/locations/depots/{depot_id}`
Lấy chi tiết 1 depot.

**Response** `200` — DepotResponse  
**Response** `404` — `{ "detail": "Depot not found" }`

---

### `PUT /api/v1/locations/depots/{depot_id}`
Cập nhật depot.

**Request Body** (tất cả fields là tuỳ chọn)
```json
{
  "name": "Kho Mới",
  "coordinates": { "lat": 21.03, "lng": 105.86 },
  "operating_windows": ["07:00-19:00"]
}
```

---

### `DELETE /api/v1/locations/depots/{depot_id}`
Xoá depot.

> ⚠️ Không thể xoá depot còn xe đang gán.

**Response** `204` — No Content  
**Response** `409` — Depot còn xe

---

## 4. Users — Quản lý Người dùng

> Prefix: `/api/v1/users`

---

### `GET /api/v1/users`
Danh sách người dùng.

---

### `POST /api/v1/users`
Tạo người dùng mới.

**Request Body**
```json
{
  "full_name": "Nguyễn Văn A",
  "role": "driver",
  "email": "driver.a@company.com",
  "phone": "0901234567"
}
```

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| `full_name` | string | ✅ | |
| `role` | enum | ✅ | `admin` / `dispatcher` / `driver` |
| `email` | email | ❌ | Phải unique |
| `phone` | string | ❌ | |

---

### `GET /api/v1/users/{user_id}`
Chi tiết user.

---

### `PUT /api/v1/users/{user_id}`
Cập nhật user.

---

### `DELETE /api/v1/users/{user_id}`
Xoá user.

---

## 5. Fleet — Quản lý Đội xe

> Prefix: `/api/v1/fleet`

---

### `GET /api/v1/fleet/vehicles`
Danh sách tất cả xe.

**Response** `200`
```json
[
  {
    "id": "veh-a1b2c3d4",
    "name": "Freightliner M2",
    "license_plate": "51A-12345",
    "status": "available",
    "capacity_kg": 2500,
    "volume_m3": 15.0,
    "cost_per_km": 1.45,
    "cost_per_hour": null,
    "max_shift_hours": 8,
    "ev": false,
    "depot_id": "depot-hanoi",
    "driver_id": "user-abc123",
    "driver_name": "Nguyễn Văn A",
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### `POST /api/v1/fleet/vehicles`
Thêm xe mới.

**Request Body**
```json
{
  "name": "Freightliner M2",
  "license_plate": "51A-12345",
  "status": "available",
  "capacity_kg": 2500,
  "volume_m3": 15.0,
  "cost_per_km": 1.45,
  "ev": false,
  "depot_id": "depot-hanoi",
  "driver_id": "user-abc123"
}
```

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| `name` | string | ✅ | |
| `depot_id` | string | ✅ | Phải tồn tại trong DB |
| `capacity_kg` | int ≥ 0 | ❌ | Default 0 |
| `volume_m3` | float ≥ 0 | ❌ | Default 0 |
| `cost_per_km` | float ≥ 0 | ❌ | Default 0 |
| `ev` | bool | ❌ | Default false |
| `driver_id` | string | ❌ | Gán tài xế (role=driver) |

---

### `GET /api/v1/fleet/vehicles/{vehicle_id}`
Chi tiết xe.

---

### `PUT /api/v1/fleet/vehicles/{vehicle_id}`
Cập nhật xe (tất cả fields tuỳ chọn).

---

### `DELETE /api/v1/fleet/vehicles/{vehicle_id}`
Xoá xe.

> ⚠️ Không thể xoá xe đang có route active.

**Response** `409` nếu có route đang chạy.

---

## 6. Locations — Quản lý Điểm giao hàng

> Prefix: `/api/v1/locations`

---

### `GET /api/v1/locations/demand`
Lấy tất cả điểm giao hàng (chưa được phân công).

**Response** `200`
```json
[
  {
    "id": "loc-f1e2d3c4",
    "name": "Siêu thị BigC Q7",
    "address": "123 Nguyễn Thị Thập, Q7, TP.HCM",
    "coordinates": { "lat": 10.7365, "lng": 106.7003 },
    "demand_kg": 240,
    "priority": 1,
    "phone": "028-1234567",
    "time_window_start": "08:00:00",
    "time_window_end": "12:00:00",
    "service_time_mins": 15,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### `POST /api/v1/locations`
Tạo điểm giao hàng mới.

**Request Body**
```json
{
  "name": "Siêu thị BigC Q7",
  "address": "123 Nguyễn Thị Thập",
  "coordinates": { "lat": 10.7365, "lng": 106.7003 },
  "demand_kg": 240,
  "priority": 1,
  "phone": "028-1234567",
  "time_window_start": "08:00:00",
  "time_window_end": "12:00:00",
  "service_time_mins": 15
}
```

---

### `GET /api/v1/locations/{location_id}`
Chi tiết 1 điểm giao.

---

### `PUT /api/v1/locations/{location_id}`
Cập nhật điểm giao.

---

### `DELETE /api/v1/locations/{location_id}`
Xoá điểm giao.

> ⚠️ Không thể xoá location đang được dùng trong route.

---

### `POST /api/v1/locations/upload-manifest`
Upload hàng loạt điểm giao từ file CSV/Excel.

**Request** `multipart/form-data`

| Field | Type |
|---|---|
| `file` | `.csv`, `.xlsx`, `.xls` |

**Cột file CSV/Excel được nhận diện:**

| Cột | Tên có thể dùng |
|---|---|
| ID | `id`, `location_id`, `stop_id` |
| Tên | `name`, `location_name`, `customer_name` |
| Địa chỉ | `address`, `address_string` |
| Vĩ độ | `latitude`, `lat` |
| Kinh độ | `longitude`, `lng`, `lon` |
| Khối lượng | `demand`, `demand_kg`, `quantity` |
| Ưu tiên | `priority` |
| SĐT | `phone` |
| TG dịch vụ | `service_time`, `service_time_mins` |

**Response** `200`
```json
{
  "success": true,
  "message": "Manifest processed",
  "uploaded_rows": 50,
  "created_locations": 48,
  "skipped_existing": 2
}
```

---

## 7. Optimize — Tối ưu hoá lộ trình

> Prefix: `/api/v1/optimize`

---

### `POST /api/v1/optimize/run`
Kích hoạt bộ giải VRP (bất đồng bộ).

**Request Body**
```json
{
  "project_id": "vrp-2024-001",
  "solver_algorithm": "nearest_neighbor",
  "objective": "minimize_distance",
  "vehicles": ["veh-a1b2c3d4", "veh-e5f6g7h8"],
  "locations": ["loc-f1e2d3c4", "loc-a2b3c4d5"],
  "constraints": {
    "avoid_tolls": false,
    "strict_time_windows": true
  }
}
```

| Field | Type | Bắt buộc | Ghi chú |
|---|---|---|---|
| `project_id` | string | ✅ | |
| `solver_algorithm` | enum | ❌ | Default `nearest_neighbor` |
| `objective` | enum | ❌ | Default `minimize_distance` |
| `vehicles` | string[] | ✅ | ≥ 1 vehicle id |
| `locations` | string[] | ✅ | ≥ 1 location id |
| `constraints` | dict | ❌ | Tuỳ ý |

**Response** `202`
```json
{
  "job_id": "job-8f72a1b3",
  "status": "calculating",
  "estimated_time_seconds": 12.4
}
```

---

### `GET /api/v1/optimize/jobs`
Danh sách tất cả jobs (mới nhất trước).

---

### `GET /api/v1/optimize/job/{job_id}`
Trạng thái chi tiết 1 job.

**Response khi `status = "calculating"`**
```json
{
  "job_id": "job-8f72a1b3",
  "status": "calculating",
  ...
}
```

**Response khi `status = "completed"`**
```json
{
  "job_id": "job-8f72a1b3",
  "status": "completed",
  "result": {
    "total_distance_km": 145.2,
    "total_duration_mins": 312.5,
    "routes": [
      {
        "route_id": "route-job-8f72a1b3-1",
        "vehicle_id": "veh-a1b2c3d4",
        "stop_count": 8,
        "load_kg": 1200,
        "utilization_pct": 48.0,
        "distance_km": 72.6,
        "duration_mins": 156.2
      }
    ]
  }
}
```

---

### `GET /api/v1/optimize/job/{job_id}/result`
Lấy kết quả đầy đủ (chỉ khi `completed`).

**Response** `409` nếu job chưa xong.

---

### `POST /api/v1/optimize/job/{job_id}/cancel`
Huỷ job đang tính.

**Response** `409` nếu job đã `completed` hoặc đã `cancelled`.

---

## 8. Routes — Quản lý Lộ trình

> Prefix: `/api/v1/routes`

---

### `GET /api/v1/routes`
Danh sách tất cả routes (tự động materialize jobs đang calculating).

**Response** `200` — `RouteSummary[]`
```json
[
  {
    "id": "route-job-8f72a1b3-1",
    "vehicle_id": "veh-a1b2c3d4",
    "depot_id": "depot-hanoi",
    "job_id": "job-8f72a1b3",
    "status": "planned",
    "total_distance_km": 72.6,
    "total_duration_mins": 156.2,
    "total_cost": 105.27,
    "load_kg": 1200,
    "utilization_pct": 48.0,
    "stop_count": 8
  }
]
```

---

### `GET /api/v1/routes/active`
Danh sách xe đang chạy (có tracking realtime).

**Response** `200`
```json
[
  {
    "route_id": "route-job-8f72a1b3-1",
    "vehicle_id": "veh-a1b2c3d4",
    "driver_name": "Nguyễn Văn A",
    "tracking_status": "on_time",
    "progress_percentage": 62.5,
    "current_coordinates": { "lat": 10.762, "lng": 106.701 },
    "next_stop": {
      "id": "stop-xxx",
      "location_id": "loc-abc",
      "location_name": "Siêu thị BigC Q7",
      "sequence_index": 5,
      "status": "pending"
    },
    "delay_mins": 0,
    "updated_at": "2024-01-01T10:30:00Z"
  }
]
```

---

### `GET /api/v1/routes/{route_id}`
Chi tiết route kèm toàn bộ stops theo thứ tự.

**Response** `200` — `RouteDetail`

---

### `GET /api/v1/routes/{route_id}/manifest`
Tờ lệnh vận chuyển (danh sách điểm dừng cho tài xế).

```json
{
  "route_id": "route-...",
  "vehicle_id": "veh-...",
  "driver_name": "Nguyễn Văn A",
  "status": "dispatched",
  "stops": [
    {
      "stop_id": "stop-xxx",
      "location_id": "loc-abc",
      "name": "Siêu thị BigC Q7",
      "address": "123 Nguyễn Thị Thập",
      "sequence": 1,
      "status": "pending"
    }
  ]
}
```

---

### `POST /api/v1/routes/{route_id}/dispatch`
Điều phối route cho tài xế.

- Chỉ route có `status = "planned"` mới dispatch được.
- Tạo `ActiveRoute` record → bắt đầu tracking.
- Route chuyển sang `status = "dispatched"`.

**Response** `200`
```json
{
  "success": true,
  "route_id": "route-...",
  "status": "dispatched"
}
```

---

### `POST /api/v1/routes/{route_id}/complete`
Đánh dấu route hoàn thành.

- Xoá `ActiveRoute` (dừng tracking).
- Tất cả stops `pending` → `completed`.

---

### `POST /api/v1/routes/{route_id}/status`
Cập nhật status thủ công.

**Request Body**
```json
{
  "status": "cancelled",
  "note": "Xe hỏng, huỷ lộ trình"
}
```

---

### `POST /api/v1/routes/{route_id}/adjust`
Chỉnh sửa thủ công (kéo thả stop giữa các routes).

**Request Body**
```json
{
  "stop_id": "stop-xxx",
  "source_route_id": "route-alpha",
  "target_route_id": "route-beta",
  "new_sequence_index": 3
}
```

> Backend tự re-index sequence của cả 2 routes.

---

### `DELETE /api/v1/routes/{route_id}`
Xoá route.

> ⚠️ Không thể xoá route đang `dispatched` hoặc `in_progress`.

---

### `GET /api/v1/routes/{route_id}/export?format=json|xlsx|pdf`
Xuất báo cáo route.

| Format | Content-Type |
|---|---|
| `json` | `application/json` |
| `xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| `pdf` | `application/pdf` |

---

## 9. Driver — Ứng dụng Tài xế

> Prefix: `/api/v1/driver`

---

### `GET /api/v1/driver/manifest`
Lấy toàn bộ routes đang active và stops của tài xế đang đăng nhập.

---

### `GET /api/v1/driver/routes/{route_id}/stops`
Danh sách stops của 1 route theo thứ tự.

---

### `GET /api/v1/driver/stops/{stop_id}`
Chi tiết 1 stop.

---

### `PUT /api/v1/driver/stops/{stop_id}/status`
Tài xế cập nhật trạng thái điểm dừng (giao hàng xong / thất bại / có sự cố).

**Request Body**
```json
{
  "status": "completed",
  "proof_of_delivery_url": "https://storage/pod-102.jpg",
  "notes": "Đã giao cho chú bảo vệ"
}
```

| `status` | Ý nghĩa |
|---|---|
| `arrived` | Xe đến nơi, ghi nhận `actual_arrived_at` |
| `completed` | Giao thành công, ghi nhận `actual_completed_at` |
| `failed` | Giao thất bại |
| `skipped` | Bỏ qua điểm này |

> **Tự động:** Backend tính lại `progress_percentage` và `next_stop_id` trên `ActiveRoute`. Khi tất cả stops xong → route tự chuyển `completed`.

---

## 10. Metrics — Thống kê

> Prefix: `/api/v1/metrics`

---

### `GET /api/v1/metrics/dashboard`
KPIs tổng quan hệ thống.

**Response** `200`
```json
{
  "total_active_routes": 12,
  "total_vehicles": 25,
  "vehicles_in_use": 12,
  "vehicle_utilization_pct": 48.0,
  "total_distance_km": 14250.5,
  "cost_savings_usd": 1852.56,
  "efficiency_trend": [46, 48, 47, 49]
}
```

---

### `GET /api/v1/metrics/routes/{route_id}`
Metrics chi tiết cho 1 route.

**Response** `200`
```json
{
  "route_id": "route-...",
  "status": "in_progress",
  "total_distance_km": 72.6,
  "total_duration_mins": 156.2,
  "total_cost": 105.27,
  "stop_count": 8,
  "completed_stops": 5,
  "completion_pct": 62.5
}
```

---

## 11. Enums

### `UserRole`
| Value | Mô tả |
|---|---|
| `admin` | Quản trị viên |
| `dispatcher` | Điều phối viên |
| `driver` | Tài xế |

### `VehicleStatus`
| Value | Mô tả |
|---|---|
| `available` | Sẵn sàng |
| `in_use` | Đang sử dụng |
| `maintenance` | Bảo trì |
| `retired` | Ngừng hoạt động |

### `SolverAlgorithm`
| Value | Mô tả |
|---|---|
| `nearest_neighbor` | Thuật toán láng giềng gần nhất + 2-opt, nhanh |
| `genetic_algorithm` | Thuật toán di truyền, chất lượng cao hơn |
| `clarke_wright_savings` | Tiết kiệm Clarke-Wright (chưa implement) |

### `Objective`
| Value | Mô tả |
|---|---|
| `minimize_distance` | Tối thiểu tổng quãng đường |
| `minimize_time` | Tối thiểu thời gian |
| `minimize_cost` | Tối thiểu chi phí |

### `RouteStatus`
| Value | Mô tả |
|---|---|
| `planned` | Đã lên kế hoạch |
| `dispatched` | Đã điều phối |
| `in_progress` | Đang thực hiện |
| `completed` | Hoàn thành |
| `cancelled` | Đã huỷ |

### `StopStatus`
| Value | Mô tả |
|---|---|
| `pending` | Chờ xử lý |
| `en_route` | Xe đang đến |
| `arrived` | Xe đã đến |
| `completed` | Giao thành công |
| `failed` | Giao thất bại |
| `skipped` | Bỏ qua |

### `TrackingStatus`
| Value | Mô tả |
|---|---|
| `on_time` | Đúng giờ |
| `delayed` | Trễ giờ |
| `off_route` | Đi lạc đường |

---

## 12. Luồng nghiệp vụ đầy đủ

### Bước 0 — Xác thực
```
POST /api/v1/auth/register   → Tạo tài khoản (lần đầu)
POST /api/v1/auth/login      → Đăng nhập → lấy access_token
  Dùng token cho tất cả request sau:
  Header: Authorization: Bearer <access_token>
```

### Bước 1 — Setup hạ tầng (Admin)
```
POST /api/v1/locations/depots    → Tạo kho bãi
POST /api/v1/users               → Tạo tài xế (role=driver)
POST /api/v1/fleet/vehicles      → Thêm xe (gán depot_id + driver_id)
```

### Bước 2 — Nhập đơn hàng (Dispatcher)
```
POST /api/v1/locations           → Thêm thủ công từng điểm giao
  HOẶC
POST /api/v1/locations/upload-manifest  → Upload file CSV/Excel hàng loạt
```

### Bước 3 — Tối ưu lộ trình (Dispatcher)
```
POST /api/v1/optimize/run        → Gửi yêu cầu tính toán
GET  /api/v1/optimize/job/{id}   → Poll kết quả (lặp đến khi status=completed)
GET  /api/v1/routes              → Xem routes đã tạo
```

### Bước 4 — Điều chỉnh & Dispatch (Dispatcher)
```
POST /api/v1/routes/{id}/adjust  → Kéo thả điều chỉnh nếu cần
POST /api/v1/routes/{id}/dispatch → Gửi lệnh cho tài xế
GET  /api/v1/routes/active       → Theo dõi xe đang chạy
```

### Bước 5 — Giao hàng (Driver App)
```
GET /api/v1/driver/manifest      → Xem danh sách điểm giao hôm nay
PUT /api/v1/driver/stops/{id}/status  → Báo cáo từng điểm (arrived/completed/failed)
```

### Bước 6 — Giám sát & Báo cáo
```
GET /api/v1/metrics/dashboard        → KPIs tổng quan
GET /api/v1/metrics/routes/{id}      → Chi tiết 1 route
GET /api/v1/routes/{id}/export       → Xuất báo cáo xlsx/pdf
```

---

*Tài liệu tự động tổng hợp từ OpenAPI spec. Cập nhật lần cuối: 2026-05-02.*
