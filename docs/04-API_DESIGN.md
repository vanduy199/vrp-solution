# API Design - REST Endpoints

## 1. Base Configuration

```
Base URL: http://localhost:8000/api
Auth: Bearer Token (JWT)
Content-Type: application/json
Rate Limit: 100 requests/minute
```

---

## 2. Point (Điểm Giao Hàng) Endpoints

### 2.1 CREATE - Thêm một điểm

```http
POST /api/points
Authorization: Bearer {token}
Content-Type: application/json

Request:
{
  "id": "C001",
  "name": "Hà Nội Plaza",
  "latitude": 21.0285,
  "longitude": 105.8542,
  "demand": 50,               # kg
  "service_time": 15,         # minutes
  "priority": 1,              # 1=highest, 5=lowest
  "phone": "0901234567",
  "address": "107 Nguyễn Hữu Cảnh, Hà Nội"
}

Response (201):
{
  "success": true,
  "data": {
    "id": "C001",
    "created_at": "2024-03-06T10:30:00Z",
    "message": "Point created successfully"
  }
}

Error (400):
{
  "success": false,
  "error": "INVALID_COORDINATES",
  "message": "Latitude must be between -90 and 90"
}
```

### 2.2 BATCH CREATE - Thêm nhiều điểm cùng lúc

```http
POST /api/points/batch
Authorization: Bearer {token}

Request:
{
  "points": [
    {"id": "C001", "name": "...", "latitude": 21.0285, "longitude": 105.8542, ...},
    {"id": "C002", "name": "...", ...},
    ...
  ]
}

Response (201):
{
  "success": true,
  "created": 50,
  "failed": 2,
  "errors": [
    {"id": "C015", "error": "DUPLICATE_ID"}
  ]
}
```

### 2.3 READ - Lấy danh sách tất cả

```http
GET /api/points?page=1&limit=20&sort=name&filter=active

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "C001",
        "name": "Hà Nội Plaza",
        "latitude": 21.0285,
        "longitude": 105.8542,
        "demand": 50,
        "created_at": "2024-03-06T10:30:00Z"
      },
      ...
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 156,
      "pages": 8
    }
  }
}
```

### 2.4 SEARCH - Tìm kiếm điểm

```http
GET /api/points/search?q=Hà%20Nội&radius=5&lat=21.03&lon=105.85

Response (200):
{
  "success": true,
  "data": {
    "query": "Hà Nội",
    "found": 12,
    "results": [
      {"id": "C001", "name": "Hà Nội Plaza", "distance_km": 0.5},
      ...
    ]
  }
}
```

### 2.5 GET ONE - Lấy chi tiết một điểm

```http
GET /api/points/C001

Response (200):
{
  "success": true,
  "data": {
    "id": "C001",
    "name": "Hà Nội Plaza",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "demand": 50,
    "service_time": 15,
    "priority": 1,
    "phone": "0901234567",
    "address": "107 Nguyễn Hữu Cảnh, Hà Nội",
    "created_at": "2024-03-06T10:30:00Z",
    "updated_at": "2024-03-06T10:30:00Z"
  }
}
```

### 2.6 UPDATE - Sửa một điểm

```http
PUT /api/points/C001
Content-Type: application/json

Request:
{
  "name": "Hà Nội Plaza Ver 2",
  "demand": 75,
  "priority": 2
}

Response (200):
{
  "success": true,
  "data": {
    "id": "C001",
    "message": "Point updated successfully"
  }
}
```

### 2.7 DELETE - Xóa một điểm

```http
DELETE /api/points/C001

Response (200):
{
  "success": true,
  "message": "Point C001 deleted successfully"
}
```

### 2.8 BULK DELETE - Xóa nhiều điểm

```http
POST /api/points/bulk-delete

Request:
{
  "ids": ["C001", "C002", "C015"]
}

Response (200):
{
  "success": true,
  "deleted": 3,
  "message": "3 points deleted"
}
```

