# Jasmine Ledger — an independently auditable trading track record

This repository is an **append-only, hash-chained** daily record of a live trading
account's balance. It exists to prove one claim, honestly and without trust:

> the account returned ~1% per month, for 6 consecutive months, on real money.

## How to audit it yourself
```
git clone <this repo>
python3 jasmine_ledger.py verify   # re-walks the chain; fails loudly if any past day was edited
python3 jasmine_ledger.py report   # month-by-month returns vs the +1% target
```
Each record's hash covers the previous record's hash, so **no historical day can be
changed** without breaking every hash after it. Because each seal is a **public git
commit**, GitHub's own timestamps witness *when* each day was recorded — the history
**cannot be back-dated or fabricated after the fact**.

## Ground truth
The balances are pulled read-only from the live MT4 terminal (Pepperstone Razor,
account on file). Broker-issued account statements are archived under `statements/`
as the independent source of truth; this chain proves those numbers were recorded
day-by-day, in order, and never altered.

*Built for Jasmine.*

---
**Status:** repository initialised 2026-07-04. Genesis (first real seal) scheduled 16 Jul 2026. No trading data yet.
