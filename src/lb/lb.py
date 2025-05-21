from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import replace
from decimal import Decimal
from enum import Enum
from typing import Final
from typing import Protocol
from typing import final

from phantom.interval import Natural

type Predicate[T: object] = Callable[[T], bool]


class BaseAccount(Enum):
    @property
    def credit(self) -> Credit:
        return Credit(self)

    @property
    def debit(self) -> Debit:
        return Debit(self)

    @property
    def balance(self) -> Balance:
        return Balance(self)


class Transactable[A: BaseAccount, N: int | Decimal](Protocol):
    @property
    @abstractmethod
    def value(self) -> N: ...
    @property
    @abstractmethod
    def credit(self) -> A: ...
    @property
    @abstractmethod
    def debit(self) -> A: ...


class Metric[V](Protocol):
    """A Metric is a function that extracts some value from a group of transactions."""

    def __call__(self, transactions: Iterable[Transactable], /) -> V: ...


class Credit(Metric[Natural]):
    def __init__(self, account: BaseAccount) -> None:
        self.account: Final = account

    def __call__(self, transactions: Iterable[Transactable], /) -> Natural:
        # Ignore because sum of Natural is Natural. Would be nice with support for that
        # in phantom-types.
        return sum(  # type: ignore[no-any-return]
            tx.value for tx in transactions if tx.credit is self.account
        )


class Debit(Metric[Natural]):
    def __init__(self, account: BaseAccount) -> None:
        self.account: Final = account

    def __call__(self, transactions: Iterable[Transactable], /) -> Natural:
        return sum(  # type: ignore[no-any-return]
            tx.value for tx in transactions if tx.debit is self.account
        )


class Balance(Metric[int]):
    def __init__(self, account: BaseAccount) -> None:
        self.credit: Final = Credit(account)
        self.debit: Final = Debit(account)

    def __call__(self, transactions: Iterable[Transactable], /) -> int:
        return self.debit(transactions) - self.credit(transactions)


class SystemBalance(Metric[int]):
    def __init__(self, accounts: Iterable[BaseAccount]) -> None:
        self.balances: Final = tuple(Balance(account) for account in accounts)

    def __call__(self, transactions: Iterable[Transactable], /) -> int:
        return sum(balance(transactions) for balance in self.balances)


class HasRoutes(Metric[bool]):
    def __init__[A: BaseAccount](
        self,
        routes: Sequence[tuple[A, A]],
        bidirectional: bool = False,
    ) -> None:
        self.routes: Final = routes
        self.bidirectional: Final = bidirectional

    def __call__(self, transactions: Iterable[Transactable], /) -> bool:
        for transaction in transactions:
            if (transaction.credit, transaction.debit) in self.routes or (
                self.bidirectional
                and (transaction.debit, transaction.credit) in self.routes
            ):
                return True
        return False


@final
@dataclass(frozen=True, slots=True)
class Rule[V]:
    """
    A rule is a combination of a metric and a predicate. A system can have many rules,
    and guarantees not to violate them by checking all rules in a pre-condition
    implemented in `__post_init__`.
    """

    code: str
    metric: Metric[V]
    predicate: Predicate[V]

    def __call__(self, transactions: Iterable[Transactable], /) -> bool:
        return self.predicate(self.metric(transactions))

    def __str__(self) -> str:
        return f"Rule(code={self.code})"


@dataclass(frozen=True, slots=True)
class InvalidSystem(ValueError):
    violated_rules: tuple[Rule, ...]


@dataclass(frozen=True, slots=True)
class System[Txn: Transactable]:
    transactions: tuple[Txn, ...]
    rules: tuple[Rule, ...] = ()

    def verify(self) -> Iterator[Rule]:
        for rule in self.rules:
            if not rule(self):
                yield rule

    def __post_init__(self) -> None:
        if violated_rules := tuple(self.verify()):
            raise InvalidSystem(violated_rules=violated_rules)

    def __iter__(self) -> Iterator[Txn]:
        return iter(self.transactions)

    def append[S: System](self: S, *transactions: Txn) -> S:
        return replace(
            self,
            rules=self.rules,
            transactions=(*self.transactions, *transactions),
        )