---

## 3. Vehicle (Phương Tiện) Endpoints

### 3.1 CREATE - Thêm xe

```http
POST /api/vehicles

Request:
{
  "vehicle_id": "V001",
  "license_plate": "29A-12345",
  "capacity": 1000,           # kg
  "cost_per_km": 5000,        # VND
  "cost_per_hour": 50000,     # VND
  "max_shift_hours": 8,
  "depot_lat": 21.0285,
  "depot_lon": 105.8542,
  "driver_name": "Nguyễn Văn A"
}

Response (201):
{
  "success": true,
  "data": {
    "vehicle_id": "V001",
    "status": "active",
    "created_at": "2024-03-06T10:30:00Z"
  }
}
```

### 3.2 LIST - Lấy danh sách xe

```http
GET /api/vehicles?status=active

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {
        "vehicle_id": "V001",
        "license_plate": "29A-12345",
        "capacity": 1000,
        "driver_name": "Nguyễn Văn A",
        "status": "active",
        "utilization": 65    # % dung tích sử dụng
      },
      ...
    ],
    "total": 8
  }
}
```

### 3.3 UPDATE - Sửa thông tin xe

```http
PUT /api/vehicles/V001

Request:
{
  "driver_name": "Phạm Văn B",
  "status": "maintenance"
}

Response (200):
{
  "success": true,
  "data": {
    "vehicle_id": "V001",
    "message": "Vehicle updated"
  }
}
```

### 3.4 DELETE - Xóa xe (hoặc/inactive)

```http
DELETE /api/vehicles/V001

Response (200):
{
  "success": true,
  "message": "Vehicle V001 marked as inactive"
}
```

---

## 4. Optimization (Tối Ưu Hóa) Endpoints - **CORE**

### 4.1 NEAREST NEIGHBOR - Greedy Algorithm

```http
POST /api/optimize/nearest-neighbor
Authorization: Bearer {token}

Request:
{
  "point_ids": ["C001", "C002", "C003", ...],  # Các điểm cần tối ưu
  "vehicle_id": "V001",                         # Xe để sử dụng
  "depot_id": "DEPOT_001",                      # Điểm xuất phát
  "use_google_maps": false                      # Dùng API hay Euclidean
}

Response (200):
{
  "success": true,
  "data": {
    "route": {
      "route_id": "ROUTE_20240306_001",
      "vehicle_id": "V001",
      "algorithm": "nearest_neighbor",
      "execution_time_ms": 45,
      
      "path": [
        {
          "order": 1,
          "point_id": "DEPOT_001",
          "name": "Kho chính",
          "arrival_time": "08:00",
          "departure_time": "08:00"
        },
        {
          "order": 2,
          "point_id": "C005",
          "name": "KH-5",
          "arrival_time": "08:15",
          "departure_time": "08:30",
          "distance_from_prev": 3.2,
          "duration_from_prev": 15
        },
        {
          "order": 3,
          "point_id": "C002",
          "arrival_time": "08:42",
          "departure_time": "08:57"
        },
        ...
        {
          "order": n,
          "point_id": "DEPOT_001",
          "arrival_time": "17:00",
          "departure_time": "17:00"
        }
      ],
      
      "statistics": {
        "total_distance": 125.6,     # km
        "total_duration": 9.0,       # hours
        "total_cost": 878000,        # VND = 125.6*5000 + 9*50000
        "points_served": 23,
        "utilization": 87.5,         # % load
        "quality_score": 75.3        # 0-100
      }
    }
  }
}

Error (400):
{
  "success": false,
  "error": "VEHICLE_OVERLOAD",
  "message": "Total demand (1200kg) exceeds vehicle capacity (1000kg)"
}
```

### 4.2 GENETIC ALGORITHM - Advanced Optimization

