"""Deterministic dataset generator for Duka Electronics and the Mobile Money Agent Network."""

from __future__ import annotations

import numpy as np
import pandas as pd


def generate_duka_sales(
    seed: int = 2026,
    n: int = 1000,
    output_path: str = "duka_sales.csv",
) -> pd.DataFrame:
    """Generate the Duka Electronics synthetic sales dataset and write it to CSV."""
    rng = np.random.default_rng(seed)
    products = {
        "Phone": 15000,
        "Laptop": 65000,
        "Headphones": 2500,
        "Tablet": 28000,
        "Charger": 1200,
    }

    sales = pd.DataFrame({
        "order_id": range(1001, 1001 + n),
        "order_date": (
            pd.to_datetime("2026-01-01")
            + pd.to_timedelta(rng.integers(0, 180, n), unit="D")
        ),
        "branch": rng.choice(
            ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"],
            n,
            p=[0.4, 0.2, 0.15, 0.15, 0.1],
        ),
        "product": rng.choice(list(products), n),
        "quantity": rng.integers(1, 6, n),
        "channel": rng.choice(
            ["In-store", "Online", "Phone order"],
            n,
            p=[0.55, 0.35, 0.10],
        ),
    })
    sales["unit_price"] = sales["product"].map(products)
    sales.to_csv(output_path, index=False)
    return sales


def generate_agent_network(
    seed: int = 44,
    n: int = 600,
    agents_path: str = "agents.csv",
    txns_path: str = "agent_transactions.csv",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate the Mobile Money Agent Network register and raw transaction log."""
    rng = np.random.default_rng(seed)

    agents = pd.DataFrame({
        "agent_id": [f"AG{i:03d}" for i in range(1, 21)],
        "county": rng.choice(["Nairobi", "Kiambu", "Nakuru", "Mombasa", "Kisumu"], 20),
        "onboarded": pd.date_range("2024-01-01", periods=20, freq="MS").strftime("%Y-%m-%d"),
    })

    txns = pd.DataFrame({
        "txn_id": [f"TX{i:05d}" for i in range(1, n + 1)],
        "agent_id": rng.choice(agents["agent_id"], n),
        "txn_type": rng.choice(
            ["Deposit", "withdrawal", "DEPOSIT ", "Withdrawal", "deposit"], n
        ),
        "amount": rng.lognormal(7.5, 0.8, n).round(0).astype(str),
        "txn_date": (
            pd.to_datetime("2026-03-01")
            + pd.to_timedelta(rng.integers(0, 60, n), unit="D")
        ).strftime("%Y-%m-%d"),
    })

    idx = rng.choice(n, 30, replace=False)
    txns.loc[idx[:15], "amount"] = np.nan
    txns.loc[idx[15:20], "amount"] = "N/A"
    txns.loc[idx[20:25], "amount"] = "250000"
    txns.loc[idx[25:], "txn_date"] = txns.loc[idx[25:], "txn_date"].str.replace("-", "/")

    txns = pd.concat([txns, txns.sample(12, random_state=1)], ignore_index=True)
    txns.loc[rng.choice(len(txns), 8, replace=False), "agent_id"] = "AG099"

    agents.to_csv(agents_path, index=False)
    txns.to_csv(txns_path, index=False)
    return agents, txns


def generate_all() -> None:
    """Reproduce all project CSV files in the current working directory."""
    sales = generate_duka_sales()
    agents, txns = generate_agent_network()
    print(f"Generated duka_sales.csv:         {sales.shape}")
    print(f"Generated agents.csv:             {agents.shape}")
    print(f"Generated agent_transactions.csv: {txns.shape}")


if __name__ == "__main__":
    generate_all()
