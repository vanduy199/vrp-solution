#Yêu Cầu Chức Năng & Kỹ Thuật

## 1. Yêu Cầu Chức Năng (Functional Requirements)

### 1.1 Quản Lý Điểm Giao Hàng

```
FR-1: Thêm/Xóa/Sửa điểm giao hàng
  Input:  {id, name, latitude, longitude, demand}
  Output: {status, message}

FR-2: Thêm điểm lấy hàng
  Input: {id, name, latatude, longitude}
  Output: {status, message}
  
FR-2: Lấy danh sách tất cả điểm
  Input:  (get all)
  Output: List<Point>
  
FR-3: Tìm kiếm điểm theo ID/tên
  Input:  {search_key}
  Output: List<Point>
```

### 1.2 Quản Lý Phương Tiện

```
FR-4: Thêm xe mới
  Input:  {vehicle_id, capacity, cost_per_km}
  Output: {status, vehicle_info}
  
FR-5: Lấy thông tin xe
  Input:  {vehicle_id}
  Output: Vehicle object
```

### 1.3 Tính Toán Lộ Trình (Core)

```
FR-6: Tính lộ trình tối ưu (Nearest Neighbor)
  Input:  {points: List[Point], vehicle: Vehicle}
  Output: Route {
    path: [P1 → P2 → P3 ... → Depot],
    distance: 123.45 km,
    cost: 5000 VND,
    time_estimate: 2.5 hours
  }
  
FR-7: Tính lộ trình tối ưu (Genetic Algorithm)
  Input:  {points, vehicles, population_size=100, generations=500}
  Output: List<Route>
  
FR-8: So sánh nhiều thuật toán
  Input:  {points, vehicles}
  Output: {
    nearest_neighbor: Route,
    genetic: Route,
    savings: {
      distance: -15%,
      cost: -15%
    }
  }
```

### 1.4 Đồ Thị & Trực Quan Hóa

```
FR-9: Vẽ bản đồ tuyến đường
  Input:  {route, map_style}
  Output: HTML map visualization
  
FR-10: Xuất báo cáo
  Input:  {routes, format: [pdf|csv|json]}
  Output: file
```

---

## 2. Yêu Cầu Kỹ Thuật (Non-Functional Requirements)

### 2.1 Hiệu Năng

```
NFR-1: Thời gian tính toán
  - Nearest Neighbor: < 100ms cho 100 điểm
  - Genetic Algorithm: < 5s cho 100 điểm
  - Google Maps API: < 2s cho 50 điểm
  
NFR-2: Khả năng mở rộng
  - Xử lý tối thiểu 1000 điểm giao hàng
  - Hỗ trợ tối thiểu 100 chiếc xe
```

### 2.2 Bảo Mật

```
NFR-3: Authentication
  - API endpoint cần token (JWT)
  - Rate limiting: 100 request/phút/user
  
NFR-4: Dữ liệu nhạy cảm
  - Mã hóa tọa độ khách hàng
  - Logging các thao tác quan trọng
```

### 2.3 Độ Tin Cậy

```
NFR-5: Error Handling
  - Xử lý lỗi gracefully
  - Return meaningful error messages
  
NFR-6: Caching
  - Cache Google Maps API responses
  - Cache kết quả lộ trình thường xuyên
```

### 2.4 Usability

```
NFR-7: API Design
  - RESTful endpoints
  - Clear documentation (Swagger)
  
NFR-8: Frontend
  - Responsive design
  - Real-time visualization
```

---

## 3. Ràng Buộc & Hạn Chế

### 3.1 Ràng Buộc Xe (Vehicle Constraints)

```
C-1: Dung tích xe (CVRP)
  Σ(demand của các điểm) ≤ vehicle.capacity
  
C-2: Khung giờ làm việc
  departure_time ≤ service_start ≤ return_time
  
C-3: Thời gian phục vụ
  total_time = driving_time + service_time ≤ max_shift
```

### 3.2 Ràng Buộc Điểm Giao Hàng

```
C-4: Mỗi điểm phải được phục vụ đúng một lần
C-5: Tất cả xe bắt đầu/kết thúc tại Kho (Depot)
C-6: Địa điểm có thể có yêu cầu đặc biệt (ưu tiên, fragile, ...)
```

### 3.3 Ràng Buộc Đầu Vào

```
C-7: Tọa độ GPS hợp lệ
  -90 ≤ latitude ≤ 90
  -180 ≤ longitude ≤ 180
  
C-8: Demand > 0
C-9: Cost per km > 0
```

---

## 4. Trường Hợp Sử Dụng (Use Cases)

### UC-1: Giao hàng hàng ngày
```
Actor: Nhân viên logistics
Precondition: Biết danh sách khách hàng + tọa độ
Flow:
  1. Upload danh sách khách hàng
  2. Chọn thuật toán tối ưu (Nearest Neighbor / GA)
  3. System tính lộ trình
  4. Hiển thị trên bản đồ
  5. Xuất PDF hướng dẫn cho lái xe
Postcondition: Lái xe nhận được lộ trình tối ưu
```

### UC-2: Phân tích chi phí
```
Actor: Quản lý
Precondition: Đã có lộ trình
Flow:
  1. Xem báo cáo chi phí theo ngày/tháng
  2. So sánh lộ trình cũ vs tối ưu
  3. Nhìn tiết kiệm được (%)
Postcondition: Đánh giá hiệu quả hệ thống
```

### UC-3: Tối ưu hóa động
```
Actor: System
Precondition: Có order mới đến
Flow:
  1. Thêm điểm mới vào danh sách
  2. Tính toán lại lộ trình (nếu cần)
  3. Thông báo cho xe gần nhất
PostCondition: Giao hàng không bị delay
```

---

## 5. Success Criteria (Tiêu Chí Thành Công)

Dự án được coi là **thành công** nếu:

```
✓ Hệ thống tính toán lộ trình chính xác
✓ Tối ưu hóa để giảm khoảng cách ≥ 30% so với random
✓ API hoạt động ổn định (> 99% uptime)
✓ UI/UX thân thiện, dễ sử dụng
✓ Xử lý tối thiểu 100 điểm giao hàng
✓ Documentation đầy đủ & rõ ràng
✓ Unit tests coverage > 80%
✓ Demo thành công trước khán giả
```

