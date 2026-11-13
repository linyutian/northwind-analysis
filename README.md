# Northwind Business Analysis (15.561 HW3)

Three business questions answered from the Northwind database. The results are on the webpage (`index.html`).

## Reproduce

Requires Python 3.14 and [uv](https://docs.astral.sh/uv/) (or plain `pip`).

```bash
uv venv --python 3.14
uv pip install -r requirements.txt
.venv/bin/python analysis.py
```

`analysis.py` reads `Northwind Database.xlsx` and writes:

| Output | Used for |
|---|---|
| `figures/q1_market_growth.png`, `figures/q1_market_change.png`, `outputs/q1_market_growth.csv` | Q1: country markets growing/declining (revenue, $ change, % change, rank move) |
| `figures/q2_discount_quantity.png`, `outputs/q2_discount_effect.csv` | Q2: do discounts pay off? |
| `figures/q3_customer_concentration.png`, `outputs/q3_customer_concentration.csv` | Q3: customer concentration risk |
| `outputs/summary.json` | Headline numbers quoted on the webpage |

## Definitions
- **Revenue** = `UnitPrice × Quantity × (1 − Discount)` per order line.
- **Q1 window**: orders run 1996-07-04 to 1998-05-06, so growth compares Jan–Apr 1997 with Jan–Apr 1998. Rank 1 = largest market in that period. The change chart shows all markets, or only the top and bottom 15 when there are more than 30.
- **Q2 discount levels**: discounts are rounded to 2 decimals before binning, because Excel stores 0.05 as 0.0500001. *Quantity index* = line quantity ÷ that product's average undiscounted quantity.
- **Q3**: revenue per customer over the full period (Jul 1996 – May 1998).

Check: total revenue is $1,265,793.04 across 830 orders.
