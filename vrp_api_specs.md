# Tối ưu hóa VRP (Vehicle Routing Problem) - Đặc tả API Backend

Tài liệu này mô tả các API RESTful cần thiết từ backend để tích hợp liền mạch với ứng dụng frontend VRP Optimizer.

---

## 1. Quản lý Đội xe & Phương tiện (Fleet & Vehicle Management)
Cung cấp cho ứng dụng danh sách các phương tiện có sẵn, sức chứa, trạng thái hoạt động và chi phí.

### `GET /api/v1/fleet/vehicles`
- **Mô tả**: Lấy toàn bộ danh sách phương tiện có sẵn cho việc tối ưu hóa.
- **Phản hồi (Response)**: Mảng các đối tượng Vehicle (Phương tiện).
```json
[
  {
    "id": "trk-9902",
    "name": "Freightliner M2",
    "status": "available",
    "capacity_kg": 2500,
    "volume_m3": 15,
    "cost_per_km": 1.45,
    "ev": false
  }
]
```

---

## 2. Quản lý Điểm đến & Nhu cầu (Locations & Demand Points)
Các endpoint để quản lý các trạm giao hàng, khung thời gian yêu cầu và khối lượng hàng hóa.

### `GET /api/v1/locations/demand`
- **Mô tả**: Lấy danh sách các điểm giao hàng/nhiệm vụ chưa được phân công.
- **Phản hồi**: Mảng các đối tượng Location.
```json
[
  {
    "id": "loc-102",
    "name": "Metro Grocers #42",
    "address_string": "North Parkway Blvd",
    "coordinates": {"lat": 51.5074, "lng": -0.1278},
    "demand_kg": 240,
    "time_window_start": "08:00:00",
    "time_window_end": "12:00:00",
    "service_time_mins": 15
  }
]
```

---

## 3. Lõi Thuật toán Tối ưu VRP (Core VRP Optimizer Engine)
Các endpoint tính toán nặng, nơi frontend gửi lên các ràng buộc và nhận lại lộ trình đã được tính toán.

### `POST /api/v1/optimize/run`
- **Mô tả**: Kích hoạt bộ máy tối ưu hóa VRP (thường chạy bất đồng bộ).
- **Dữ liệu gửi lên (Payload)**:
```json
{
  "project_id": "vrp-2024-001",
  "solver_algorithm": "clarke_wright_savings",
  "vehicles": ["trk-9902", "van-0412"],
  "locations": ["loc-102", "loc-103", "loc-104"],
  "objective": "minimize_time",
  "constraints": {
    "avoid_tolls": true,
    "strict_time_windows": true
  }
}
```
- **Phản hồi**:
```json
{
  "job_id": "job-8f72a",
  "status": "calculating",
  "estimated_time_seconds": 12.4
}
```

### `GET /api/v1/optimize/job/{job_id}`
- **Mô tả**: Lấy trạng thái của tiến trình tối ưu hóa. 
- **Phản hồi**: Khi hoàn thành (`completed`), trả về toàn bộ lộ trình chi tiết, tổng quãng đường, tổng thời gian và thứ tự các điểm dừng cho từng xe.

---

