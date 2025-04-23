from sqlalchemy import Column, Float, ForeignKey, Integer, String
from app.database.base import Base
from sqlalchemy.orm import relationship

class ChargingConfig(Base):
    __tablename__ = "charging_configs"

    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, ForeignKey("stations.id"))
    charging_type = Column(String)  # AC or DC
    connector_type = Column(String)  # Type2, CCS, etc.
    power_output = Column(Float)
    cost_per_kwh = Column(Float)  # e.g., 10.0 for ₹10/kWh or $0.25/kWh

    station = relationship("Station", back_populates="charging_configs")