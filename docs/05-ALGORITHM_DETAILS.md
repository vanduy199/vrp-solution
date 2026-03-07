# 🧬 Chi Tiết Thuật Toán VRP

## 1. Nearest Neighbor (Thuật Tham Lam)

### 1.1 Ý Tưởng

```
Bắt đầu từ Kho (Depot):
  REPEAT:
    - Từ vị trí hiện tại
    - Tìm điểm chưa ghé gần nhất
    - Di chuyển đến đó
    - Đánh dấu điểm đó là đã ghé
  UNTIL: Tất cả điểm đã ghé
  
Quay về Kho
```

### 1.2 Pseudocode

```
FUNCTION nearest_neighbor(all_points, depot):
    current = depot
    unvisited = all_points - depot
    route = [depot]
    total_distance = 0
    
    WHILE unvisited is not empty:
        nearest_point = null
        min_distance = INFINITY
        
        FOR EACH point IN unvisited:
            dist = calculate_distance(current, point)
            IF dist < min_distance:
                min_distance = dist
                nearest_point = point
        
        route.append(nearest_point)
        total_distance += min_distance
        unvisited.remove(nearest_point)
        current = nearest_point
    
    # Quay về kho
    route.append(depot)
    total_distance += calculate_distance(current, depot)
    
    RETURN Route(path=route, distance=total_distance)
END FUNCTION
```

### 1.3 Python Implementation

```python
import math

class NearestNeighbor:
    def __init__(self, distance_function='euclidean'):
        self.distance_func = distance_function
    
    def solve(self, points, depot):
        """
        Args:
            points: List[Point] - Tất cả điểm (bao gồm depot)
            depot: Point - Điểm xuất phát
        
        Returns:
            Route - Lộ trình tối ưu
        """
        current = depot
        unvisited = [p for p in points if p.id != depot.id]
        route_path = [depot]
        total_distance = 0.0
        
        while unvisited:
            # Tìm điểm gần nhất
            nearest = self._find_nearest(current, unvisited)
            
            # Cập nhật
            dist = self._calculate_distance(current, nearest)
            route_path.append(nearest)
            total_distance += dist
            unvisited.remove(nearest)
            current = nearest
        
        # Quay về depot
        final_dist = self._calculate_distance(current, depot)
        route_path.append(depot)
        total_distance += final_dist
        
        return Route(
            vehicle_id="V1",
            path=route_path,
            distance=total_distance,
            algorithm="nearest_neighbor"
        )
    
    def _find_nearest(self, current, candidates):
        """Tìm điểm gần nhất"""
        nearest = None
        min_dist = float('inf')
        
        for point in candidates:
            dist = self._calculate_distance(current, point)
            if dist < min_dist:
                min_dist = dist
                nearest = point
        
        return nearest
    
    def _calculate_distance(self, p1, p2):
        """Tính khoảng cách Euclid"""
        return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
```

### 1.4 Ví Dụ Thực Thi

```
Input:
  Depot: (0, 0)
  Points: C1(3,4), C2(1,5), C3(8,0), C4(7,9)

Bước 1: Current = (0,0), Unvisited = [C1, C2, C3, C4]
  Distance to C1 = √(3² + 4²) = 5.0
  Distance to C2 = √(1² + 5²) = √26 ≈ 5.1
  Distance to C3 = √(8² + 0²) = 8.0
  Distance to C4 = √(7² + 9²) = √130 ≈ 11.4
  → Chọn C1, Total = 5.0

Bước 2: Current = (3,4), Unvisited = [C2, C3, C4]
  Distance to C2 = √((1-3)² + (5-4)²) = √5 ≈ 2.2
  Distance to C3 = √((8-3)² + (0-4)²) = √41 ≈ 6.4
  Distance to C4 = √((7-3)² + (9-4)²) = √41 ≈ 6.4
  → Chọn C2, Total = 5.0 + 2.2 = 7.2

Bước 3: Current = (1,5), Unvisited = [C3, C4]
  Distance to C3 = √((8-1)² + (0-5)²) = √74 ≈ 8.6
  Distance to C4 = √((7-1)² + (9-5)²) = √52 ≈ 7.2
  → Chọn C4, Total = 7.2 + 7.2 = 14.4

Bước 4: Current = (7,9), Unvisited = [C3]
  → Chọn C3, Total = 14.4 + √((8-7)² + (0-9)²) = 14.4 + √82 ≈ 14.4 + 9.1 = 23.5

Bước 5: Quay về Depot
  Distance = √64 + 0 = 8.0
  Total = 23.5 + 8.0 = 31.5

Route: Depot → C1 → C2 → C4 → C3 → Depot
Distance: 31.5
```

