REGISTON_HOSPITAL_CATALOG = [
    {
        "name": "City Hospital",
        "distance_km": 1.2,
        "capacity_min": 150,
        "capacity_max": 300,
        "address": "Navoi Avenue, Samarqand",
        "map_code": "MW8X+6P6",
        "note": "Hospital, Open",
    },
    {
        "name": "SamMI Clinic",
        "distance_km": 1.5,
        "capacity_min": 200,
        "capacity_max": 400,
        "address": "Ankabay ko'chasi 6, Samarqand",
        "map_code": "MX89+8FR",
        "note": "University hospital, Open",
    },
    {
        "name": "Samarkand Regional Hospital",
        "distance_km": 1.8,
        "capacity_min": 400,
        "capacity_max": 700,
        "address": "Mirzo Ulug'bek ko'chasi, Samarqand",
        "map_code": "MW6V+58P",
        "note": "Hospital",
    },
    {
        "name": "Traumatological Hospital",
        "distance_km": 2.3,
        "capacity_min": 100,
        "capacity_max": 200,
        "address": "Samarqand (aniq ko'cha ko'rsatilmagan)",
        "map_code": "MWH8+R8P",
        "note": "Hospital, Open",
    },
    {
        "name": "ZARMED PRATIKSHA Bog'ishamol",
        "distance_km": 2.7,
        "capacity_min": 100,
        "capacity_max": 250,
        "address": "Isayev ko'chasi 16, Samarqand",
        "map_code": "",
        "note": "Private hospital, Open",
    },
    {
        "name": "Meros International Hospital",
        "distance_km": 3.5,
        "capacity_min": 50,
        "capacity_max": 120,
        "address": "Ali Qushchi ko'chasi, Samarqand",
        "map_code": "",
        "note": "Private hospital, Open",
    },
    {
        "name": "Oncology Center (Respublika markazi filial)",
        "distance_km": 4.2,
        "capacity_min": 150,
        "capacity_max": 300,
        "address": "Jomiy ko'chasi, Samarqand",
        "map_code": "JXWQ+26P",
        "note": "Cancer treatment center, Open",
    },
    {
        "name": "Pediatric Hospital Samarkand State Medical University",
        "distance_km": 4.8,
        "capacity_min": 200,
        "capacity_max": 350,
        "address": "Samarqand (universitet hududi)",
        "map_code": "MXFC+8XM",
        "note": "Hospital, Open",
    },
    {
        "name": "Samarkand Maternity Hospital #4",
        "distance_km": 5.3,
        "capacity_min": 150,
        "capacity_max": 300,
        "address": "Ali Qushchi ko'chasi 35, Samarqand",
        "map_code": "",
        "note": "Maternity hospital, Open",
    },
    {
        "name": "Marokand Hospital",
        "distance_km": 6.5,
        "capacity_min": 100,
        "capacity_max": 200,
        "address": "M-37 yo'li, Buxoro shossesi 42, Samarqand tumani",
        "map_code": "",
        "note": "Hospital, Open",
    },
]


def get_registon_hospitals_for_dashboard():
    rows = []
    for item in REGISTON_HOSPITAL_CATALOG:
        rows.append(
            {
                "name": item["name"],
                "distance_km": item["distance_km"],
                "capacity_range": f'{item["capacity_min"]}-{item["capacity_max"]}',
                "note": item["note"],
                "address": item["address"],
                "map_code": item["map_code"],
            }
        )
    return rows


def get_hospital_choice_pairs():
    return [(item["name"], item["name"]) for item in REGISTON_HOSPITAL_CATALOG]


def get_hospital_autofill_map():
    result = {}
    for item in REGISTON_HOSPITAL_CATALOG:
        capacity_auto = int(round((item["capacity_min"] + item["capacity_max"]) / 2))
        result[item["name"]] = {
            "address": item["address"],
            "capacity_auto": capacity_auto,
            "distance_km": item["distance_km"],
            "map_code": item["map_code"],
            "capacity_range": f'{item["capacity_min"]}-{item["capacity_max"]}',
        }
    return result
