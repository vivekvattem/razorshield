from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.base import Base
from app.db.session import Database
from app.main import create_app
from app.models import Customer, Merchant, Order, ReturnRequest


def make_order_graph(session):  # type: ignore[no-untyped-def]
    merchant = Merchant(external_id="merchant-1", name="Merchant")
    session.add(merchant)
    session.flush()
    customer = Customer(merchant_id=merchant.id, external_id="customer-1")
    session.add(customer)
    session.flush()
    order = Order(
        merchant_id=merchant.id,
        customer_id=customer.id,
        external_id="order-1",
        ordered_at=datetime.now(UTC),
        order_value_paise=12500,
        product_category="electronics",
    )
    session.add(order)
    session.flush()
    return merchant, customer, order


def test_all_model_tables_are_registered() -> None:
    expected = {
        "merchants",
        "customers",
        "orders",
        "return_requests",
        "identity_links",
        "model_versions",
        "policy_versions",
        "risk_assessments",
        "cases",
        "analyst_decisions",
        "audit_events",
    }
    assert expected.issubset(Base.metadata.tables)


def test_return_idempotency_is_unique(session) -> None:
    merchant, customer, order = make_order_graph(session)
    session.add_all(
        [
            ReturnRequest(
                merchant_id=merchant.id,
                customer_id=customer.id,
                order_id=order.id,
                external_id="return-1",
                event_time=datetime.now(UTC),
                reason_code="SIZE",
                requested_amount_paise=1000,
                idempotency_key="same-key",
            ),
            ReturnRequest(
                merchant_id=merchant.id,
                customer_id=customer.id,
                order_id=order.id,
                external_id="return-2",
                event_time=datetime.now(UTC),
                reason_code="SIZE",
                requested_amount_paise=1000,
                idempotency_key="same-key",
            ),
        ]
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_order_value_constraint_is_enforced(session) -> None:
    merchant, customer, _ = make_order_graph(session)
    session.add(
        Order(
            merchant_id=merchant.id,
            customer_id=customer.id,
            external_id="negative-order",
            ordered_at=datetime.now(UTC),
            order_value_paise=-1,
            product_category="electronics",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_transaction_rolls_back_after_failure(database: Database) -> None:
    with pytest.raises(IntegrityError):
        with database.transaction() as session:
            session.add(Merchant(external_id="duplicate", name="First"))
            session.flush()
            session.add(Merchant(external_id="duplicate", name="Second"))
            session.flush()
    with database.transaction() as session:
        session.add(Merchant(external_id="after-rollback", name="Recovered"))


def test_no_tables_created_by_application_factory(tmp_path) -> None:  # type: ignore[no-untyped-def]
    database_url = f"sqlite:///{tmp_path / 'startup.db'}"
    app = create_app(Settings(environment="test", database_url=database_url))
    try:
        assert inspect(app.state.database.engine).get_table_names() == []
    finally:
        app.state.database.engine.dispose()