### 1.5 Độ Phức Tạp

```
Time Complexity:  O(n²)
  - Ngoài vòng: n lần (mỗi điểm 1 lần)
  - Trong vòng: n-i lần tìm điểm gần nhất
  - Total: n + (n-1) + (n-2) + ... + 1 = n(n+1)/2 = O(n²)

Space Complexity: O(n)
  - Lưu route_path: O(n)
  - Lưu unvisited list: O(n)

Chất lượng: 70-80% so với tối ưu (tùy vào dữ liệu)
```

### 1.6 Ưu & Nhược Điểm

```
✓ Ưu:
  - Dễ hiểu & triển khai
  - Nhanh (O(n²))
  - Cho lời giải hợp lý
  - Thích hợp cho bài toán nhỏ

✗ Nhược:
  - Dễ bị "local optimum" (cực tiểu cục bộ)
  - Không tìm được lời giải tối ưu global
  - "Greedy" decision có thể sai ở bước đầu
```

---

## 2. Genetic Algorithm (Thuật Tiến Hóa)

### 2.1 Khái Niệm Cơ Bản

**Giả sử:**
- **Population** = Tập hợp các lộ trình (solutions)
- **Individual** = Một lộ trình (solution)
- **Gene** = Một điểm giao hàng trong lộ trình
- **Chromosome** = Toàn bộ lộ trình
- **Fitness** = Độ tốt (= 1/khoảng_cách)
- **Generation** = Thế hệ

**Quy trình:**
```
Tạo quần thể ban đầu (ngẫu nhiên)
  ↓
REPEAT:
  1. Đánh giá fitness (tính khoảng cách) → Cá thể tốt
  2. Selection (chọn những cá thể tốt)
  3. Crossover (kết hợp cha mẹ → con đẻ)
  4. Mutation (thay đổi ngẫu nhiên 10-20%)
  5. Tạo quần thể thế hệ mới
UNTIL: Đủ số thế hệ hoặc không cải tiến
```

### 2.2 Pseudocode Đầy Đủ

```
FUNCTION genetic_algorithm(points, population_size=100, generations=500, mutation_rate=0.1):
    
    # Bước 1: Tạo quần thể ban đầu
    population = create_initial_population(points, population_size)
    best_solution = null
    best_fitness = 0
    
    # Bước 2: Lặp các thế hệ
    FOR generation = 1 TO generations:
        
        # 2a. Tính fitness cho mỗi cá thể
        fitness_scores = []
        FOR EACH individual IN population:
            distance = calculate_route_distance(individual)
            fitness = 1 / distance  # Fitness = ngược với khoảng cách
            fitness_scores.append(fitness)
            
            IF fitness > best_fitness:
                best_fitness = fitness
                best_solution = individual
        
        # 2b. Selection - Chọn những cá thể tốt
        parents = selection(population, fitness_scores, num_select=population_size/2)
        
        # 2c. Crossover - Kết hợp cha mẹ
        offspring = []
        WHILE offspring.length < population_size:
            parent1 = random_select(parents)
            parent2 = random_select(parents)
            child = crossover(parent1, parent2)
            offspring.append(child)
        
        # 2d. Mutation - Thay đổi ngẫu nhiên
        FOR EACH child IN offspring:
            IF random() < mutation_rate:
                child = mutate(child)
        
        # 2e. Thay thế quần thể
        population = offspring
        
        # Report tiến độ
        IF generation % 50 == 0:
            PRINT f"Gen {generation}: Best fitness = {best_fitness}"
    
    RETURN best_solution
END FUNCTION
```

