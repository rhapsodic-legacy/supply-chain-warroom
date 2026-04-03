"""Reference data for synthetic supply chain generation."""

# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------
REGIONS: dict[str, list[dict[str, str]]] = {
    "East Asia": [
        {"country": "China", "city": "Shanghai"},
        {"country": "China", "city": "Shenzhen"},
        {"country": "China", "city": "Guangzhou"},
        {"country": "China", "city": "Suzhou"},
        {"country": "South Korea", "city": "Seoul"},
        {"country": "South Korea", "city": "Busan"},
        {"country": "Japan", "city": "Tokyo"},
        {"country": "Japan", "city": "Osaka"},
        {"country": "Taiwan", "city": "Taipei"},
        {"country": "Vietnam", "city": "Ho Chi Minh City"},
        {"country": "Vietnam", "city": "Hanoi"},
    ],
    "South Asia": [
        {"country": "India", "city": "Mumbai"},
        {"country": "India", "city": "Chennai"},
        {"country": "India", "city": "Bangalore"},
        {"country": "India", "city": "Hyderabad"},
        {"country": "Bangladesh", "city": "Dhaka"},
    ],
    "Europe": [
        {"country": "Germany", "city": "Hamburg"},
        {"country": "Germany", "city": "Munich"},
        {"country": "Netherlands", "city": "Rotterdam"},
        {"country": "United Kingdom", "city": "London"},
        {"country": "Italy", "city": "Genoa"},
        {"country": "France", "city": "Lyon"},
        {"country": "Poland", "city": "Warsaw"},
    ],
    "North America": [
        {"country": "United States", "city": "Los Angeles"},
        {"country": "United States", "city": "Houston"},
        {"country": "United States", "city": "Chicago"},
        {"country": "Mexico", "city": "Monterrey"},
        {"country": "Canada", "city": "Toronto"},
    ],
    "South America": [
        {"country": "Brazil", "city": "Sao Paulo"},
        {"country": "Colombia", "city": "Bogota"},
        {"country": "Chile", "city": "Santiago"},
    ],
}

# ---------------------------------------------------------------------------
# Ports  (lat/lon to 4 decimals)
# ---------------------------------------------------------------------------
PORTS: dict[str, dict] = {
    # East Asia
    "Shanghai": {
        "country": "China",
        "region": "East Asia",
        "lat": 31.2304,
        "lon": 121.4737,
    },
    "Shenzhen": {
        "country": "China",
        "region": "East Asia",
        "lat": 22.5431,
        "lon": 114.0579,
    },
    "Busan": {
        "country": "South Korea",
        "region": "East Asia",
        "lat": 35.1796,
        "lon": 129.0756,
    },
    "Tokyo": {
        "country": "Japan",
        "region": "East Asia",
        "lat": 35.6532,
        "lon": 139.8395,
    },
    "Ho Chi Minh City": {
        "country": "Vietnam",
        "region": "East Asia",
        "lat": 10.8231,
        "lon": 106.6297,
    },
    # South Asia
    "Mumbai": {
        "country": "India",
        "region": "South Asia",
        "lat": 19.0760,
        "lon": 72.8777,
    },
    "Chennai": {
        "country": "India",
        "region": "South Asia",
        "lat": 13.0827,
        "lon": 80.2707,
    },
    # Europe
    "Rotterdam": {
        "country": "Netherlands",
        "region": "Europe",
        "lat": 51.9225,
        "lon": 4.4792,
    },
    "Hamburg": {
        "country": "Germany",
        "region": "Europe",
        "lat": 53.5511,
        "lon": 9.9937,
    },
    "Felixstowe": {
        "country": "United Kingdom",
        "region": "Europe",
        "lat": 51.9615,
        "lon": 1.3513,
    },
    "Genoa": {
        "country": "Italy",
        "region": "Europe",
        "lat": 44.4056,
        "lon": 8.9463,
    },
    # North America
    "Los Angeles": {
        "country": "United States",
        "region": "North America",
        "lat": 33.7405,
        "lon": -118.2608,
    },
    "Long Beach": {
        "country": "United States",
        "region": "North America",
        "lat": 33.7540,
        "lon": -118.2165,
    },
    "New York/Newark": {
        "country": "United States",
        "region": "North America",
        "lat": 40.6840,
        "lon": -74.1502,
    },
    "Savannah": {
        "country": "United States",
        "region": "North America",
        "lat": 32.0809,
        "lon": -81.0912,
    },
    "Houston": {
        "country": "United States",
        "region": "North America",
        "lat": 29.7534,
        "lon": -95.0135,
    },
    # South America
    "Santos": {
        "country": "Brazil",
        "region": "South America",
        "lat": -23.9535,
        "lon": -46.3226,
    },
    "Cartagena": {
        "country": "Colombia",
        "region": "South America",
        "lat": 10.3910,
        "lon": -75.5143,
    },
}

