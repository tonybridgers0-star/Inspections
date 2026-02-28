import csv
import io
import json
import re
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from . import models

STATUS_MAP = {
    "work in progress": "Active",
    "completed": "Completed",
    "on hold": "OnHold",
}

CSV_CUSTOM_FIELDS = {
    "Date Assigned": ("date_assigned", "Date Assigned", "date"),
    "DBA Name": ("dba_name", "DBA Name", "string"),
    "Contact": ("contact_name", "Contact", "string"),
    "Business Desc": ("business_desc", "Business Desc", "string"),
    "Priority": ("priority", "Priority", "string"),
    "Appointment": ("appointment", "Appointment", "string"),
    "Consultant Name": ("consultant_name", "Consultant Name", "string"),
    "Program Name": ("program_name", "Program Name", "string"),
}


def normalize_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.strip().lower()).strip("_")


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits if len(digits) >= 7 else None


def infer_type(value: str) -> str:
    clean = value.replace(",", "").strip()
    if re.fullmatch(r"\d+(\.\d+)?", clean):
        return "number"
    if re.fullmatch(r"\d{4}", clean):
        return "number"
    return "string"


def get_or_create_custom_field(db: Session, key: str, label: str, field_type: str = "string") -> models.CustomFieldDefinition:
    item = db.scalar(select(models.CustomFieldDefinition).where(models.CustomFieldDefinition.key == key))
    if item:
        return item
    item = models.CustomFieldDefinition(key=key, label=label, field_type=field_type)
    db.add(item)
    db.flush()
    return item


def set_custom_value(db: Session, order_id: str, key: str, label: str, value: Any, field_type: str = "string"):
    if value is None or value == "":
        return
    definition = get_or_create_custom_field(db, key, label, field_type)
    existing = db.scalar(
        select(models.OrderCustomField).where(
            models.OrderCustomField.order_id == order_id,
            models.OrderCustomField.custom_field_id == definition.id,
        )
    )
    serialized = str(value)
    if existing:
        existing.value = serialized
    else:
        db.add(models.OrderCustomField(order_id=order_id, custom_field_id=definition.id, value=serialized))


def log_activity(db: Session, entity_type: str, entity_id: str, action: str, before: Any = None, after: Any = None):
    db.add(models.ActivityLog(entity_type=entity_type, entity_id=entity_id, action=action, before=before, after=after))


def parse_special_instructions(text: str) -> dict[str, str]:
    extracted: dict[str, str] = {}
    if not text:
        return extracted

    contact = re.search(r"Contact Information\s*:\s*([^\n]+)", text, re.IGNORECASE)
    if contact:
        parts = [p.strip() for p in contact.group(1).split(",")]
        if len(parts) >= 1:
            extracted["contact_person"] = parts[0]
        for p in parts:
            if "@" in p:
                extracted["contact_email"] = p
            phone = normalize_phone(p)
            if phone:
                extracted["contact_phone"] = phone

    pairs = re.findall(r"([A-Za-z ]+?)\s*[-:]\s*([^,\n]+)", text)
    for label, value in pairs:
        key = normalize_key(label)
        extracted[key] = value.strip()

    bi = re.search(r"Building Improvements\s*[-:]\s*([^\n]+)", text, re.IGNORECASE)
    if bi:
        items = [i.strip() for i in bi.group(1).split(",")]
        for item in items:
            m = re.match(r"([A-Za-z ]+)\s*[-:]\s*(.+)", item)
            if m:
                k = normalize_key(m.group(1))
                extracted[f"improvements_{k}"] = m.group(2).strip()
    return extracted


def apply_view_query(db: Session, view: models.SavedView | None):
    stmt = select(models.Order).options(joinedload(models.Order.custom_values).joinedload(models.OrderCustomField.custom_field))
    if not view:
        return stmt
    filters = view.filters or {}
    for rule in filters.get("rules", []):
        field = rule.get("field")
        op = rule.get("op", "eq")
        value = rule.get("value")
        if field == "needs_geocode" and value:
            stmt = stmt.where((models.Order.lat.is_(None)) | (models.Order.lon.is_(None)))
        elif field.startswith("cf:"):
            key = field[3:]
            sub = (
                select(models.OrderCustomField.order_id)
                .join(models.CustomFieldDefinition, models.CustomFieldDefinition.id == models.OrderCustomField.custom_field_id)
                .where(models.CustomFieldDefinition.key == key)
            )
            if op == "contains":
                sub = sub.where(models.OrderCustomField.value.ilike(f"%{value}%"))
            else:
                sub = sub.where(models.OrderCustomField.value == str(value))
            stmt = stmt.where(models.Order.id.in_(sub))
        else:
            col = getattr(models.Order, field, None)
            if not col:
                continue
            if op == "contains":
                stmt = stmt.where(col.ilike(f"%{value}%"))
            else:
                stmt = stmt.where(col == value)

    for sort in view.sorts or []:
        col = getattr(models.Order, sort.get("field", ""), None)
        if not col:
            continue
        stmt = stmt.order_by(col.desc() if sort.get("dir") == "desc" else col.asc())
    return stmt


