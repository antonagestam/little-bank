from dataclasses import dataclass
from lb.lb import BaseAccount

import enum


class PSP(enum.Enum):
    credit_card = "credit_card"
    gift_card = "gift_card"


# Problem: can we avoid hard coding accounts for each PSP?
# Answer: Yes!!
# We'll introduce separate system for each PSP! We'll:
# 1. Analyze main psp transactions
# 2. Analyze secondary psp transactions
# 3. Merge! :D
# This way we can setup individual rules per PSP.

# Question: are there design choices or helpers we can provide to make it easier to work
#           with a mix of single-phase and 2-phase PSPs?
class Account(BaseAccount):
    customer = "customer"
    reserved = "reserved"
    refunded = "refunded"
    bank = "bank"


@dataclass(frozen=True, slots=True)
class Transaction:
    value: int
    credit: Account
    debit: Account
    psp: PSP
