from __future__ import annotations

# Временные (MVP) захардкоженные тарифы.
# Важно: на реальном проекте тарифы должны храниться в БД/конфиге и иметь дату актуальности.
MOSCOW_TARIFFS = {
    "cold_water_m3": 35.0,  # руб / м3
    "hot_water_m3": 180.0,  # руб / м3
    "electricity_kwh": 7.0,  # руб / кВт*ч
    "maintenance_m2": 22.0,  # руб / м2
    "cap_repair_m2": 15.0,  # руб / м2
}

