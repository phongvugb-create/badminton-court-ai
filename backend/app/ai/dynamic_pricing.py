from datetime import datetime

def calculate_dynamic_price(base_price: float, slot_date: str, start_time: str, occupancy_rate: float = 0.5) -> dict:
    """
    Calculate AI Dynamic Price based on peak hours, weekend factors, and court occupancy.
    Formula:
    P_dynamic = P_base * (1 + alpha_peak + beta_demand)
    """
    # Parse hour
    try:
        hour = int(start_time.split(":")[0])
    except Exception:
        hour = 18

    # Check weekend
    is_weekend = False
    try:
        dt = datetime.strptime(slot_date, "%Y-%m-%d")
        is_weekend = dt.weekday() >= 5 # 5=Sat, 6=Sun
    except Exception:
        pass

    alpha_peak = 0.0
    adjustment_reason = "Giá chuẩn tiêu chuẩn"

    # Peak hours: 17:00 - 21:00 or all day weekend
    if is_weekend:
        alpha_peak = 0.20 # +20% for weekend
        adjustment_reason = "Giờ cao điểm cuối tuần (+20%)"
    elif 17 <= hour < 21:
        alpha_peak = 0.25 # +25% for evening peak
        adjustment_reason = "Khung giờ vàng tối ngày thường (+25%)"
    elif 5 <= hour < 8:
        alpha_peak = -0.10 # -10% early bird
        adjustment_reason = "Giảm giá chơi sáng sớm (-10%)"
    elif 8 <= hour < 14:
        alpha_peak = -0.15 # -15% off-peak afternoon
        adjustment_reason = "Ưu đãi giờ hành chính (-15%)"

    # Demand factor from occupancy
    beta_demand = 0.0
    if occupancy_rate > 0.85:
        beta_demand = 0.10
        adjustment_reason += " & Nhu cầu sân cao (+10%)"
    elif occupancy_rate < 0.20 and not is_weekend:
        beta_demand = -0.05
        adjustment_reason += " & Kích cầu giờ trống (-5%)"

    multiplier = 1.0 + alpha_peak + beta_demand
    # Keep multiplier in reasonable bounds [0.75, 1.40]
    multiplier = max(0.75, min(1.40, multiplier))
    
    dynamic_price = round(base_price * multiplier, -3) # Round to thousand VND

    return {
        "base_price": base_price,
        "dynamic_price": dynamic_price,
        "multiplier": round(multiplier, 2),
        "adjustment_reason": adjustment_reason,
        "is_ai_applied": True
    }
