from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import replace
from decimal import Decimal
from enum import Enum
from typing import Callable
from typing import Final
from typing import Generator
from typing import Generic
from typing import Iterable
from typing import Iterator
from typing import Protocol
from typing import Sequence
from typing import TypeVar
from typing import final

from phantom.interval import Natural

T = TypeVar("T", bound=object, contravariant=True)

Predicate = Callable[[T], bool]


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


A_co = TypeVar("A_co", bound=BaseAccount, covariant=True)
N_co = TypeVar("N_co", int, Decimal, covariant=True)


class Transactable(Protocol[A_co, N_co]):
    @property
    @abstractmethod
    def value(self) -> N_co:
        ...

    @property
    @abstractmethod
    def credit(self) -> A_co:
        ...

    @property
    @abstractmethod
    def debit(self) -> A_co:
        ...


V_co = TypeVar("V_co", covariant=True)


class Metric(Protocol[V_co]):
    """A Metric is a function that extracts some value from a group of transactions."""

    def __call__(self, transactions: Iterable[Transactable], /) -> V_co:
        ...


class Credit(Metric[Natural]):
    def __init__(self, account: BaseAccount) -> None:
        self.account: Final = account

    def __call__(self, transactions: Iterable[Transactable], /) -> Natural:
        # Ignore because sum of Natural is Natural. Would be nice with support for that
        # in phantom-types.
        return sum(  # type: ignore[return-value]
            tx.value for tx in transactions if tx.credit is self.account
        )


class Debit(Metric[Natural]):
    def __init__(self, account: BaseAccount) -> None:
        self.account: Final = account

    def __call__(self, transactions: Iterable[Transactable], /) -> Natural:
        return sum(  # type: ignore[return-value]
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
    def __init__(
        self,
        routes: Sequence[tuple[A_co, A_co]],
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
class Rule(Generic[V_co]):
    """
    A rule is a combination of a metric and a predicate. A system can have many rules,
    and guarantees not to violate them by checking all rules in a pre-condition
    implemented in `__post_init__`.
    """

    code: str
    metric: Metric[V_co]
    predicate: Predicate[V_co]

    def __call__(self, transactions: Iterable[Transactable], /) -> bool:
        # mypy thinks self.predicate is a bool, there's an issue for this in mypy but
        # I can't find it currently.
        return self.predicate(  # type: ignore[no-any-return, operator]
            self.metric(transactions)
        )

    def __str__(self) -> str:
        return f"Rule(code={self.code})"


@dataclass(frozen=True, slots=True)
class InvalidSystem(ValueError):
    violated_rules: tuple[Rule, ...]


S = TypeVar("S", bound="System")
Txn = TypeVar("Txn", bound=Transactable)


@dataclass(frozen=True, slots=True)
class System(Generic[Txn]):
    transactions: tuple[Txn, ...]
    rules: tuple[Rule, ...] = ()

    def verify(self) -> Generator[Rule, None, bool]:
        intact = True
        for rule in self.rules:
            if not rule(self):
                intact = False
                yield rule
        return intact

    def __post_init__(self) -> None:
        if violated_rules := tuple(self.verify()):
            raise InvalidSystem(violated_rules=violated_rules)

    def __iter__(self) -> Iterator[Txn]:
        return iter(self.transactions)

    def append(self: S, *transactions: Txn) -> S:
        return replace(
            self,
            rules=self.rules,
            transactions=(*self.transactions, *transactions),
        )
