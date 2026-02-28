from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine

client = TestClient(app)


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_import_upsert_and_complete_and_export_and_view_filter():
    reset_db()
    csv_content = """Date Assigned,Assignment #,Due Date,Insured Name,DBA Name,Contact,Business Desc,Address,City,State,Zip Code,Status,Priority,Appointment,Program Name,Consultant Name,Special Instructions
2026-01-01,A1,2026-01-10,RAJ Holdings LLC,RAJ DBA,John,Restaurant,1 Main St,Dallas,TX,75001,Work In Progress,High,2026-01-08,ProgA,ConA,Protection class - 9
2026-01-02,A2,2026-01-11,Dore's Corner Tavern LLC,Dore DBA,Jane,Bar,2 Main St,Dallas,TX,75002,On Hold,Low,2026-01-09,ProgB,ConB,Contact Information: Sam, 2704016136, sam@example.com
"""
    r = client.post("/orders/import_csv", files={"file": ("sample.csv", csv_content)})
    assert r.status_code == 200
    assert r.json()["created"] == 2

    csv_content_2 = """Date Assigned,Assignment #,Due Date,Insured Name,DBA Name,Contact,Business Desc,Address,City,State,Zip Code,Status,Priority,Appointment,Program Name,Consultant Name,Special Instructions
2026-01-01,A1,2026-01-15,RAJ Holdings LLC,RAJ DBA,John,Restaurant,1 Main St,Dallas,TX,75001,Completed,High,2026-01-08,ProgA,ConA,Protection class - 10
"""
    r2 = client.post("/orders/import_csv", files={"file": ("sample2.csv", csv_content_2)})
    assert r2.json()["updated"] == 1

    orders = client.get("/orders").json()
    assert len(orders) == 2
    assert [o for o in orders if o["order_number"] == "A1"][0]["status"] == "Completed"

    view = client.post("/views", json={"name": "active", "filters": {"rules": [{"field": "status", "op": "eq", "value": "Active"}]}, "columns": ["order_number"], "sorts": []}).json()
    filtered = client.get(f"/orders?view_id={view['id']}").json()
    assert filtered == []

    order2 = [o for o in orders if o["order_number"] == "A2"][0]
    done = client.post(f"/orders/{order2['id']}/complete")
    assert done.status_code == 200

    exported = client.get("/orders/export_csv")
    assert "Assignment #" in exported.text
    assert "A2" in exported.text
