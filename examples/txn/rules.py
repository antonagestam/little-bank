from lb.lb import Rule, Balance, HasOnlyRoutes
from .schema import Account
from phantom.predicates.numeric import le, ge
from phantom.predicates.generic import equal, identical

# Customer account should never have positive balance.
customer_balance_le_zero = Rule(
    code="customer_overdrawn",
    metric=Balance(Account.customer),
    predicate=le(0),
)

# Reserved account should never have negative balance.
reserved_balance_ge_zero = Rule(
    code="reserved_overdrawn",
    metric=Balance(Account.reserved),
    predicate=ge(0),
)

# Captured account should never have negative balance.
bank_balance_ge_zero = Rule(
    code="bank_overdrawn",
    metric=Balance(Account.bank),
    predicate=ge(0),
)

# Refunded account should always balance to zero. This is an "analysis-only"
# or "through" account.
refunded_balance_zero = Rule(
    code="refunded_non_zero",
    metric=Balance(Account.refunded),
    predicate=equal(0),
)

# Disallow all routes not explicitly listed here.
legal_routes = Rule(
    code="illegal_route",
    metric=HasOnlyRoutes(
        (Account.customer, Account.reserved),
        (Account.reserved, Account.customer),
        (Account.reserved, Account.bank),
        (Account.bank, Account.refunded),
        (Account.refunded, Account.customer),
    ),
    predicate=identical(True),
)
