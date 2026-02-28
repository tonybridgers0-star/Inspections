import json
from datetime import datetime

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from .database import Base, engine, get_db
from . import models, schemas, services

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inspection Order Manager API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/orders/import_csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    payload = await file.read()
    return services.import_csv_bytes(db, payload)


@app.get("/orders")
def list_orders(view_id: str | None = None, db: Session = Depends(get_db)):
    view = db.get(models.SavedView, view_id) if view_id else None
    stmt = services.apply_view_query(db, view)
    rows = db.scalars(stmt).unique().all()
    return [services.order_to_dict(r) for r in rows]


@app.post("/orders", response_model=schemas.OrderOut)
def create_order(payload: schemas.OrderCreate, db: Session = Depends(get_db)):
    order = models.Order(**payload.model_dump(exclude={"custom_fields"}))
    db.add(order)
    db.flush()
    for k, v in payload.custom_fields.items():
        services.set_custom_value(db, order.id, k, k.replace("_", " ").title(), v)
    services.log_activity(db, "order", order.id, "create", after=services.order_to_dict(order))
    db.commit()
    db.refresh(order)
    return services.order_to_dict(order)


@app.patch("/orders/{order_id}")
def update_order(order_id: str, payload: schemas.OrderUpdate, db: Session = Depends(get_db)):
    order = db.scalar(select(models.Order).where(models.Order.id == order_id).options(joinedload(models.Order.custom_values).joinedload(models.OrderCustomField.custom_field)))
    if not order:
        raise HTTPException(404, "Order not found")
    before = services.order_to_dict(order)
    data = payload.model_dump(exclude_unset=True, exclude={"custom_fields"})
    for key, value in data.items():
        setattr(order, key, value)
    for k, v in (payload.custom_fields or {}).items():
        services.set_custom_value(db, order.id, k, k.replace("_", " ").title(), v)
    db.flush()
    after = services.order_to_dict(order)
    services.log_activity(db, "order", order.id, "update", before=before, after=after)
    db.commit()
    return after