### 2.3 Chi Tiết Các Phép Toán

#### A. Selection (Chọn Lọc)

**Tournament Selection:**
```python
def tournament_selection(population, fitness_scores, tournament_size=5):
    """
    Chọn ngẫu nhiên 5 cá thể, lấy cá thể có fitness cao nhất
    """
    selected = []
    for _ in range(len(population) // 2):
        tournament_indices = random.sample(range(len(population)), tournament_size)
        best_index = max(tournament_indices, key=lambda i: fitness_scores[i])
        selected.append(population[best_index])
    return selected
```

#### B. Crossover (Kết Hợp)

**Order Crossover (OX):**
```python
def crossover_ox(parent1, parent2):
    """
    Kết hợp hai lộ trình cha mẹ để tạo con đẻ
    
    Parent1: [Depot, C1, C2, C3, C4, C5, Depot]
    Parent2: [Depot, C5, C3, C1, C2, C4, Depot]
    
    Bước:
    1. Chọn ngẫu nhiên 2 điểm cắt
    2. Copy đoạn giữa từ Parent1 (bảo toàn thứ tự)
    3. Lấp chỗ trống từ Parent2 (giữ thứ tự)
    """
    size = len(parent1)
    cut1, cut2 = sorted(random.sample(range(1, size-1), 2))
    
    # Copy đoạn giữa từ parent1
    child = [None] * size
    child[cut1:cut2] = parent1[cut1:cut2]
    
    # Lấp chỗ trống từ parent2, giữ thứ tự
    remaining = [p for p in parent2 if p not in child]
    idx = 0
    for i in range(size):
        if child[i] is None:
            child[i] = remaining[idx]
            idx += 1
    
    return child
```

#### C. Mutation (Đột Biến)

**Swap Mutation:**
```python
def mutate(route, mutation_rate=0.1):
    """
    10% xác suất hoán đổi 2 điểm ngẫu nhiên
    """
    if random.random() < mutation_rate:
        idx1, idx2 = random.sample(range(1, len(route)-1), 2)
        route[idx1], route[idx2] = route[idx2], route[idx1]
    return route
```

### 2.4 Python Implementation Hoàn Chỉnh

