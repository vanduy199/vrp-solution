"""Streamlit app — VRP Route Visualization.

Run:
    streamlit run app/dashboard/route_viz.py --server.port 8501 \
        --server.enableCORS false --server.enableXsrfProtection false
"""

import requests
import streamlit as st
import plotly.graph_objects as go

API_BASE = "http://localhost:8000"

ROUTE_COLORS = [
    "#E53935",  # red
    "#1E88E5",  # blue
    "#43A047",  # green
    "#FB8C00",  # orange
    "#8E24AA",  # purple
    "#00ACC1",  # cyan
    "#F4511E",  # deep orange
    "#6D4C41",  # brown
]


def get_auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@st.cache_data(ttl=30, show_spinner=False)
def fetch_job(job_id: str, token: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/api/v1/optimize/job/{job_id}", headers=get_auth_headers(token), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Không thể lấy thông tin job: {e}")
        return None


@st.cache_data(ttl=30, show_spinner=False)
def fetch_route(route_id: str, token: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/api/v1/routes/{route_id}", headers=get_auth_headers(token), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=30, show_spinner=False)
def fetch_location(location_id: str, token: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/api/v1/locations/{location_id}", headers=get_auth_headers(token), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def fetch_vehicle(vehicle_id: str, token: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/api/v1/fleet/vehicles/{vehicle_id}", headers=get_auth_headers(token), timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def build_figure(routes_data: list[dict], token: str) -> go.Figure:
    fig = go.Figure()

    depot_added = False
    depot_lat = depot_lng = depot_name = None

    for idx, route_meta in enumerate(routes_data):
        route_id = route_meta.get("route_id")
        vehicle_id = route_meta.get("vehicle_id")
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
        load_kg = route_meta.get("load_kg", 0)

        route_detail = fetch_route(route_id, token) if route_id else None
        stops = route_detail.get("stops", []) if route_detail else []
        stops_sorted = sorted(stops, key=lambda s: s.get("sequence", s.get("sequence_index", 0)))

        # Fetch vehicle depot coordinates (once)
        if not depot_added and vehicle_id:
            vehicle = fetch_vehicle(vehicle_id, token)
            if vehicle and vehicle.get("depot_id"):
                depot_r = requests.get(
                    f"{API_BASE}/api/v1/locations/depots/{vehicle['depot_id']}",
                    headers=get_auth_headers(token), timeout=10
                )
                if depot_r.ok:
                    depot_data = depot_r.json()
                    coords = depot_data.get("coordinates", {})
                    depot_lat = coords.get("lat")
                    depot_lng = coords.get("lng")
                    depot_name = depot_data.get("name", "Depot")

        lats = []
        lngs = []
        names = []

        # Start from depot
        if depot_lat is not None:
            lats.append(depot_lat)
            lngs.append(depot_lng)
            names.append(f"Depot: {depot_name}")

        for stop in stops_sorted:
            coords = stop.get("coordinates", {})
            lat = coords.get("lat", 0)
            lng = coords.get("lng", 0)
            name = stop.get("location_name") or stop.get("location_id", "?")
            seq = stop.get("sequence_index", 0)
            if lat == 0 and lng == 0:
                names.append(f"⚠️ {name} (thiếu tọa độ)")
            else:
                lats.append(float(lat))
                lngs.append(float(lng))
                names.append(f"#{seq+1} {name}")

        # Return to depot
        if depot_lat is not None and len(lats) > 1:
            lats.append(depot_lat)
            lngs.append(depot_lng)
            names.append(f"Depot: {depot_name}")

        if len(lats) < 2:
            continue

        # Route line
        fig.add_trace(go.Scatter(
            x=lngs, y=lats,
            mode="lines+markers",
            name=f"Route {idx + 1} — {vehicle_id} (Demand: {load_kg} kg)",
            line=dict(color=color, width=2),
            marker=dict(size=8, color=color, symbol="circle"),
            text=names,
            hovertemplate="%{text}<extra></extra>",
        ))

        # Numbered stop markers
        stop_lats = lats[1:-1]
        stop_lngs = lngs[1:-1]
        stop_labels = [str(i + 1) for i in range(len(stop_lats))]
        stop_names = names[1:-1]

        if stop_lats:
            fig.add_trace(go.Scatter(
                x=stop_lngs, y=stop_lats,
                mode="markers+text",
                name=f"Stops — Route {idx + 1}",
                marker=dict(
                    size=22,
                    color=color,
                    symbol="circle",
                    line=dict(color="white", width=2),
                ),
                text=stop_labels,
                textposition="middle center",
                textfont=dict(color="white", size=11, family="Arial Black"),
                hovertext=stop_names,
                hovertemplate="%{hovertext}<extra></extra>",
                showlegend=False,
            ))

    # Add depot marker (on top)
    if depot_lat is not None:
        if not depot_added:
            fig.add_trace(go.Scatter(
                x=[depot_lng], y=[depot_lat],
                mode="markers+text",
                name=f"Depot: {depot_name}",
                marker=dict(size=18, color="red", symbol="star"),
                text=["Depot"],
                textposition="top center",
                hovertemplate=f"<b>{depot_name}</b><extra>Depot</extra>",
            ))
            depot_added = True

    fig.update_layout(
        title="Lộ trình giao hàng tối ưu",
        xaxis_title="Kinh độ (Lng)",
        yaxis_title="Vĩ độ (Lat)",
        legend=dict(orientation="v", x=1.02, y=1, xanchor="left"),
        hovermode="closest",
        height=600,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")

    return fig


def main():
    st.set_page_config(
        page_title="VRP Route Visualization",
        page_icon="🚚",
        layout="wide",
    )

    params = st.experimental_get_query_params()
    job_id: str = params.get("job_id", [""])[0]
    token: str = params.get("token", [""])[0]

    st.title("🚚 VRP Route Visualization")

    if not job_id:
        st.warning("Không có job_id. Mở trang này từ nút **Xem trực quan** sau khi optimize.")
        return

    if not token:
        st.error("Thiếu token xác thực. Vui lòng đăng nhập lại và thử lại.")
        return

    with st.spinner("Đang tải dữ liệu job..."):
        job = fetch_job(job_id, token)

    if not job:
        st.error("Không tìm thấy job hoặc lỗi kết nối backend.")
        return

    if job.get("status") != "completed":
        st.warning(f"Job chưa hoàn thành (status: **{job.get('status')}**). Vui lòng thử lại sau.")
        return

    result = job.get("result", {})
    routes = result.get("routes", [])

    if not routes:
        st.warning("Job đã hoàn thành nhưng không có lộ trình nào được tạo.")
        return

    # Sidebar metrics
    with st.sidebar:
        st.header("📊 Tóm tắt")
        st.metric("Job ID", job_id[:12] + "...")
        st.metric("Số lộ trình", len(routes))
        st.metric("Tổng khoảng cách", f"{result.get('total_distance_km', 0):.1f} km")
        st.metric("Tổng thời gian", f"{result.get('total_duration_mins', 0):.0f} phút")
        if result.get("total_cost"):
            st.metric("Chi phí ước tính", f"${result['total_cost']:.2f}")

        st.divider()
        st.subheader("Chi tiết lộ trình")
        for i, r in enumerate(routes):
            with st.expander(f"Route {i + 1} — {r.get('vehicle_id', '?')}"):
                st.write(f"**Stops:** {r.get('stop_count', 0)}")
                st.write(f"**Tải:** {r.get('load_kg', 0)} kg")
                st.write(f"**Khoảng cách:** {r.get('distance_km', 0):.1f} km")
                st.write(f"**Sử dụng:** {r.get('utilization_pct', 0):.1f}%")

    # Main chart
    with st.spinner("Đang vẽ biểu đồ lộ trình..."):
        fig = build_figure(routes, token)

    st.plotly_chart(fig, use_container_width=True)

    # Unassigned customers
    if result.get("unassigned_customers"):
        st.warning(f"⚠️ {result['unassigned_count']} điểm giao chưa được phân công: {', '.join(result['unassigned_customers'])}")


if __name__ == "__main__":
    main()
