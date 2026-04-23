import json
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import HTTPException

from app.schemas import VinDecodeItem, VinDecodeResponse, VinDecodeSection

NHTSA_SOURCE = "NHTSA vPIC"
NHTSA_API_BASE = "https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValuesExtended/{vin}"
NHTSA_PORTAL_BASE = "https://vpic.nhtsa.dot.gov/decoder/Decoder"
TIMEOUT_SECONDS = 12


IGNORED_VALUES = {"", "0", "Not Applicable", "Not Available", "Unknown", "null", "None"}


SUMMARY_FIELDS = [
    ("make", "Make", "Make"),
    ("model", "Model", "Model"),
    ("model_year", "Model Year", "ModelYear"),
    ("body_class", "Body Class", "BodyClass"),
    ("vehicle_type", "Vehicle Type", "VehicleType"),
    ("trim", "Trim", "Trim"),
    ("series", "Series", "Series"),
]

SECTION_FIELDS = {
    "Identification": [
        ("manufacturer", "Manufacturer", "Manufacturer"),
        ("plant_city", "Plant City", "PlantCity"),
        ("plant_state", "Plant State", "PlantState"),
        ("plant_country", "Plant Country", "PlantCountry"),
        ("vehicle_descriptor", "Vehicle Descriptor", "VehicleDescriptor"),
        ("gvwr", "GVWR", "GVWR"),
    ],
    "Powertrain": [
        ("drive_type", "Drive Type", "DriveType"),
        ("fuel_type_primary", "Fuel Type", "FuelTypePrimary"),
        ("electrification_level", "Electrification", "ElectrificationLevel"),
        ("ev_drive_unit", "EV Drive Unit", "EVDriveUnit"),
        ("engine_hp", "Horsepower", "EngineHP"),
        ("transmission_style", "Transmission", "TransmissionStyle"),
        ("transmission_speeds", "Transmission Speeds", "TransmissionSpeeds"),
        ("battery_type", "Battery Type", "BatteryType"),
        ("battery_kwh", "Battery kWh", "BatteryKWh"),
    ],
    "Body & Cabin": [
        ("doors", "Doors", "Doors"),
        ("seats", "Seats", "Seats"),
        ("seat_rows", "Seat Rows", "SeatRows"),
        ("steering_location", "Steering Location", "SteeringLocation"),
        ("wheelbase", "Wheelbase", "WheelBaseShort"),
        ("nhtsa_body_type", "NHTSA Body Type", "NCSABodyType"),
    ],
    "Safety & Driver Assist": [
        ("abs", "ABS", "ABS"),
        ("esc", "ESC", "ESC"),
        ("traction_control", "Traction Control", "TractionControl"),
        ("blind_spot_monitor", "Blind Spot Monitor", "BlindSpotMon"),
        ("forward_collision_warning", "Forward Collision Warning", "ForwardCollisionWarning"),
        ("lane_departure_warning", "Lane Departure Warning", "LaneDepartureWarning"),
        ("lane_keep_system", "Lane Keep System", "LaneKeepSystem"),
        ("adaptive_cruise_control", "Adaptive Cruise Control", "AdaptiveCruiseControl"),
        ("park_assist", "Park Assist", "ParkAssist"),
        ("rear_visibility_system", "Rear Visibility System", "RearVisibilitySystem"),
        (
            "pedestrian_aeb",
            "Pedestrian Automatic Emergency Braking",
            "PedestrianAutomaticEmergencyBraking",
        ),
        ("auto_reverse_system", "Auto Reverse System", "AutoReverseSystem"),
        ("tpms", "TPMS", "TPMS"),
        ("daytime_running_light", "Daytime Running Light", "DaytimeRunningLight"),
        ("keyless_ignition", "Keyless Ignition", "KeylessIgnition"),
        ("dynamic_brake_support", "Dynamic Brake Support", "DynamicBrakeSupport"),
        (
            "pedestrian_alert_sound",
            "Pedestrian Alert Sound",
            "AutomaticPedestrianAlertingSound",
        ),
    ],
}


def _clean_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in IGNORED_VALUES:
        return None
    return text


@lru_cache(maxsize=512)
def _fetch_decoded_payload(vin: str, model_year: int | None = None) -> tuple[dict[str, object], str | None]:
    query = {"format": "json"}
    if model_year is not None:
        query["modelyear"] = str(model_year)
    api_url = f"{NHTSA_API_BASE.format(vin=vin)}?{urlencode(query)}"
    try:
        with urlopen(api_url, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail=f"NHTSA decoder unavailable: {exc}") from exc

    results = payload.get("Results") or []
    if not results:
        raise HTTPException(status_code=404, detail="VIN decode not found")

    record = results[0]
    if not isinstance(record, dict):
        raise HTTPException(status_code=502, detail="Unexpected NHTSA decoder response")

    note = _clean_value(payload.get("Message"))
    return record, note


def decode_vin(vin: str, model_year: int | None = None) -> VinDecodeResponse:
    record, note = _fetch_decoded_payload(vin, model_year)
    source_url = f"{NHTSA_PORTAL_BASE}?VIN={vin}"

    summary = [
        VinDecodeItem(key=key, label=label, value=value)
        for key, label, field in SUMMARY_FIELDS
        if (value := _clean_value(record.get(field)))
    ]

    sections: list[VinDecodeSection] = []
    for title, fields in SECTION_FIELDS.items():
        items = [
            VinDecodeItem(key=key, label=label, value=value)
            for key, label, field in fields
            if (value := _clean_value(record.get(field)))
        ]
        if items:
            sections.append(VinDecodeSection(title=title, items=items))

    return VinDecodeResponse(
        vin=vin,
        source=NHTSA_SOURCE,
        source_url=source_url,
        note=note,
        summary=summary,
        sections=sections,
    )
