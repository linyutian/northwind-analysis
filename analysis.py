"""Answer three Northwind business questions with charts and tables.

Run as a script to write figures to ``figures/`` and tables to
``outputs/``.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# Paths are relative to this file, so the script runs from any directory.
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Northwind Database.xlsx"
FIG = ROOT / "figures"
OUT = ROOT / "outputs"
# Northwind has no cost data; assumed gross margin for the Q2 profit test.
MARGIN = 0.30


def load_sales(path):
    """Load order lines joined with order dates and customer details.

    Args:
        path (str | pathlib.Path): Northwind Excel workbook.

    Returns:
        pandas.DataFrame: One row per order line with ``OrderDate``,
        ``CompanyName``, ``Country`` and ``Revenue`` (USD, after
        discount).
    """
    sheets = pd.read_excel(path, sheet_name=None)
    orders = sheets["Orders"]
    details = sheets["Orders Details"]
    customers = sheets["Customers"][["CustomerID", "CompanyName", "Country"]]
    sales = details.merge(orders[["OrderID", "CustomerID", "OrderDate"]], on="OrderID")
    sales = sales.merge(customers, on="CustomerID")
    sales["Revenue"] = sales["UnitPrice"] * sales["Quantity"] * (1 - sales["Discount"])
    return sales


def market_growth(sales):
    """Compare Jan-Apr revenue by customer country, 1997 vs 1998.

    Writes ``figures/q1_market_growth.png``,
    ``figures/q1_market_change.png`` and
    ``outputs/q1_market_growth.csv``; all directories must exist.

    Args:
        sales (pandas.DataFrame): Order lines from ``load_sales``.

    Returns:
        pandas.DataFrame: One row per country, sorted by 1998 revenue
        ascending, with ``1997`` and ``1998`` revenue (USD),
        ``Change`` (USD), ``GrowthPct`` (NaN if 1997 revenue is 0),
        ``Rank1997`` and ``Rank1998`` (1 = largest market) and
        ``RankChange`` (positive = moved up).
    """
    # 1998 data stops in early May, so compare the same Jan-Apr window each year.
    window = sales[sales["OrderDate"].dt.month <= 4]
    by_year = window.pivot_table(
        index="Country",
        columns=window["OrderDate"].dt.year,
        values="Revenue",
        aggfunc="sum",
        fill_value=0,
    )[[1997, 1998]]
    by_year["Change"] = by_year[1998] - by_year[1997]
    by_year["GrowthPct"] = by_year["Change"] / by_year[1997].where(by_year[1997] > 0) * 100
    by_year["Rank1997"] = by_year[1997].rank(ascending=False, method="min").astype(int)
    by_year["Rank1998"] = by_year[1998].rank(ascending=False, method="min").astype(int)
    by_year["RankChange"] = by_year["Rank1997"] - by_year["Rank1998"]
    by_year = by_year.sort_values(1998)

    fig, ax = plt.subplots(figsize=(9, 8))
    y = range(len(by_year))
    ax.barh([i + 0.2 for i in y], by_year[1997] / 1000, height=0.4, label="Jan-Apr 1997", color="#9bb7d4")
    ax.barh([i - 0.2 for i in y], by_year[1998] / 1000, height=0.4, label="Jan-Apr 1998", color="#1f4e79")
    ax.set_yticks(list(y), by_year.index)
    ax.set_xlabel("Revenue (USD thousands)")
    ax.set_title("Revenue by customer country, Jan-Apr 1997 vs Jan-Apr 1998")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "q1_market_growth.png", dpi=150)
    plt.close(fig)

    # Rank markets by dollar change so gainers and decliners separate
    # systematically; with many countries, keep only the 15 at each end.
    change = by_year.sort_values("Change")
    if len(change) > 30:
        change = pd.concat([change.head(15), change.tail(15)])
    fig, ax = plt.subplots(figsize=(9, 8))
    colors = ["#2e7d32" if c >= 0 else "#c62828" for c in change["Change"]]
    ax.barh(change.index, change["Change"] / 1000, color=colors)
    for i, (_, row) in enumerate(change.iterrows()):
        pct = "new" if pd.isna(row["GrowthPct"]) else f"{row['GrowthPct']:+.0f}%"
        label = f"  {pct}, rank #{int(row['Rank1997'])} → #{int(row['Rank1998'])}  "
        ax.text(row["Change"] / 1000, i, label, va="center", fontsize=8,
                ha="left" if row["Change"] >= 0 else "right")
    ax.axvline(0, color="black", linewidth=0.8)
    # Leave room on both sides for the text labels.
    lo, hi = min(change["Change"].min(), 0) / 1000, max(change["Change"].max(), 0) / 1000
    pad = 0.5 * (hi - lo)
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_xlabel("Change in revenue, Jan-Apr 1998 vs Jan-Apr 1997 (USD thousands)")
    ax.set_title("Revenue change by customer country (labels: % change, revenue rank move)")
    fig.tight_layout()
    fig.savefig(FIG / "q1_market_change.png", dpi=150)
    plt.close(fig)

    by_year.sort_values("Change", ascending=False).round(1).to_csv(OUT / "q1_market_growth.csv")
    return by_year


def discount_effect(sales):
    """Test whether each discount level pays for its extra volume.

    The quantity index is units sold divided by expected units, where
    expected units are each line's product average quantity on
    undiscounted lines. Break-even indexes are ``1 / (1 - d)`` for
    revenue and ``MARGIN / (MARGIN - d)`` for gross profit, with ``d``
    the level's average discount. Writes
    ``figures/q2_discount_economics.png`` and
    ``outputs/q2_discount_effect.csv``; both directories must exist.

    Args:
        sales (pandas.DataFrame): Order lines from ``load_sales``;
            not modified.

    Returns:
        pandas.DataFrame: One row per discount level with ``Lines``,
        ``AvgDiscount`` (fraction), ``Units``, ``ExpectedUnits``,
        ``ExtraUnits``, ``QtyIndex``, ``BreakEvenRevenue``,
        ``BreakEvenProfit`` (inf if the discount exceeds ``MARGIN``),
        ``DiscountCost`` (USD), ``CostPerExtraUnit`` (USD),
        ``AvgListPrice`` (USD per unit) and ``CostPctOfPrice``
        (cost per extra unit as a percent of its full price).
    """
    bins = [-0.001, 0, 0.05, 0.10, 0.15, 0.20, 0.25]
    labels = ["0%", "1-5%", "6-10%", "11-15%", "16-20%", "21-25%"]
    sales = sales.copy()
    # Excel stores e.g. 0.05 as 0.0500001, which would spill into the next bin.
    sales["Discount"] = sales["Discount"].round(2)
    sales["DiscountLevel"] = pd.cut(sales["Discount"], bins=bins, labels=labels)
    sales["ListValue"] = sales["UnitPrice"] * sales["Quantity"]
    sales["DiscountCost"] = sales["ListValue"] - sales["Revenue"]
    # Expected units = what the same product sells per line at full price,
    # so a discount level is not credited for selling naturally bulkier products.
    base_qty = sales[sales["Discount"] == 0].groupby("ProductID")["Quantity"].mean()
    sales["ExpectedUnits"] = sales["ProductID"].map(base_qty)

    table = sales.groupby("DiscountLevel", observed=True).agg(
        Lines=("OrderID", "size"),
        AvgDiscount=("Discount", "mean"),
        Units=("Quantity", "sum"),
        ExpectedUnits=("ExpectedUnits", "sum"),
        ListValue=("ListValue", "sum"),
        DiscountCost=("DiscountCost", "sum"),
    )
    table["ExtraUnits"] = table["Units"] - table["ExpectedUnits"]
    table["QtyIndex"] = table["Units"] / table["ExpectedUnits"]
    table["BreakEvenRevenue"] = 1 / (1 - table["AvgDiscount"])
    table["BreakEvenProfit"] = (MARGIN / (MARGIN - table["AvgDiscount"])).where(
        table["AvgDiscount"] < MARGIN, float("inf")
    )
    table["CostPerExtraUnit"] = table["DiscountCost"] / table["ExtraUnits"].where(table["ExtraUnits"] > 0)
    table["AvgListPrice"] = table["ListValue"] / table["Units"]
    table["CostPctOfPrice"] = table["CostPerExtraUnit"] / table["AvgListPrice"] * 100
    table = table.drop(columns="ListValue")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    x = list(range(len(table)))
    names = table.index.astype(str)
    cap = 3.5
    ax1.bar(x, table["QtyIndex"], color="#1f4e79", label="Actual quantity index")
    ax1.plot(x, table["BreakEvenRevenue"], "o--", color="#7f7f7f", label="Needed to break even on revenue")
    profit = table["BreakEvenProfit"].clip(upper=cap)
    ax1.plot(x, profit, "s-", color="#c62828", label=f"Needed to break even on profit ({MARGIN:.0%} margin)")
    for i, (actual, needed) in enumerate(zip(table["QtyIndex"], table["BreakEvenProfit"])):
        ax1.text(i, actual / 2, f"{actual:.2f}", ha="center", color="white", fontsize=9)
        if needed > cap:
            ax1.annotate(f"needs {needed:.1f}" if needed < float("inf") else "never", (i, cap),
                         xytext=(0, -14), textcoords="offset points", ha="center", color="#c62828", fontsize=9)
    ax1.set_xticks(x, names)
    ax1.set_ylim(0, cap + 0.2)
    ax1.set_xlabel("Discount level")
    ax1.set_ylabel("Units sold ÷ units expected at full price")
    ax1.set_title("Extra volume won vs. extra volume needed")
    ax1.legend(loc="upper left", fontsize=9)

    # 0% has no extra units, so it has no cost per extra unit.
    pct = table["CostPctOfPrice"].dropna()
    ax2.bar(pct.index.astype(str), pct, color="#1f4e79")
    ax2.axhline(100, color="#c62828", linewidth=1.5, label="100% = discount costs as much as the unit sells for")
    for i, v in enumerate(pct):
        ax2.text(i, v + 2, f"{v:.0f}%", ha="center", fontsize=9)
    ax2.set_ylim(0, 120)
    ax2.set_xlabel("Discount level")
    ax2.set_ylabel("Discount cost per extra unit, % of its full price")
    ax2.set_title("What each extra unit costs in discounts")
    ax2.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "q2_discount_economics.png", dpi=150)
    plt.close(fig)

    table.round(2).to_csv(OUT / "q2_discount_effect.csv")
    return table


def customer_concentration(sales):
    """Rank customers by revenue and compute cumulative revenue share.

    Writes ``figures/q3_customer_concentration.png`` and
    ``outputs/q3_customer_concentration.csv``; both directories must
    exist.

    Args:
        sales (pandas.DataFrame): Order lines from ``load_sales``.

    Returns:
        pandas.DataFrame: Indexed by company name, highest revenue
        first, with ``Revenue`` (USD), ``SharePct`` and
        ``CumulativePct`` (percent of total revenue).
    """
    by_customer = sales.groupby("CompanyName")["Revenue"].sum().sort_values(ascending=False)
    share = by_customer / by_customer.sum() * 100
    cumulative = share.cumsum()

    fig, ax = plt.subplots(figsize=(10, 5))
    ranks = range(1, len(by_customer) + 1)
    ax.bar(ranks, by_customer / 1000, color="#1f4e79")
    ax.set_xlabel("Customers ranked by revenue")
    ax.set_ylabel("Revenue (USD thousands)")
    ax2 = ax.twinx()
    ax2.plot(ranks, cumulative, color="#c0504d", linewidth=2)
    ax2.set_ylabel("Cumulative share of revenue (%)")
    ax2.set_ylim(0, 105)
    for n in (3, 10):
        top = cumulative.iloc[n - 1]
        ax2.axhline(top, color="#7f7f7f", linestyle=":", linewidth=1.2)
        ax2.plot(n, top, "o", color="#c0504d")
        ax2.text(len(by_customer), top + 1.5, f"Top {n} customers: {top:.0f}% of revenue", fontsize=9, ha="right")
    ax.set_title("Customer revenue concentration (Jul 1996 - May 1998)")
    fig.tight_layout()
    fig.savefig(FIG / "q3_customer_concentration.png", dpi=150)
    plt.close(fig)

    table = pd.DataFrame({"Revenue": by_customer, "SharePct": share, "CumulativePct": cumulative})
    table.round(2).to_csv(OUT / "q3_customer_concentration.csv")
    return table


def main():
    """Run all three analyses and write the headline summary.

    Args:
        None.

    Returns:
        None. Writes figures, CSVs and ``outputs/summary.json``, and
        prints the summary.
    """
    FIG.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    sales = load_sales(DATA)
    growth = market_growth(sales)
    discount = discount_effect(sales)
    concentration = customer_concentration(sales)

    n_customers = len(concentration)
    top20 = round(n_customers * 0.2)
    top_growth = growth.sort_values("Change", ascending=False).head(3)
    deep = discount.loc[["16-20%", "21-25%"], "DiscountCost"].sum()
    summary = {
        "total_revenue": round(sales["Revenue"].sum(), 2),
        "orders": int(sales["OrderID"].nunique()),
        "customers_with_orders": n_customers,
        "first_order_date": str(sales["OrderDate"].min().date()),
        "last_order_date": str(sales["OrderDate"].max().date()),
        "q1_revenue_jan_apr_1997": round(growth[1997].sum(), 2),
        "q1_revenue_jan_apr_1998": round(growth[1998].sum(), 2),
        "q1_total_growth_pct": round((growth[1998].sum() / growth[1997].sum() - 1) * 100, 1),
        "q1_top3_markets": list(top_growth.index),
        "q1_top3_share_of_growth_pct": round(top_growth["Change"].sum() / growth["Change"].sum() * 100, 1),
        "q2_total_discount_cost": round(discount["DiscountCost"].sum(), 2),
        "q2_discount_cost_pct_of_revenue": round(discount["DiscountCost"].sum() / sales["Revenue"].sum() * 100, 1),
        "q2_discount_cost_above_15pct": round(deep, 2),
        "q2_above_15pct_share_of_discount_cost_pct": round(deep / discount["DiscountCost"].sum() * 100, 1),
        "q2_assumed_margin": MARGIN,
        "q3_top3_share_pct": round(concentration["SharePct"].head(3).sum(), 1),
        "q3_top10_share_pct": round(concentration["SharePct"].head(10).sum(), 1),
        "q3_top20pct_customers": top20,
        "q3_top20pct_share_pct": round(concentration["SharePct"].head(top20).sum(), 1),
        "q3_bottom_half_customers": n_customers // 2,
        "q3_bottom_half_share_pct": round(concentration["SharePct"].tail(n_customers // 2).sum(), 1),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