def order_to_dict(order: models.Order) -> dict[str, Any]:
    custom = {v.custom_field.key: v.value for v in order.custom_values}
    return {
        "id": order.id,
        "order_number": order.order_number,
        "client": order.client,
        "insured_name": order.insured_name,
        "phone": order.phone,
        "address1": order.address1,
        "city": order.city,
        "state": order.state,
        "zip": order.zip,
        "status": order.status,
        "due_date": order.due_date,
        "notes": order.notes,
        "lat": order.lat,
        "lon": order.lon,
        "completed_at": order.completed_at,
        "custom_fields": custom,
    }


def import_csv_bytes(db: Session, payload: bytes):
    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    report = {"created": 0, "updated": 0, "errors": []}
    for idx, row in enumerate(reader, start=2):
        try:
            order_number = (row.get("Assignment #") or "").strip()
            if not order_number:
                raise ValueError("Assignment # missing")
            existing = db.scalar(select(models.Order).where(models.Order.order_number == order_number))
            before = order_to_dict(existing) if existing else None
            status_raw = (row.get("Status") or "Active").strip().lower()
            status = STATUS_MAP.get(status_raw, "Active")
            notes = row.get("Special Instructions") or ""
            phone = normalize_phone(row.get("Contact"))

            target = existing or models.Order(order_number=order_number)
            target.client = row.get("Program Name")
            target.insured_name = row.get("Insured Name")
            target.phone = phone
            target.address1 = row.get("Address")
            target.city = row.get("City")
            target.state = row.get("State")
            target.zip = row.get("Zip Code")
            target.status = status
            target.due_date = row.get("Due Date")
            target.notes = notes
            if not existing:
                db.add(target)
                db.flush()

            for col, (key, label, ftype) in CSV_CUSTOM_FIELDS.items():
                set_custom_value(db, target.id, key, label, row.get(col), ftype)

            extracted = parse_special_instructions(notes)
            if extracted.get("contact_phone"):
                target.phone = extracted["contact_phone"]
            if extracted.get("contact_phone"):
                set_custom_value(db, target.id, "contact_phone", "Contact Phone", extracted["contact_phone"], "string")
            if extracted.get("contact_email"):
                set_custom_value(db, target.id, "contact_email", "Contact Email", extracted["contact_email"], "string")
            for key, value in extracted.items():
                if key in {"contact_phone", "contact_email", "contact_person"}:
                    continue
                set_custom_value(db, target.id, key, key.replace("_", " ").title(), value, infer_type(value))

            db.flush()
            after = order_to_dict(target)
            if existing:
                report["updated"] += 1
                log_activity(db, "order", target.id, "import update", before=before, after=after)
            else:
                report["created"] += 1
                log_activity(db, "order", target.id, "import create", before=None, after=after)
        except Exception as exc:
            report["errors"].append({"row": idx, "error": str(exc)})
    db.commit()
    return report


def full_address(order: models.Order) -> str:
    return ", ".join([p for p in [order.address1, order.city, order.state, order.zip] if p]).strip()


async def geocode_address(db: Session, address: str):
    normalized = address.lower().strip()
    if not normalized:
        return None
    cached = db.scalar(select(models.GeocodeCache).where(models.GeocodeCache.normalized_address == normalized))
    if cached:
        return cached.lat, cached.lon
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get("https://nominatim.openstreetmap.org/search", params={"q": address, "format": "json", "limit": 1}, headers={"User-Agent": "InspectionOrderManager/1.0"})
        resp.raise_for_status()
        data = resp.json()
    if not data:
        return None
    lat, lon = float(data[0]["lat"]), float(data[0]["lon"])
    db.add(models.GeocodeCache(normalized_address=normalized, lat=lat, lon=lon))
    db.commit()
    return lat, lon


async def optimize_route(db: Session, points: list[tuple[float, float]], osrm_base: str):
    if len(points) < 2:
        return {"distance_m": 0, "duration_s": 0, "geometry": [], "order": list(range(len(points)))}
    coords = ";".join([f"{lon},{lat}" for lat, lon in points])
    url = f"{osrm_base.rstrip('/')}/trip/v1/driving/{coords}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params={"source": "first", "roundtrip": "false", "overview": "full", "geometries": "geojson"})
        resp.raise_for_status()
        data = resp.json()
    trip = data["trips"][0]
    order = [w["waypoint_index"] for w in sorted(data["waypoints"], key=lambda x: x["waypoint_index"])]
    return {"distance_m": trip["distance"], "duration_s": trip["duration"], "geometry": trip["geometry"]["coordinates"], "order": order, "raw": data}


def export_orders_csv(rows: list[dict[str, Any]]):
    headers = ["Assignment #", "Program Name", "Insured Name", "Address", "City", "State", "Zip Code", "Status", "Due Date", "Special Instructions"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=headers)
    writer.writeheader()
    for r in rows:
        writer.writerow({
            "Assignment #": r.get("order_number"),
            "Program Name": r.get("client"),
            "Insured Name": r.get("insured_name"),
            "Address": r.get("address1"),
            "City": r.get("city"),
            "State": r.get("state"),
            "Zip Code": r.get("zip"),
            "Status": r.get("status"),
            "Due Date": r.get("due_date"),
            "Special Instructions": r.get("notes"),
        })
    return buf.getvalue()