@app.post("/orders/{order_id}/complete")
def complete_order(order_id: str, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    before = services.order_to_dict(order)
    order.status = "Completed"
    order.completed_at = datetime.utcnow()
    db.flush()
    services.log_activity(db, "order", order.id, "status_change", before=before, after=services.order_to_dict(order))
    db.commit()
    return {"ok": True}


@app.delete("/orders/{order_id}")
def delete_order(order_id: str, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    db.delete(order)
    db.commit()
    return {"ok": True}


@app.get("/orders/export_csv", response_class=PlainTextResponse)
def export_csv(view_id: str | None = None, db: Session = Depends(get_db)):
    view = db.get(models.SavedView, view_id) if view_id else None
    rows = [services.order_to_dict(r) for r in db.scalars(services.apply_view_query(db, view)).unique().all()]
    return services.export_orders_csv(rows)


@app.get("/views", response_model=list[schemas.SavedViewOut])
def list_views(db: Session = Depends(get_db)):
    return db.scalars(select(models.SavedView)).all()


@app.post("/views", response_model=schemas.SavedViewOut)
def create_view(payload: schemas.SavedViewIn, db: Session = Depends(get_db)):
    view = models.SavedView(**payload.model_dump())
    db.add(view)
    db.commit()
    db.refresh(view)
    return view


@app.patch("/views/{view_id}", response_model=schemas.SavedViewOut)
def patch_view(view_id: str, payload: schemas.SavedViewIn, db: Session = Depends(get_db)):
    view = db.get(models.SavedView, view_id)
    if not view:
        raise HTTPException(404, "View not found")
    for k, v in payload.model_dump().items():
        setattr(view, k, v)
    db.commit()
    db.refresh(view)
    return view


@app.delete("/views/{view_id}")
def remove_view(view_id: str, db: Session = Depends(get_db)):
    db.execute(delete(models.SavedView).where(models.SavedView.id == view_id))
    db.commit()
    return {"ok": True}


@app.get("/custom_fields", response_model=list[schemas.CustomFieldOut])
def list_custom(db: Session = Depends(get_db)):
    return db.scalars(select(models.CustomFieldDefinition)).all()


@app.post("/custom_fields", response_model=schemas.CustomFieldOut)
def create_custom(payload: schemas.CustomFieldIn, db: Session = Depends(get_db)):
    item = services.get_or_create_custom_field(db, payload.key, payload.label, payload.field_type)
    db.commit()
    db.refresh(item)
    return item


@app.patch("/custom_fields/{field_id}", response_model=schemas.CustomFieldOut)
def patch_custom(field_id: str, payload: schemas.CustomFieldIn, db: Session = Depends(get_db)):
    item = db.get(models.CustomFieldDefinition, field_id)
    if not item:
        raise HTTPException(404, "Not found")
    item.key = payload.key
    item.label = payload.label
    item.field_type = payload.field_type
    db.commit()
    db.refresh(item)
    return item


@app.delete("/custom_fields/{field_id}")
def delete_custom(field_id: str, db: Session = Depends(get_db)):
    db.execute(delete(models.CustomFieldDefinition).where(models.CustomFieldDefinition.id == field_id))
    db.commit()
    return {"ok": True}


@app.get("/activity")
def activity(entity_type: str | None = None, entity_id: str | None = None, limit: int = 200, db: Session = Depends(get_db)):
    stmt = select(models.ActivityLog).order_by(models.ActivityLog.created_at.desc()).limit(limit)
    if entity_type:
        stmt = stmt.where(models.ActivityLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(models.ActivityLog.entity_id == entity_id)
    rows = db.scalars(stmt).all()
    return [{"id": r.id, "entity_type": r.entity_type, "entity_id": r.entity_id, "action": r.action, "before": r.before, "after": r.after, "created_at": r.created_at} for r in rows]


@app.post("/geocode/order/{order_id}")
async def geocode_order(order_id: str, db: Session = Depends(get_db)):
    order = db.get(models.Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    coords = await services.geocode_address(db, services.full_address(order))
    if not coords:
        raise HTTPException(404, "No geocode result")
    order.lat, order.lon = coords
    db.commit()
    return {"lat": order.lat, "lon": order.lon}


@app.post("/geocode/bulk")
async def geocode_bulk(view_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    view = db.get(models.SavedView, view_id) if view_id else None
    rows = db.scalars(services.apply_view_query(db, view)).unique().all()
    updated = 0
    for order in rows:
        if order.lat and order.lon:
            continue
        coords = await services.geocode_address(db, services.full_address(order))
        if coords:
            order.lat, order.lon = coords
            updated += 1
    db.commit()
    return {"updated": updated}


@app.post("/route/optimize")
async def route_optimize(view_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    start_setting = db.get(models.AppSetting, "start_location")
    if not start_setting:
        raise HTTPException(400, "Missing start location")
    osrm = db.get(models.AppSetting, "osrm_base_url")
    osrm_base = osrm.value if osrm else "http://router.project-osrm.org"
    start_coords = await services.geocode_address(db, start_setting.value)
    if not start_coords:
        raise HTTPException(400, "Cannot geocode start location")

    view = db.get(models.SavedView, view_id) if view_id else None
    rows = db.scalars(services.apply_view_query(db, view)).unique().all()
    coords = [start_coords] + [(o.lat, o.lon) for o in rows if o.lat is not None and o.lon is not None and o.status != "Completed"]
    result = await services.optimize_route(db, coords, osrm_base)
    gm = "https://www.google.com/maps/dir/?api=1"
    return {"start": start_coords, "route": result, "google_maps_url": gm}


@app.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    rows = db.scalars(select(models.AppSetting)).all()
    return {r.key: r.value for r in rows}


@app.post("/settings")
def set_settings(payload: dict, db: Session = Depends(get_db)):
    for k, v in payload.items():
        item = db.get(models.AppSetting, k)
        if item:
            item.value = str(v)
        else:
            db.add(models.AppSetting(key=k, value=str(v)))
    db.commit()
    return {"ok": True}
