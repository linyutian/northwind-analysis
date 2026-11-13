# Northwind Business Analysis (15.561 HW3)

Three business questions answered from the Northwind database:

1. Which country markets are growing or declining?
2. Do discounts pay for the extra volume they bring?
3. How dependent is the business on a few large customers?

- **Webpage:** https://linyutian.github.io/northwind-analysis/ (source: `index.html`)
- **Code:** `analysis.py` (Python only)
- **Data:** `Northwind Database.xlsx` (included)

## Reproduce

Requires Python 3.14. Clone the repo, then use either option.

**With [uv](https://docs.astral.sh/uv/):**

```bash
git clone https://github.com/linyutian/northwind-analysis.git
cd northwind-analysis
uv venv --python 3.14
uv pip install -r requirements.txt
.venv/bin/python analysis.py
```

**With plain pip:**

```bash
git clone https://github.com/linyutian/northwind-analysis.git
cd northwind-analysis
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python analysis.py
```

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.

The script runs in a few seconds and prints `summary.json`. It finds the data file and output folders relative to itself, so it can be run from any directory. `requirements.txt` pins exact package versions, so a fresh install reproduces the committed figures and CSVs byte-for-byte (tested on a clean clone).

## Outputs

| Output | Webpage section |
|---|---|
| `figures/q1_market_growth.png`, `figures/q1_market_change.png`, `outputs/q1_market_growth.csv` | Q1: revenue, $ change, % change and rank move by country |
| `figures/q2_discount_economics.png`, `outputs/q2_discount_effect.csv` | Q2: quantity index vs. break-even; cost per extra unit as % of full price |
| `figures/q3_customer_concentration.png`, `outputs/q3_customer_concentration.csv` | Q3: revenue and cumulative share by customer |
| `outputs/summary.json` | Headline numbers quoted in the text (totals, growth shares, discount spend, customer shares) |

## Definitions

- **Revenue** = `UnitPrice × Quantity × (1 − Discount)` per order line.
- **Q1 window:** orders run 1996-07-04 to 1998-05-06. Jan–Apr is the only full period present in both 1997 and 1998, so growth compares Jan–Apr 1997 with Jan–Apr 1998. Rank 1 = largest market in that period. The change chart shows all markets, or only the top and bottom 15 when there are more than 30.
- **Q2 discount levels:** discounts are rounded to 2 decimals before binning, because Excel stores 0.05 as 0.0500001.
  - *Expected units:* for each order line, that product's average quantity on undiscounted lines.
  - *Quantity index* = units sold ÷ expected units.
  - *Break-even index:* revenue `1/(1−d)`; profit `m/(m−d)`, with an assumed gross margin `m = 30%`. Set by `MARGIN` in `analysis.py`; Northwind has no cost data.
  - *Cost per extra unit* = discount cost ÷ (units sold − expected units), shown as a % of the average full unit price.
- **Q3:** revenue per customer over the full period (Jul 1996 – May 1998).

## Sanity check

Total revenue is $1,265,793.04 across 830 orders and 89 customers.