```python
import random
import math
from typing import List

class GeneticAlgorithm:
    def __init__(self, points, depot, population_size=100, generations=500, 
                 mutation_rate=0.1, crossover_rate=0.8):
        self.points = points
        self.depot = depot
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.best_fitness_history = []
        self.best_route_history = []
    
    def solve(self):
        """Giải quyết VRP bằng GA"""
        # 1. Tạo quần thể ban đầu
        population = self._create_initial_population()
        best_route = None
        best_distance = float('inf')
        
        # 2. Lặp các thế hệ
        for generation in range(self.generations):
            # Tính fitness
            distances = [self._calculate_route_distance(route) for route in population]
            fitness_scores = [1 / d for d in distances]
            
            # Cập nhật best
            min_dist_idx = distances.index(min(distances))
            if distances[min_dist_idx] < best_distance:
                best_distance = distances[min_dist_idx]
                best_route = population[min_dist_idx].copy()
            
            # Lưu lịch sử
            self.best_fitness_history.append(best_distance)
            self.best_route_history.append(best_route.copy())
            
            # Selection
            parents = self._selection(population, fitness_scores)
            
            # Crossover + Mutation
            offspring = []
            for _ in range(len(population)):
                if random.random() < self.crossover_rate:
                    parent1, parent2 = random.sample(parents, 2)
                    child = self._crossover_ox(parent1, parent2)
                else:
                    child = random.choice(parents).copy()
                
                # Mutation
                child = self._swap_mutation(child)
                offspring.append(child)
            
            population = offspring
            
            # Log tiến độ
            if (generation + 1) % 100 == 0:
                print(f"Generation {generation+1}: Best distance = {best_distance:.2f}")
        
        return Route(
            path=best_route,
            distance=best_distance,
            algorithm="genetic_algorithm"
        )
    
    def _create_initial_population(self):
        """Tạo quần thể ban đầu (ngẫu nhiên)"""
        population = []
        for _ in range(self.population_size):
            # Lấy tất cả điểm trừ depot
            route_points = [p for p in self.points if p.id != self.depot.id]
            random.shuffle(route_points)
            
            # Thêm depot ở đầu và cuối
            route = [self.depot] + route_points + [self.depot]
            population.append(route)
        return population
    
    def _calculate_route_distance(self, route):
        """Tính tổng khoảng cách"""
        total = 0.0
        for i in range(len(route) - 1):
            dist = self._distance(route[i], route[i+1])
            total += dist
        return total
    
    def _distance(self, p1, p2):
        """Khoảng cách Euclid"""
        return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
    
    def _selection(self, population, fitness_scores):
        """Tournament selection"""
        selected = []
        tournament_size = 3
        for _ in range(len(population)):
            tournament_idx = random.sample(range(len(population)), tournament_size)
            best_idx = max(tournament_idx, key=lambda i: fitness_scores[i])
            selected.append(population[best_idx].copy())
        return selected
    
    def _crossover_ox(self, parent1, parent2):
        """Order Crossover"""
        size = len(parent1)
        cut1, cut2 = sorted(random.sample(range(1, size-1), 2))
        
        child = [None] * size
        child[cut1:cut2] = parent1[cut1:cut2]
        
        remaining = [p for p in parent2 if p not in child]
        idx = 0
        for i in range(size):
            if child[i] is None:
                child[i] = remaining[idx]
                idx += 1
        
        return child
    
    def _swap_mutation(self, route):
        """Swap mutation"""
        if random.random() < self.mutation_rate:
            idx1, idx2 = random.sample(range(1, len(route)-1), 2)
            route[idx1], route[idx2] = route[idx2], route[idx1]
        return route
```

### 2.5 Độ Phức Tạp

```
Time Complexity:
  - Mỗi thế hệ: O(population_size² × n)
    - Tính fitness: O(population × n)
    - Selection: O(population²) (tournament)
    - Crossover: O(population × n)
  - Tổng: O(generations × population × n²)
  
  Ví dụ: 500 thế hệ × 100 quần thể × 100 điểm = 500M phép tính
         → ~5 giây trên máy hiện đại

Space Complexity: O(population × n)
  - Lưu toàn bộ quần thể

Chất lượng: 85-95% so với tối ưu
```

### 2.6 So Sánh GA vs Nearest Neighbor

| Tiêu Chí | Nearest Neighbor | Genetic Algorithm |
|----------|------------------|-------------------|
| **Thời gian** | O(n²) = 0.05s | O(gen×pop×n²) = 5s |
| **Chất lượng** | 70-80% | 85-95% |
| **Dễ hiểu** | Rất dễ | Phức tạp |
| **Tùy biến** | Khó | Dễ (cấu hình GA) |
| **Phù hợp** | Bài toán nhỏ | Bài toán lớn |

---

## 3. Khoảng Cách - Các Cách Tính

### 3.1 Euclidean Distance (Đơn giản, tính toán)

```python
def euclidean_distance(p1, p2):
    """
    Tính đường thẳng giữa 2 điểm
    d = √((x2-x1)² + (y2-y1)²)
    """
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
```

**Ưu:** Nhanh, không cần API  
**Nhược:** Không chính xác (không tính địa hình, đường giao thông)

### 3.2 Haversine Distance (Thực tế nhất)

```python
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách thực tế trên Trái Đất (km)
    Công thức Haversine (chuẩn xác 0.5%)
    """
    R = 6371  # Bán kính Trái Đất (km)
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c
```

**Ưu:** Chính xác với GPS  
**Nhược:** Vẫn không tính đường cụ thể