# ---------------------------------------------------------------------------
# Product catalog  (25 products, 4 categories)
# ---------------------------------------------------------------------------
PRODUCT_CATALOG: list[dict] = [
    # --- Electronics (7) ---
    {"sku": "ELEC-MCU-7200", "name": "ARM Cortex-M7 Microcontroller", "category": "electronics", "unit_cost": 8.50, "weight_kg": 0.02, "is_critical": True, "description": "High-performance 32-bit MCU for industrial IoT and motor control"},
    {"sku": "ELEC-MEM-3200", "name": "DDR5 16GB Memory Module", "category": "electronics", "unit_cost": 42.00, "weight_kg": 0.03, "is_critical": True, "description": "Server-grade DDR5-4800 ECC registered memory"},
    {"sku": "ELEC-CAP-1000", "name": "MLCC 100uF Capacitor Array", "category": "electronics", "unit_cost": 0.85, "weight_kg": 0.001, "is_critical": True, "description": "Multi-layer ceramic capacitor pack for power filtering"},
    {"sku": "ELEC-SEN-9050", "name": "LiDAR Proximity Sensor", "category": "electronics", "unit_cost": 135.00, "weight_kg": 0.15, "is_critical": False, "description": "Time-of-flight LiDAR module for autonomous systems"},
    {"sku": "ELEC-PCB-4400", "name": "8-Layer HDI PCB Blank", "category": "electronics", "unit_cost": 24.50, "weight_kg": 0.08, "is_critical": False, "description": "High-density interconnect board for miniaturized assemblies"},
    {"sku": "ELEC-DIS-2100", "name": "OLED 6.7\" Display Panel", "category": "electronics", "unit_cost": 67.00, "weight_kg": 0.04, "is_critical": False, "description": "AMOLED flexible display for consumer devices"},
    {"sku": "ELEC-BAT-5500", "name": "Li-Ion 5000mAh Cell", "category": "electronics", "unit_cost": 5.20, "weight_kg": 0.07, "is_critical": True, "description": "Cylindrical lithium-ion cell for EV battery packs"},
    # --- Automotive (6) ---
    {"sku": "AUTO-BRK-3100", "name": "Ceramic Brake Pad Set", "category": "automotive", "unit_cost": 32.00, "weight_kg": 2.50, "is_critical": True, "description": "High-temp ceramic compound front/rear brake pads"},
    {"sku": "AUTO-WIR-6600", "name": "CAN Bus Wiring Harness", "category": "automotive", "unit_cost": 78.00, "weight_kg": 3.20, "is_critical": True, "description": "Full vehicle CAN-FD wiring loom with connectors"},
    {"sku": "AUTO-TUR-1200", "name": "Twin-Scroll Turbocharger", "category": "automotive", "unit_cost": 420.00, "weight_kg": 8.50, "is_critical": False, "description": "Variable geometry twin-scroll turbo for 2.0L engines"},
    {"sku": "AUTO-SUS-8800", "name": "Adaptive Damper Assembly", "category": "automotive", "unit_cost": 195.00, "weight_kg": 5.40, "is_critical": False, "description": "Electronically controlled magnetorheological damper"},
    {"sku": "AUTO-CAT-4500", "name": "Catalytic Converter Core", "category": "automotive", "unit_cost": 310.00, "weight_kg": 4.80, "is_critical": True, "description": "Palladium/rhodium substrate for Euro 7 compliance"},
    {"sku": "AUTO-ECU-7700", "name": "ADAS Control Module", "category": "automotive", "unit_cost": 245.00, "weight_kg": 0.35, "is_critical": True, "description": "Advanced driver-assistance ECU with sensor fusion"},
    # --- Pharma (6) ---
    {"sku": "PHRM-API-1100", "name": "Ibuprofen API Powder", "category": "pharma", "unit_cost": 18.00, "weight_kg": 1.00, "is_critical": True, "description": "Active pharmaceutical ingredient, USP grade bulk"},
    {"sku": "PHRM-VIA-2200", "name": "Borosilicate Glass Vials 10mL", "category": "pharma", "unit_cost": 0.45, "weight_kg": 0.02, "is_critical": True, "description": "Type I borosilicate vials for injectable formulations"},
    {"sku": "PHRM-CAP-3300", "name": "Enteric Coating Capsules", "category": "pharma", "unit_cost": 0.12, "weight_kg": 0.001, "is_critical": False, "description": "Acid-resistant HPMC capsules size 0"},
    {"sku": "PHRM-EXC-4400", "name": "Microcrystalline Cellulose", "category": "pharma", "unit_cost": 6.50, "weight_kg": 25.00, "is_critical": False, "description": "Pharmaceutical excipient, 50kg drum"},
    {"sku": "PHRM-SYR-5500", "name": "Pre-Filled Syringe Bodies", "category": "pharma", "unit_cost": 1.80, "weight_kg": 0.01, "is_critical": True, "description": "COP polymer syringe barrels with luer lock"},
    {"sku": "PHRM-FIL-6600", "name": "Sterile Filtration Membrane", "category": "pharma", "unit_cost": 95.00, "weight_kg": 0.30, "is_critical": False, "description": "0.22um PVDF membrane cartridge for bioprocessing"},
    # --- Consumer Goods (6) ---
    {"sku": "CONS-TEX-1100", "name": "Organic Cotton Jersey Fabric", "category": "consumer_goods", "unit_cost": 8.50, "weight_kg": 0.30, "is_critical": False, "description": "GOTS-certified 180gsm single jersey roll"},
    {"sku": "CONS-PKG-2200", "name": "Recycled Kraft Packaging Box", "category": "consumer_goods", "unit_cost": 0.95, "weight_kg": 0.25, "is_critical": False, "description": "FSC-certified corrugated shipper box 12x10x8"},
    {"sku": "CONS-PLM-3300", "name": "Fragrance Oil Blend (Cedarwood)", "category": "consumer_goods", "unit_cost": 28.00, "weight_kg": 0.50, "is_critical": False, "description": "Clean-label essential oil blend for home goods"},
    {"sku": "CONS-CER-4400", "name": "Porcelain Dinnerware Set Blanks", "category": "consumer_goods", "unit_cost": 15.00, "weight_kg": 4.00, "is_critical": False, "description": "Unglazed 12-piece set for custom finishing"},
    {"sku": "CONS-SOL-5500", "name": "Monocrystalline Solar Cell 6x6", "category": "consumer_goods", "unit_cost": 3.80, "weight_kg": 0.02, "is_critical": False, "description": "22% efficiency cells for portable charger kits"},
    {"sku": "CONS-LED-6600", "name": "Smart LED Bulb PCB Assembly", "category": "consumer_goods", "unit_cost": 4.20, "weight_kg": 0.05, "is_critical": False, "description": "WiFi-enabled dimmable LED driver board"},
]