```http
POST /api/optimize/genetic-algorithm
Authorization: Bearer {token}

Request:
{
  "point_ids": ["C001", "C002", ...],
  "vehicle_ids": ["V001", "V002", "V003"],  # Multiple vehicles
  "depot_id": "DEPOT_001",
  
  "ga_config": {
    "population_size": 100,    # Kích thước quần thể
    "generations": 500,        # Số thế hệ
    "mutation_rate": 0.1,      # 10% đột biến
    "crossover_rate": 0.8,     # 80% kết hợp
    "elite_size": 5            # Giữ 5 lộ trình tốt nhất
  },
  
  "constraints": {
    "max_shift_hours": 8,
    "service_priority": true,
    "time_windows": true
  },
  
  "use_google_maps": true
}

Response (200):
{
  "success": true,
  "data": {
    "optimization_result": {
      "session_id": "OPT_20240306_A1B2C3D4",
      "algorithm": "genetic_algorithm",
      "execution_time_seconds": 4.67,
      
      "best_solution": {
        "routes": [
          {
            "route_id": "ROUTE_1",
            "vehicle_id": "V001",
            "path": [
              {
                "order": 1,
                "point_id": "DEPOT_001",
                "arrival_time": "08:00"
              },
              ...
            ],
            "statistics": {
              "distance": 120.5,
              "duration": 8.0,
              "cost": 900000,
              "utilization": 95
            }
          },
          {
            "route_id": "ROUTE_2",
            "vehicle_id": "V002",
            ...
          },
          {
            "route_id": "ROUTE_3",
            "vehicle_id": "V003",
            ...
          }
        ],
        
        "overall_statistics": {
          "total_distance": 312.3,     # Tổng km tất cả xe
          "total_duration": 22.5,      # Tổng giờ
          "total_cost": 2240000,       # Tổng chi phí
          "vehicles_used": 3,
          "points_served": 73,
          "unserved_points": 0
        },
        
        "quality_metrics": {
          "fitness_score": 95.7,       # Kiểm soát chất lượng
          "convergence_generation": 423, # Kthế hệ hội tụ
          "improvement_vs_initial": "42.3%"  # So với quần thể đầu
        }
      }
    }
  }
}
```

### 4.3 COMPARE ALGORITHMS - So sánh thuật toán

```http
POST /api/optimize/compare

Request:
{
  "point_ids": ["C001", "C002", ...],
  "vehicle_ids": ["V001", "V002"],
  "depot_id": "DEPOT_001"
}

Response (200):
{
  "success": true,
  "data": {
    "comparison": {
      "nearest_neighbor": {
        "execution_time": 0.05,
        "total_distance": 215.3,
        "total_cost": 1626000,
        "quality_score": 72.1
      },
      "genetic_algorithm": {
        "execution_time": 4.23,
        "total_distance": 142.5,
        "total_cost": 1062500,
        "quality_score": 94.8
      },
      "improvement": {
        "distance_saved": "33.8 km",
        "cost_saved": "563500 VND",
        "percentage": "34.6%",
        "time_cost": 4.23  # seconds để chạy GA
      },
      "recommendation": {
        "algorithm": "genetic_algorithm",
        "reason": "Cao hơn 34.6% về khoảng cách/chi phí"
      }
    }
  }
}
```

### 4.4 SAVE ROUTE - Lưu lộ trình

```http
POST /api/optimize/save-route

Request:
{
  "route_id": "ROUTE_20240306_001",
  "session_id": "OPT_20240306_A1B2C3D4",
  "notes": "Lộ trình cho ngày 06/03/2024"
}

Response (201):
{
  "success": true,
  "message": "Route saved successfully"
}
```

---

## 5. Route Management Endpoints

### 5.1 GET ROUTE DETAILS

```http
GET /api/routes/ROUTE_20240306_001

Response (200):
{
  "success": true,
  "data": {
    "route_id": "ROUTE_20240306_001",
    "vehicle_id": "V001",
    "created_at": "2024-03-06T10:15:00Z",
    "path": [...],
    "statistics": {...}
  }
}
```