### 3.3 Google Maps Distance (Chính xác nhất)

```python
import googlemaps

def google_maps_distance(origin, destination, api_key):
    """
    Sử dụng Google Maps API để lấy khoảng cách/thời gian thực tế
    """
    gmaps = googlemaps.Client(key=api_key)
    
    result = gmaps.distance_matrix(
        origins=f"{origin.lat},{origin.lon}",
        destinations=f"{destination.lat},{destination.lon}",
        mode="driving",
        units="metric"
    )
    
    if result['rows'][0]['elements'][0]['status'] == 'OK':
        distance_m = result['rows'][0]['elements'][0]['distance']['value']
        duration_s = result['rows'][0]['elements'][0]['duration']['value']
        return distance_m / 1000, duration_s / 60  # km, minutes
    else:
        return None, None
```

**Ưu:** Chính xác 100% theo đường thực tế  
**Nhược:** Chậm (API call), tốn chi phí, rate limit

---

## 4. Hội Tụ & Performance Tuning

### 4.1 Hội Tụ GA

```
Iteration:   1    50    100   200   300   400   500
Distance:   500   280   220   180   150   145   142
             ↓    ↓     ↓     ↓     ↓     ✓     ✓ (plateau)

Hội tụ xảy ra khi:
- Fitness không cải thiện trong 10-20 thế hệ
- Tất cả cá thể trở nên giống nhau
→ Có thể dừng sớm để tiết kiệm thời gian
```

### 4.2 Cấu Hình Tối Ưu

```
population_size = 50-100
  → Quân thể lớn = tìm toàn diện hơn, chậm hơn
  → Quần thể nhỏ = nhanh, nhưng bỏ sót

generations = 300-500
  → 300 thế hệ thường đủ hội tụ
  → 500+ chỉ cần nếu muốn tối ưu tuyệt đối

mutation_rate = 0.05-0.2
  → 10% là cân bằng tốt

crossover_rate = 0.7-0.9
  → 80% là mặc định tốt
```

### 4.3 Early Stopping

```python
def solve_with_early_stopping(self, patience=20):
    """Dừng sớm nếu không cải thiện"""
    best_fitness = -float('inf')
    patience_counter = 0
    
    for generation in range(self.generations):
        # ... (tính fitness)
        
        if current_best > best_fitness:
            best_fitness = current_best
            patience_counter = 0  # Reset
        else:
            patience_counter += 1
        
        if patience_counter >= patience:
            print(f"Dừng sớm ở thế hệ {generation}")
            break
    
    return best_solution
```

---

## 5. Hybrid Approach (Kết Hợp)

```
Ý tưởng: Dùng NN để tạo quần thể ban đầu tốt → GA tinh chỉnh

1. Tạo 100 lộ trình bằng NN (chọn depot ngẫu nhiên)
   → Tất cả đều ≈ 150km (chất lượng ổn định)

2. Chạy GA với quần thể này
   → Bắt đầu từ base tốt → hội tụ nhanh hơn
   → 200 thế hệ là đủ (thay vì 500)

Lợi ích: Kết hợp tốc độ NN + chất lượng GA
```

---

## 6. Testing & Validation

```python
def validate_ga_solution(route, points):
    """
    Kiểm tra lộ trình có hợp lệ không
    """
    # 1. Tất cả điểm phải được ghé
    route_points = set([p.id for p in route[1:-1]])  # Bỏ depot
    all_points = set([p.id for p in points if p.id != depot.id])
    assert route_points == all_points, "Không ghé hết điểm"
    
    # 2. Không ghé điểm nào 2 lần
    assert len(route_points) == len(route) - 2, "Ghé điểm lặp lại"
    
    # 3. Bắt đầu và kết thúc tại depot
    assert route[0].id == depot.id, "Không bắt đầu từ depot"
    assert route[-1].id == depot.id, "Không kết thúc tại depot"
    
    print("✓ Lộ trình hợp lệ")
    return True
```