# ---------------------------------------------------------------------------
# Trade lanes  (36 routes)
# ---------------------------------------------------------------------------
TRADE_LANES: list[dict] = [
    # East Asia -> North America (transpacific)
    {"origin": "Shanghai", "dest": "Los Angeles", "mode": "ocean", "days": 14, "var": 3, "cost_kg": 0.18, "risk": 0.25, "cap": 18000},
    {"origin": "Shanghai", "dest": "Long Beach", "mode": "ocean", "days": 15, "var": 3, "cost_kg": 0.17, "risk": 0.25, "cap": 20000},
    {"origin": "Shanghai", "dest": "New York/Newark", "mode": "ocean", "days": 30, "var": 5, "cost_kg": 0.22, "risk": 0.30, "cap": 12000},
    {"origin": "Shenzhen", "dest": "Los Angeles", "mode": "ocean", "days": 16, "var": 3, "cost_kg": 0.19, "risk": 0.22, "cap": 15000},
    {"origin": "Shenzhen", "dest": "Savannah", "mode": "ocean", "days": 28, "var": 4, "cost_kg": 0.21, "risk": 0.28, "cap": 10000},
    {"origin": "Busan", "dest": "Long Beach", "mode": "ocean", "days": 12, "var": 2, "cost_kg": 0.16, "risk": 0.18, "cap": 14000},
    {"origin": "Busan", "dest": "Los Angeles", "mode": "ocean", "days": 11, "var": 2, "cost_kg": 0.15, "risk": 0.15, "cap": 16000},
    {"origin": "Tokyo", "dest": "Los Angeles", "mode": "ocean", "days": 10, "var": 2, "cost_kg": 0.20, "risk": 0.12, "cap": 12000},
    {"origin": "Ho Chi Minh City", "dest": "Long Beach", "mode": "ocean", "days": 20, "var": 4, "cost_kg": 0.21, "risk": 0.30, "cap": 8000},
    # East Asia -> Europe
    {"origin": "Shanghai", "dest": "Rotterdam", "mode": "ocean", "days": 28, "var": 5, "cost_kg": 0.20, "risk": 0.35, "cap": 16000},
    {"origin": "Shanghai", "dest": "Hamburg", "mode": "ocean", "days": 30, "var": 5, "cost_kg": 0.21, "risk": 0.35, "cap": 14000},
    {"origin": "Shenzhen", "dest": "Rotterdam", "mode": "ocean", "days": 26, "var": 4, "cost_kg": 0.19, "risk": 0.32, "cap": 15000},
    {"origin": "Shenzhen", "dest": "Felixstowe", "mode": "ocean", "days": 27, "var": 4, "cost_kg": 0.20, "risk": 0.30, "cap": 11000},
    {"origin": "Busan", "dest": "Rotterdam", "mode": "ocean", "days": 26, "var": 4, "cost_kg": 0.18, "risk": 0.28, "cap": 13000},
    {"origin": "Ho Chi Minh City", "dest": "Genoa", "mode": "ocean", "days": 22, "var": 4, "cost_kg": 0.23, "risk": 0.35, "cap": 7000},
    # South Asia -> Europe
    {"origin": "Mumbai", "dest": "Rotterdam", "mode": "ocean", "days": 18, "var": 3, "cost_kg": 0.16, "risk": 0.30, "cap": 12000},
    {"origin": "Mumbai", "dest": "Felixstowe", "mode": "ocean", "days": 20, "var": 3, "cost_kg": 0.17, "risk": 0.28, "cap": 10000},
    {"origin": "Chennai", "dest": "Hamburg", "mode": "ocean", "days": 22, "var": 4, "cost_kg": 0.18, "risk": 0.32, "cap": 9000},
    {"origin": "Chennai", "dest": "Genoa", "mode": "ocean", "days": 16, "var": 3, "cost_kg": 0.15, "risk": 0.25, "cap": 8000},
    # South Asia -> North America
    {"origin": "Mumbai", "dest": "New York/Newark", "mode": "ocean", "days": 25, "var": 5, "cost_kg": 0.22, "risk": 0.35, "cap": 10000},
    {"origin": "Chennai", "dest": "Savannah", "mode": "ocean", "days": 28, "var": 5, "cost_kg": 0.24, "risk": 0.38, "cap": 8000},
    # Europe -> North America (transatlantic)
    {"origin": "Rotterdam", "dest": "New York/Newark", "mode": "ocean", "days": 9, "var": 2, "cost_kg": 0.14, "risk": 0.10, "cap": 20000},
    {"origin": "Hamburg", "dest": "New York/Newark", "mode": "ocean", "days": 10, "var": 2, "cost_kg": 0.15, "risk": 0.10, "cap": 18000},
    {"origin": "Rotterdam", "dest": "Savannah", "mode": "ocean", "days": 12, "var": 2, "cost_kg": 0.15, "risk": 0.12, "cap": 14000},
    {"origin": "Felixstowe", "dest": "New York/Newark", "mode": "ocean", "days": 10, "var": 2, "cost_kg": 0.16, "risk": 0.10, "cap": 15000},
    {"origin": "Genoa", "dest": "New York/Newark", "mode": "ocean", "days": 14, "var": 3, "cost_kg": 0.17, "risk": 0.15, "cap": 11000},
    # South America -> North America
    {"origin": "Santos", "dest": "Houston", "mode": "ocean", "days": 14, "var": 3, "cost_kg": 0.13, "risk": 0.20, "cap": 12000},
    {"origin": "Santos", "dest": "New York/Newark", "mode": "ocean", "days": 12, "var": 3, "cost_kg": 0.14, "risk": 0.18, "cap": 10000},
    {"origin": "Cartagena", "dest": "Houston", "mode": "ocean", "days": 5, "var": 1, "cost_kg": 0.10, "risk": 0.12, "cap": 8000},
    {"origin": "Cartagena", "dest": "Savannah", "mode": "ocean", "days": 6, "var": 1, "cost_kg": 0.11, "risk": 0.14, "cap": 7000},
    # Air freight premium lanes
    {"origin": "Shanghai", "dest": "Los Angeles", "mode": "air", "days": 2, "var": 1, "cost_kg": 4.50, "risk": 0.05, "cap": 120},
    {"origin": "Shenzhen", "dest": "Los Angeles", "mode": "air", "days": 2, "var": 1, "cost_kg": 4.80, "risk": 0.05, "cap": 100},
    {"origin": "Tokyo", "dest": "Los Angeles", "mode": "air", "days": 1, "var": 0, "cost_kg": 5.20, "risk": 0.03, "cap": 80},
    {"origin": "Shanghai", "dest": "Rotterdam", "mode": "air", "days": 2, "var": 1, "cost_kg": 5.00, "risk": 0.05, "cap": 100},
    {"origin": "Mumbai", "dest": "New York/Newark", "mode": "air", "days": 2, "var": 1, "cost_kg": 4.20, "risk": 0.06, "cap": 90},
    # Rail (China-Europe land bridge)
    {"origin": "Shanghai", "dest": "Hamburg", "mode": "rail", "days": 18, "var": 3, "cost_kg": 0.60, "risk": 0.40, "cap": 3000},
]

