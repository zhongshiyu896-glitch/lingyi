"""PostgreSQL integration test for concurrent inspection over-limit protection (TASK-002F3)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import os
import threading
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep


@pytest.mark.postgresql
def test_inspect_concurrent_requests_do_not_overinspect() -> None:
    dsn = str(os.getenv("POSTGRES_TEST_DSN", "") or "").strip()
    if not dsn:
        pytest.skip("POSTGRES_TEST_DSN is not set; skipping PostgreSQL concurrency integration test")

    os.environ["APP_ENV"] = "test"
    os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
    os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

    engine = create_engine(dsn, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    seed = int(time.time() * 1000) % 1_000_000 + int(uuid4().int % 1_000_000)
    bom_id = 900_000_000 + seed
    bom_op_id = 910_000_000 + seed
    order_id = 920_000_000 + seed
    receipt_id = 930_000_000 + seed
    receipt_batch_no = f"RB-CONC-{seed}"

    old_main_session_local = main_module.SessionLocal

    def _override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ly_schema"))
        BomBase.metadata.create_all(bind=engine)
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=engine)
        AuditBase.metadata.create_all(bind=engine)

        with SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=bom_id,
                    bom_no=f"BOM-CONC-{seed}",
                    item_code="ITEM-CONC",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyBomOperation(
                    id=bom_op_id,
                    bom_id=bom_id,
                    process_name="外发裁剪",
                    sequence_no=1,
                    is_subcontract=True,
                    subcontract_cost_per_piece=Decimal("10"),
                )
            )
            session.add(
                LySubcontractOrder(
                    id=order_id,
                    subcontract_no=f"SC-CONC-{seed}",
                    supplier="SUP-CONC",
                    item_code="ITEM-CONC",
                    company="COMP-CONC",
                    bom_id=bom_id,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    subcontract_rate=Decimal("10"),
                    status="waiting_inspection",
                    resource_scope_status="ready",
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=receipt_id,
                    subcontract_id=order_id,
                    company="COMP-CONC",
                    receipt_batch_no=receipt_batch_no,
                    receipt_warehouse="WH-CONC",
                    item_code="ITEM-CONC",
                    received_qty=Decimal("100"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name=f"STE-REAL-CONC-{seed}",
                    idempotency_key=f"idem-receipt-conc-{seed}",
                )
            )
            session.commit()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[subcontract_db_dep] = _override_db
        main_module.SessionLocal = SessionLocal

        headers = {
            "X-LY-Dev-User": "inspect.concurrent",
            "X-LY-Dev-Roles": "Subcontract Manager",
        }
        payload_a = {
            "receipt_batch_no": receipt_batch_no,
            "idempotency_key": f"idem-inspect-conc-a-{seed}",
            "inspected_qty": "70",
            "rejected_qty": "0",
            "deduction_amount_per_piece": "0",
            "remark": "concurrency-a",
        }
        payload_b = {
            "receipt_batch_no": receipt_batch_no,
            "idempotency_key": f"idem-inspect-conc-b-{seed}",
            "inspected_qty": "70",
            "rejected_qty": "0",
            "deduction_amount_per_piece": "0",
            "remark": "concurrency-b",
        }

        with TestClient(app) as client_a, TestClient(app) as client_b:
            start_barrier = threading.Barrier(3)

            def _send(client: TestClient, payload: dict[str, str]):
                start_barrier.wait(timeout=5)
                return client.post(f"/api/subcontract/{order_id}/inspect", headers=headers, json=payload)

            with ThreadPoolExecutor(max_workers=2) as executor:
                fut_a = executor.submit(_send, client_a, payload_a)
                fut_b = executor.submit(_send, client_b, payload_b)
                start_barrier.wait(timeout=5)
                resp_a = fut_a.result(timeout=20)
                resp_b = fut_b.result(timeout=20)

        responses = [resp_a, resp_b]
        success_count = 0
        exceed_count = 0
        for response in responses:
            body = response.json()
            if response.status_code == 200 and body.get("code") == "0":
                success_count += 1
            elif response.status_code == 409 and body.get("code") == "SUBCONTRACT_INSPECTION_QTY_EXCEEDED":
                exceed_count += 1

        assert success_count == 1, f"expected exactly one success, got responses={[(r.status_code, r.json()) for r in responses]}"
        assert exceed_count == 1, f"expected one over-inspection rejection, got responses={[(r.status_code, r.json()) for r in responses]}"

        with SessionLocal() as session:
            total_inspected = (
                session.query(func.sum(LySubcontractInspection.inspected_qty))
                .filter(
                    LySubcontractInspection.subcontract_id == order_id,
                    LySubcontractInspection.receipt_batch_no == receipt_batch_no,
                )
                .scalar()
            )
            receipt_row = (
                session.query(LySubcontractReceipt)
                .filter(
                    LySubcontractReceipt.subcontract_id == order_id,
                    LySubcontractReceipt.receipt_batch_no == receipt_batch_no,
                )
                .first()
            )

        assert receipt_row is not None
        assert Decimal(str(total_inspected or "0")) <= Decimal(str(receipt_row.received_qty or "0"))
    finally:
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        main_module.SessionLocal = old_main_session_local
        with SessionLocal() as cleanup_session:
            cleanup_session.query(LySubcontractInspection).filter(LySubcontractInspection.subcontract_id == order_id).delete()
            cleanup_session.query(LySubcontractReceipt).filter(LySubcontractReceipt.id == receipt_id).delete()
            cleanup_session.query(LySubcontractOrder).filter(LySubcontractOrder.id == order_id).delete()
            cleanup_session.query(LyBomOperation).filter(LyBomOperation.id == bom_op_id).delete()
            cleanup_session.query(LyApparelBom).filter(LyApparelBom.id == bom_id).delete()
            cleanup_session.commit()
        engine.dispose()
