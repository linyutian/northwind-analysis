import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DATA = Path("Northwind Database.xlsx")
FIG = Path("figures")
OUT = Path("outputs")


def load_sales(path):
    sheets = pd.read_excel(path, sheet_name=None)
    orders = sheets["Orders"]
    details = sheets["Orders Details"]
    customers = sheets["Customers"][["CustomerID", "CompanyName", "Country"]]
    sales = details.merge(orders[["OrderID", "CustomerID", "OrderDate"]], on="OrderID")
    sales = sales.merge(customers, on="CustomerID")
    sales["Revenue"] = sales["UnitPrice"] * sales["Quantity"] * (1 - sales["Discount"])
    return sales


def market_growth(sales):
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

    by_year.sort_values("Change", ascending=False).round(1).to_csv(OUT / "q1_market_growth.csv")
    return by_year


def discount_effect(sales):
    bins = [-0.001, 0, 0.05, 0.10, 0.15, 0.20, 0.25]
    labels = ["0%", "1-5%", "6-10%", "11-15%", "16-20%", "21-25%"]
    sales = sales.copy()
    # Excel stores e.g. 0.05 as 0.0500001, which would spill into the next bin.
    sales["DiscountLevel"] = pd.cut(sales["Discount"].round(2), bins=bins, labels=labels)
    sales["ListValue"] = sales["UnitPrice"] * sales["Quantity"]
    sales["DiscountCost"] = sales["ListValue"] - sales["Revenue"]
    # Compare each line to the same product's undiscounted average quantity,
    # so a discount level is not credited for selling naturally bulkier products.
    base_qty = sales[sales["Discount"] == 0].groupby("ProductID")["Quantity"].mean()
    sales["QtyIndex"] = sales["Quantity"] / sales["ProductID"].map(base_qty)

    table = sales.groupby("DiscountLevel", observed=True).agg(
        Lines=("OrderID", "size"),
        AvgQuantity=("Quantity", "mean"),
        QtyIndex=("QtyIndex", "mean"),
        DiscountCost=("DiscountCost", "sum"),
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(table.index.astype(str), table["AvgQuantity"], color="#1f4e79")
    for bar, n in zip(bars, table["Lines"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5, f"n={n}", ha="center", fontsize=9)
    ax.set_xlabel("Discount level")
    ax.set_ylabel("Average units per order line")
    ax.set_title("Average quantity per order line by discount level")
    fig.tight_layout()
    fig.savefig(FIG / "q2_discount_quantity.png", dpi=150)
    plt.close(fig)

    table.round(2).to_csv(OUT / "q2_discount_effect.csv")
    return table


def customer_concentration(sales):
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
    ax.set_title("Customer revenue concentration (Jul 1996 - May 1998)")
    fig.tight_layout()
    fig.savefig(FIG / "q3_customer_concentration.png", dpi=150)
    plt.close(fig)

    table = pd.DataFrame({"Revenue": by_customer, "SharePct": share, "CumulativePct": cumulative})
    table.round(2).to_csv(OUT / "q3_customer_concentration.csv")
    return table


def main():
    FIG.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    sales = load_sales(DATA)
    growth = market_growth(sales)
    discount = discount_effect(sales)
    concentration = customer_concentration(sales)

    n_customers = len(concentration)
    top20 = round(n_customers * 0.2)
    summary = {
        "total_revenue": round(sales["Revenue"].sum(), 2),
        "orders": int(sales["OrderID"].nunique()),
        "customers_with_orders": n_customers,
        "q1_total_growth_pct": round((growth[1998].sum() / growth[1997].sum() - 1) * 100, 1),
        "q2_total_discount_cost": round(discount["DiscountCost"].sum(), 2),
        "q3_top10_share_pct": round(concentration["SharePct"].head(10).sum(), 1),
        "q3_top20pct_customers": top20,
        "q3_top20pct_share_pct": round(concentration["SharePct"].head(top20).sum(), 1),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
