<h1 align=center>little-bank</h1>

<p align=center>
    <a href=https://github.com/antonagestam/little-bank/actions?query=workflow%3ACI+branch%3Amain><img src=https://github.com/antonagestam/little-bank/workflows/CI/badge.svg alt="CI Build Status"></a>
</p>

Little Bank is a framework for analyzing financial transactions.

#### Design goals

- All analysis should be a matter of summarizing credit, debit or balance of an account
  in a system. The intention is to reduce bugs by making all analysis use the same
  numerical implementation.
- Allow defining rules for a system in a declarative way.
- Disallow mutation. The design encourages immutable, append-only transactions.
- All operations that update the system are very similar: appending transactions which
  automatically verifies all defined rules, and persisting the new transactions. This
  allows centralizing code that saves transactions to a single place.
