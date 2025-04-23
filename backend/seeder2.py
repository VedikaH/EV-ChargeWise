import json
import re
from sqlalchemy.orm import Session
from app.models.stations import Station
from app.models.chargingCosts import ChargingConfig  # adjust import as per your app structure
from app.database.session import SessionLocal  # assuming you have a session generator like this

def parse_cost(cost_str):
    match = re.search(r"([\d.]+)", cost_str)
    return float(match.group(1)) if match else 0.0

def parse_power_output(type_of_charging):
    match = re.search(r"(\d+\.?\d*)\s*kW", type_of_charging, re.IGNORECASE)
    return float(match.group(1)) if match else None

def load_data(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def insert_data():
    db: Session = SessionLocal()
    data = load_data("C:/Users/dell/OneDrive/Desktop/EV_ChargeWise/data.txt")

    for item in data:
        station = Station(
            id=item["id"],
            name=item["name"],
            location=item["location"],
            latitude=item["latitude"],
            longitude=item["longitude"], 
            is_available=item["availability"].lower() == "open now",
            is_maintenance=False  # assuming all are not in maintenance
        )

        db.add(station)
        db.flush()  # ensures station.id is available if autogen

        cost = parse_cost(item["cost"])
        power_output = parse_power_output(item["type_of_charging"])
        charging_type = item["type_of_charging"].split()[0]  # "AC" or "DC"

        for connector in item["connectors"]:
            for _ in range(connector["count"]):
                config = ChargingConfig(
                    station_id=station.id,
                    charging_type=charging_type,
                    connector_type=connector["type"],
                    power_output=power_output,
                    cost_per_kwh=cost
                )
                db.add(config)

    db.commit()
    db.close()

if __name__ == "__main__":
    insert_data()