## 4. Theo dõi Thời gian thực (Real-Time Tracking - Active Routes)
Sử dụng cho màn hình [ActiveRoutesView](file:///c:/Users/vandu/Documents/vrp-web/vrp-web/src/views/ActiveRoutesView.tsx#4-160) để hiển thị tiến độ trực tiếp.

### `GET /api/v1/routes/active`
- **Mô tả**: Lấy trạng thái trực tiếp của các xe đang di chuyển. (Nên cân nhắc dùng WebSockets thay vì gọi polling API liên tục).
- **Phản hồi**:
```json
[
  {
    "route_id": "vrp-2024-001",
    "vehicle_id": "trk-9902",
    "driver_name": "Lê Văn A",
    "status": "on-time",
    "progress_percentage": 65,
    "current_coordinates": {"lat": 51.512, "lng": -0.118},
    "next_stop": {
       "location_id": "loc-104",
       "name": "Nhà thuốc số 1",
       "eta": "14:45:00",
       "stop_index": 4,
       "total_stops": 12
    },
    "delay_mins": 0
  }
]
```

### `POST /api/v1/routes/{route_id}/dispatch`
- **Mô tả**: Đánh dấu một lộ trình bản nháp (đã được tối ưu) sang trạng thái đang hoạt động (active), phát lệnh điều phối đến tài xế.

---

## 5. Thống kê & Chỉ số Tổng quan (Analytics & Dashboard Metrics)
Tổng hợp dữ liệu cho màn hình [DashboardView](file:///c:/Users/vandu/Documents/vrp-web/vrp-web/src/views/Dashboard.tsx#4-158).

### `GET /api/v1/metrics/dashboard`
- **Mô tả**: Lấy các chỉ số hiệu suất chính (KPIs).
- **Phản hồi**:
```json
{
  "total_active_routes": 128,
  "vehicle_utilization_pct": 84.2,
  "total_distance_km": 14250,
  "cost_savings_usd": 12400,
  "efficiency_trend": [92, 94, 91, 95]
}
```

---

## 6. Quản trị Hệ thống (Admin Management - CRUD)
Các API để quản lý dữ liệu gốc (Phương tiện, Tài xế/Người dùng, Kho bãi). Hỗ trợ chuẩn `POST`, `PUT`, `DELETE`.

### `POST /api/v1/fleet/vehicles`
- **Mô tả**: Thêm phương tiện mới vào hệ thống.

### `POST /api/v1/locations/depots`
- **Mô tả**: Cấu hình các điểm Kho bãi (nơi xuất phát/kết thúc).
- **Ví dụ Payload**:
```json
{
  "name": "Kho Tổng Miền Bắc",
  "coordinates": {"lat": 21.0285, "lng": 105.8542},
  "operating_windows": ["06:00-18:00"]
}
```

### `POST /api/v1/users`
- **Mô tả**: Đăng ký người điều phối hoặc tài xế vào hệ thống.

---

## 7. Import Danh sách đơn hàng (Manifest Import)
Xử lý việc tải dữ liệu hàng loạt từ tính năng Upload.

### `POST /api/v1/locations/upload-manifest`
- **Mô tả**: Tải lên file `.xlsx` hoặc `.csv` chứa không giới hạn số lượng điểm giao hàng. Backend phải xử lý đọc file, tự động Geocode các tọa độ còn thiếu và thêm vào danh sách `locations/demand`.
- **Payload**: Gửi dữ liệu dưới dạng `multipart/form-data` chứa file upload.

---

## 8. Chỉnh sửa Lộ trình Thủ công (Manual Route Editing)
Hỗ trợ chức năng Kéo thả (Drag & Drop) tại màn hình Bản đồ (MapView).

### `POST /api/v1/routes/{route_id}/adjust`
- **Mô tả**: Chuyển đổi thủ công (ép buộc) một trạm dừng từ lộ trình xe này sang lộ trình xe khác, khóa cứng thuật toán không thay đổi điểm dừng này nữa.
- **Ví dụ Payload**:
```json
{
  "stop_id": "loc-102",
  "source_route_id": "route-alpha",
  "target_route_id": "route-beta",
  "new_sequence_index": 3
}
```

---

## 9. Ứng dụng Tài xế (Driver Mobile App)
Các API phục vụ riêng cho thiết bị của tài xế thực hiện giao hàng.

### `GET /api/v1/driver/manifest`
- **Mô tả**: Trả về danh sách các điểm dừng/đơn hàng trong ngày cho tài xế đang đăng nhập.

### `PUT /api/v1/driver/stops/{stop_id}/status`
- **Mô tả**: Cho phép tài xế báo cáo hoàn thành đơn hàng hoặc gặp sự cố. Cho phép đính kèm ảnh chụp/chữ ký làm Bằng chứng Giao hàng (Proof of Delivery).
- **Ví dụ Payload**:
```json
{
  "status": "completed", 
  "proof_of_delivery_url": "https://storage/bucket/pod-102.jpg",
  "notes": "Đã giao cho chú bảo vệ."
}
```
