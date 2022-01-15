from .system import Account, Transaction, base_system, PSP


def process_transactions():
    ...


def initiate_purchase():
    system = base_system.append(
        Transaction(
            value=250,
            psp=PSP.credit_card,
            debit=Account.customer,
            credit=Account.reserved,
        ),
        Transaction(
            value=50,
            psp=PSP.gift_card,
            debit=Account.customer,
            credit=Account.bank,
        )
    )