### 5.2 LIST ROUTES

```http
GET /api/routes?vehicle_id=V001&date=2024-03-06&status=active

Response (200):
{
  "success": true,
  "data": {
    "items": [
      {"route_id": "ROUTE_1", "vehicle_id": "V001", ...},
      {"route_id": "ROUTE_2", "vehicle_id": "V001", ...}
    ],
    "total": 2
  }
}
```

### 5.3 DELETE ROUTE

```http
DELETE /api/routes/ROUTE_20240306_001

Response (200):
{
  "success": true,
  "message": "Route deleted"
}
```

---

## 6. Analytics & Reporting Endpoints

### 6.1 GET STATISTICS

```http
GET /api/analytics/statistics?from=2024-03-01&to=2024-03-06

Response (200):
{
  "success": true,
  "data": {
    "period": "2024-03-01 to 2024-03-06",
    "total_routes": 18,
    "total_distance": 3456.7,
    "total_cost": 24200000,
    "avg_route_distance": 192.0,
    "vehicle_utilization": 87.3,
    "cost_per_point": 45000,
    "improvement_vs_baseline": "38.5%"
  }
}
```

### 6.2 DOWNLOAD REPORT

```http
GET /api/analytics/report?format=pdf&route_id=ROUTE_20240306_001

Response (200):
[Binary PDF file]

Or:
GET /api/analytics/report?format=csv&date=2024-03-06
Response: CSV file
```

---

## 7. Map Visualization Endpoints

### 7.1 GET MAP HTML

```http
GET /api/map/ROUTE_20240306_001?style=blue&zoom=14

Response (200):
[HTML with embedded Folium map]
```

### 7.2 GET WAYPOINTS JSON

```http
GET /api/map/waypoints/ROUTE_20240306_001

Response (200):
{
  "success": true,
  "data": {
    "route_id": "ROUTE_20240306_001",
    "waypoints": [
      {"lat": 21.0285, "lon": 105.8542, "label": "Depot"},
      {"lat": 21.0341, "lon": 105.8256, "label": "C001"},
      ...
    ],
    "polyline": "encoded_polyline_string"
  }
}
```

---

## 8. Error Handling

### Standard Error Responses

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human-readable message",
  "details": {
    "field": "value",
    "reason": "reason"
  },
  "timestamp": "2024-03-06T10:30:00Z"
}
```

### Common Error Codes

| Code | Meaning | Status |
|------|---------|--------|
| `INVALID_INPUT` | Input không hợp lệ | 400 |
| `POINT_NOT_FOUND` | Không tìm thấy điểm | 404 |
| `VEHICLE_NOT_FOUND` | Không tìm thấy xe | 404 |
| `VEHICLE_OVERLOAD` | Quá tải | 400 |
| `INVALID_COORDINATES` | Tọa độ không hợp lệ | 400 |
| `AUTHENTICATION_FAILED` | Token hết hạn/sai | 401 |
| `UNAUTHORIZED` | Không có quyền | 403 |
| `INTERNAL_ERROR` | Lỗi server | 500 |

---

## 9. Request/Response Examples (Python)

```python
import requests

BASE_URL = "http://localhost:8000/api"
HEADERS = {"Authorization": "Bearer YOUR_TOKEN"}

# 1. Add points in batch
response = requests.post(
    f"{BASE_URL}/points/batch",
    json={
        "points": [
            {"id": "C001", "name": "...", "latitude": 21.0285, "longitude": 105.8542},
            {"id": "C002", "name": "...", ...},
        ]
    },
    headers=HEADERS
)

# 2. Optimize with GA
response = requests.post(
    f"{BASE_URL}/optimize/genetic-algorithm",
    json={
        "point_ids": ["C001", "C002", ...],
        "vehicle_ids": ["V001", "V002"],
        "ga_config": {"population_size": 100, "generations": 500}
    },
    headers=HEADERS
)

print(response.json())
```