# ---------------------------------------------------------------------------
# Seasonality profiles (monthly multipliers, Jan=index 0)
# ---------------------------------------------------------------------------
SEASONALITY_PROFILES: dict[str, list[float]] = {
    "electronics": [0.85, 0.80, 0.90, 0.95, 1.00, 1.00, 1.05, 1.10, 1.15, 1.20, 1.30, 1.10],
    "automotive":  [0.90, 0.85, 0.95, 1.00, 1.05, 1.10, 1.05, 1.00, 1.10, 1.15, 1.05, 0.80],
    "pharma":      [1.10, 1.05, 1.00, 0.95, 0.90, 0.90, 0.95, 0.95, 1.00, 1.05, 1.10, 1.15],
    "consumer_goods": [0.75, 0.70, 0.80, 0.90, 0.95, 1.00, 1.00, 1.05, 1.10, 1.20, 1.40, 1.25],
}

# ---------------------------------------------------------------------------
# Risk event templates
# ---------------------------------------------------------------------------
RISK_TEMPLATES: list[dict] = [
    # Weather
    {
        "event_type": "weather",
        "title_tpl": "Typhoon {name} approaching {region}",
        "desc_tpl": "Category {cat} typhoon {name} is projected to make landfall near {port}, with sustained winds of {wind} km/h. Port operations expected to halt for {days} days. Vessels diverted to alternate berths.",
        "severity_range": ("high", "critical"),
        "score_range": (0.70, 0.95),
        "duration_days": (3, 10),
        "regions": ["East Asia"],
    },
    {
        "event_type": "weather",
        "title_tpl": "Severe winter storm disrupts {region} logistics",
        "desc_tpl": "A major winter storm system is blanketing {region} with heavy snow and ice. Highway closures and rail delays reported across {country}. Inland distribution centers operating at reduced capacity.",
        "severity_range": ("medium", "high"),
        "score_range": (0.45, 0.75),
        "duration_days": (2, 7),
        "regions": ["Europe", "North America"],
    },
    # Geopolitical
    {
        "event_type": "geopolitical",
        "title_tpl": "New tariff regime announced for {region} imports",
        "desc_tpl": "Regulatory authorities have imposed {pct}% additional duties on {category} imports originating from {country}. Effective within {days} days, impacting landed costs and margin forecasts for affected SKUs.",
        "severity_range": ("medium", "high"),
        "score_range": (0.50, 0.80),
        "duration_days": (30, 180),
        "regions": ["East Asia", "South Asia"],
    },
    {
        "event_type": "geopolitical",
        "title_tpl": "Export restrictions tighten on {category} from {country}",
        "desc_tpl": "Government of {country} has announced export licensing requirements for {category} components. Lead time for license approval estimated at {days} weeks. Supply continuity at risk for critical SKUs.",
        "severity_range": ("high", "critical"),
        "score_range": (0.65, 0.90),
        "duration_days": (14, 90),
        "regions": ["East Asia"],
    },
    # Port closure
    {
        "event_type": "port_closure",
        "title_tpl": "{port} port operations suspended",
        "desc_tpl": "Port of {port} has suspended inbound and outbound vessel operations due to {reason}. Approximately {vessels} vessels are queued at anchorage. Average delay estimated at {days} days.",
        "severity_range": ("high", "critical"),
        "score_range": (0.70, 0.95),
        "duration_days": (3, 14),
        "regions": ["East Asia", "North America", "Europe"],
    },
    # Supplier delay
    {
        "event_type": "supplier_delay",
        "title_tpl": "Production disruption at {supplier}",
        "desc_tpl": "Key supplier {supplier} in {city}, {country} reports {reason}. Estimated production shortfall of {pct}% for the next {weeks} weeks. Alternative sourcing being evaluated.",
        "severity_range": ("low", "high"),
        "score_range": (0.30, 0.70),
        "duration_days": (7, 30),
        "regions": ["East Asia", "South Asia", "Europe"],
    },
    # Demand spike
    {
        "event_type": "demand_spike",
        "title_tpl": "Unexpected demand surge for {category}",
        "desc_tpl": "Market demand for {category} products has spiked {pct}% above forecast in {region}. Driven by {reason}. Safety stock buffers projected to deplete within {days} days at current run rate.",
        "severity_range": ("medium", "high"),
        "score_range": (0.50, 0.80),
        "duration_days": (14, 45),
        "regions": ["North America", "Europe"],
    },
    # Labor strike
    {
        "event_type": "labor_strike",
        "title_tpl": "Dockworker strike at {port}",
        "desc_tpl": "Union workers at the Port of {port} have initiated a work stoppage over {reason}. Container handling throughput reduced by {pct}%. Negotiations ongoing with no resolution timeline. Cargo diversion plans activated.",
        "severity_range": ("medium", "critical"),
        "score_range": (0.55, 0.90),
        "duration_days": (5, 21),
        "regions": ["North America", "Europe"],
    },
]
