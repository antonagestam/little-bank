from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
from unittest import TestCase

import pytest
from phantom.predicates.generic import equal
from phantom.predicates.generic import identical
from phantom.predicates.numeric import ge, le

from lb.lb import Balance
from lb.lb import BaseAccount
from lb.lb import HasRoutes, HasOnlyRoutes
from lb.lb import InvalidSystem
from lb.lb import Rule
from lb.lb import System
from lb.lb import SystemBalance


class Account(BaseAccount):
    customer = "customer"
    reserved = "reserved"
    captured = "captured"
    refunded = "refunded"


@dataclass(frozen=True, slots=True)
class Transaction:
    value: int
    credit: Account
    debit: Account


is_balanced = Rule(
    code="system_unbalanced",
    metric=SystemBalance(Account),
    predicate=equal(0),
)
disallow_route = Rule(
    code="illegal_transaction",
    metric=HasRoutes([(Account.customer, Account.captured)], bidirectional=True),
    predicate=identical(False),
)
disallow_negative_balance = Rule(
    code="negative_captured_balance",
    metric=Balance(Account.captured),
    predicate=ge(0),
)


def test_basics():
    authorized = System(
        transactions=(
            Transaction(200, credit=Account.customer, debit=Account.reserved),
        ),
    )
    assert Account.reserved.balance(authorized) == 200
    assert Account.reserved.credit(authorized) == 0
    assert Account.reserved.debit(authorized) == 200
    assert Account.customer.balance(authorized) == -200
    assert Account.customer.credit(authorized) == 200
    assert Account.customer.debit(authorized) == 0

    cancelled = System(
        transactions=(
            Transaction(200, credit=Account.customer, debit=Account.reserved),
            Transaction(200, credit=Account.reserved, debit=Account.customer),
        ),
    )
    assert Account.reserved.balance(cancelled) == 0
    assert Account.reserved.credit(cancelled) == 200
    assert Account.reserved.debit(cancelled) == 200
    assert Account.customer.balance(cancelled) == 0
    assert Account.customer.credit(cancelled) == 200
    assert Account.customer.debit(cancelled) == 200

    captured = System(
        transactions=(
            Transaction(100, credit=Account.customer, debit=Account.reserved),
            Transaction(100, credit=Account.customer, debit=Account.captured),
            Transaction(100, credit=Account.reserved, debit=Account.captured),
        ),
        rules=(is_balanced, disallow_negative_balance),
    )
    assert Account.reserved.balance(captured) == 0
    assert Account.customer.balance(captured) == -200
    assert Account.captured.balance(captured) == 200

    refunded = captured.append(
        Transaction(200, Account.captured, Account.refunded),
        Transaction(200, Account.refunded, Account.customer),
    )
    assert Account.captured.balance(refunded) == 0
    assert Account.customer.balance(refunded) == 0

    # Try to refund insufficient funds ...
    with pytest.raises(InvalidSystem) as exc_info:
        refunded.append(
            Transaction(1, Account.captured, Account.refunded),
        )

    (rule,) = exc_info.value.violated_rules
    assert rule is disallow_negative_balance


def test_has_routes():
    limited = System(transactions=tuple[Transaction](), rules=(disallow_route,))

    with pytest.raises(InvalidSystem) as exc_info:
        limited.append(Transaction(1, Account.captured, Account.customer))

    (rule,) = exc_info.value.violated_rules
    assert rule is disallow_route

    with pytest.raises(InvalidSystem) as exc_info:
        limited.append(Transaction(1, Account.customer, Account.captured))

    (rule,) = exc_info.value.violated_rules
    assert rule is disallow_route


realistic_system = System(
    transactions=(),
    rules=(
        # Customer account should never have positive balance.
        customer_overdrawn := Rule(
            code="customer_overdrawn",
            metric=Balance(Account.customer),
            predicate=le(0),
        ),
        # Reserved account should never have negative balance.
        reserved_overdrawn := Rule(
            code="reserved_overdrawn",
            metric=Balance(Account.reserved),
            predicate=ge(0),
        ),
        # Captured account should never have negative balance.
        captured_overdrawn := Rule(
            code="captured_overdrawn",
            metric=Balance(Account.captured),
            predicate=ge(0),
        ),
        # Refunded account should always balance to zero. This is an "analysis-only"
        # or "through" account.
        refunded_non_zero := Rule(
            code="refunded_non_zero",
            metric=Balance(Account.refunded),
            predicate=equal(0),
        ),
        # Disallow all routes not explicitly listed here.
        illegal_route := Rule(
            code="illegal_route",
            metric=HasOnlyRoutes(
                (Account.customer, Account.reserved),
                (Account.reserved, Account.customer),
                (Account.reserved, Account.captured),
                (Account.captured, Account.refunded),
                (Account.refunded, Account.customer),
            ),
            predicate=identical(True),
        ),
    ),
)

case = TestCase()

@pytest.mark.parametrize(
    "transactions, violated_rules",
    (
        # (
        #     (Transaction(1, Account.captured, Account.customer),),
        #     (illegal_route,)
        # ),
        (
            (Transaction(1, Account.customer, Account.captured),),
            (illegal_route,)
        ),
    )
)
def test_realistic_system_raises(
    transactions: Sequence[Transaction],
    violated_rules: Sequence[Rule],
):
    with pytest.raises(InvalidSystem) as exc_info:
        realistic_system.append(*transactions)

    case.assertCountEqual(exc_info.value.violated_rules, violated_rules)
