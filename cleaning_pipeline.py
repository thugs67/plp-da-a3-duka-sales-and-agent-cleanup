"""Reusable data-cleaning pipeline module for the Mobile Money Agent Network."""

from __future__ import annotations

import numpy as np
import pandas as pd


def clean_agent_data(
    txns: pd.DataFrame,
    agents: pd.DataFrame,
    drop_missing_amounts: bool = True,
    drop_extreme_outliers: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """Clean agent transactions and merge with the registered agent register.

    Applies deterministic, rule-based cleaning steps without hard-coded row indices:
      1. **Uniqueness:** Drops exact duplicate rows and resolves duplicate `txn_id`s
         by preferring records linked to a registered `agent_id`.
      2. **Consistency:** Strips whitespace and standardizes `txn_type` into strictly
         `"Deposit"` and `"Withdrawal"`, guarding against `NaN` and `"N/A"` strings.
      3. **Validity & Types:** Strips formatting artifacts and coerces `amount` to
         `float64`, and parses mixed date formats (`YYYY-MM-DD`, `YYYY/MM/DD`) into
         `datetime64[ns]`.
      4. **Completeness:** Flags missing or non-positive amounts (`is_missing_or_invalid_amount`)
         without imputing synthetic values, and optionally filters them out.
      5. **Outliers (IQR):** Flags standard ($Q_3 + 1.5 \\times \\text{IQR}$) and extreme
         ($Q_3 + 3.0 \\times \\text{IQR}$) upper outliers, isolating injected KES 250,000
         anomalies while preserving legitimate right-skewed transactions.
      6. **Referential Integrity (Merge):** Audits transactions against `agents['agent_id']`,
         logs unknown/orphan agent IDs (e.g., `AG099`), and joins `county` and `onboarded`.

    Args:
        txns: Raw agent transactions DataFrame.
        agents: Registered agent master DataFrame (`agent_id`, `county`, `onboarded`).
        drop_missing_amounts: If True (default), exclude rows with missing/non-positive
            amounts from the returned clean DataFrame after flagging and logging them.
        drop_extreme_outliers: If True (default), exclude extreme $3.0 \\times \\text{IQR}$
            outliers (such as the KES 250,000 anomalies) after flagging and logging them.

    Returns:
        A tuple `(clean_df, log)` where `clean_df` is the cleaned, enriched DataFrame
        and `log` is a complete audit dictionary of counts and anomalies at each step.
    """
    log: dict = {
        "initial_txn_rows": int(len(txns)),
        "initial_agent_rows": int(len(agents)),
    }

    df = txns.copy()
    agents_clean = agents.copy()

    # Standardize keys & agent register metadata
    agents_clean["agent_id"] = agents_clean["agent_id"].astype(str).str.strip().str.upper()
    agents_clean["county"] = agents_clean["county"].astype(str).str.strip().str.title()
    agents_clean["onboarded"] = pd.to_datetime(agents_clean["onboarded"], format="mixed")
    valid_agents = set(agents_clean["agent_id"])

    df["txn_id"] = df["txn_id"].astype(str).str.strip().str.upper()
    df["agent_id"] = df["agent_id"].astype(str).str.strip().str.upper()

    # 1. UNIQUENESS: Remove exact duplicates, then deduplicate on txn_id preferring valid agents
    exact_dups = int(df.duplicated(keep="first").sum())
    df = df.drop_duplicates(keep="first").copy()
    log["exact_duplicates_removed"] = exact_dups

    df["_valid_agent"] = df["agent_id"].isin(valid_agents)
    df = df.sort_values(by=["txn_id", "_valid_agent"], ascending=[True, False])
    id_dups = int(df.duplicated(subset=["txn_id"], keep="first").sum())
    df = (
        df.drop_duplicates(subset=["txn_id"], keep="first")
          .drop(columns=["_valid_agent"])
          .reset_index(drop=True)
    )
    log["duplicate_txn_ids_removed"] = id_dups
    log["total_duplicates_removed"] = exact_dups + id_dups

    # 2. CONSISTENCY: Standardize txn_type into {"Deposit", "Withdrawal"}
    invalid_tokens = {"", "N/A", "NA", "NONE", "NULL", "NAN"}
    raw_type_str = df["txn_type"].astype(str).str.strip()
    invalid_type_mask = df["txn_type"].isna() | raw_type_str.str.upper().isin(invalid_tokens)

    standardized_type = np.where(
        invalid_type_mask,
        np.nan,
        raw_type_str.str.title(),
    )
    log["txn_type_values_standardized"] = int(
        (df["txn_type"].fillna("").astype(str) != pd.Series(standardized_type).fillna("")).sum()
    )
    df["txn_type"] = standardized_type

    allowed_types = {"Deposit", "Withdrawal"}
    unexpected_types = set(df["txn_type"].dropna()) - allowed_types
    if unexpected_types:
        raise ValueError(f"Unexpected txn_type values encountered: {unexpected_types}")
    log["unique_txn_types"] = sorted(df["txn_type"].dropna().unique().tolist())

    # 3. VALIDITY & TYPES: Coerce amount to numeric and txn_date to datetime64[ns]
    raw_amount_str = df["amount"].astype(str).str.strip()
    cleaned_amount_str = (
        raw_amount_str
        .str.replace(r"(?i)^kes\s*", "", regex=True)
        .str.replace(",", "", regex=False)
    )
    df["amount"] = pd.to_numeric(cleaned_amount_str, errors="coerce")

    raw_date_str = df["txn_date"].astype(str).str.strip()
    log["slash_dates_normalized"] = int(raw_date_str.str.contains("/", regex=False).sum())
    df["txn_date"] = pd.to_datetime(raw_date_str, format="mixed", errors="coerce")
    invalid_dates = int(df["txn_date"].isna().sum())
    log["invalid_dates_dropped"] = invalid_dates
    df = df.loc[df["txn_date"].notna()].copy()

    # 4. COMPLETENESS: Flag missing/invalid amounts (no imputation)
    missing_mask = df["amount"].isna() | (df["amount"] <= 0)
    df["is_missing_or_invalid_amount"] = missing_mask
    log["missing_or_invalid_amounts_flagged"] = int(missing_mask.sum())

    # 5. OUTLIERS (IQR): Compute fences on valid numeric amounts & flag anomalies
    valid_amt = df.loc[~missing_mask, "amount"]
    q1 = float(valid_amt.quantile(0.25))
    q3 = float(valid_amt.quantile(0.75))
    iqr = q3 - q1
    upper_fence_15 = q3 + 1.5 * iqr
    upper_fence_30 = q3 + 3.0 * iqr

    df["is_iqr_outlier"] = (~missing_mask) & (df["amount"] > upper_fence_15)
    df["is_extreme_outlier"] = (~missing_mask) & (df["amount"] > upper_fence_30)

    log["iqr_q1"] = round(q1, 2)
    log["iqr_q3"] = round(q3, 2)
    log["iqr_upper_fence_1_5x"] = round(upper_fence_15, 2)
    log["iqr_upper_fence_3_0x"] = round(upper_fence_30, 2)
    log["iqr_outliers_flagged_1_5x"] = int(df["is_iqr_outlier"].sum())
    log["extreme_outliers_flagged_3_0x"] = int(df["is_extreme_outlier"].sum())
    log["kes_250k_anomalies_flagged"] = int((df["amount"] == 250000).sum())

    if drop_missing_amounts:
        df = df.loc[~df["is_missing_or_invalid_amount"]].copy()
    if drop_extreme_outliers:
        df = df.loc[~df["is_extreme_outlier"]].copy()

    # 6. MERGE & REFERENTIAL INTEGRITY: Join to registered agents and isolate orphans
    merged = df.merge(agents_clean, on="agent_id", how="left", indicator=True)
    orphan_mask = merged["_merge"] == "left_only"
    log["unknown_agent_ids"] = sorted(merged.loc[orphan_mask, "agent_id"].unique().tolist())
    log["unknown_agent_rows_dropped"] = int(orphan_mask.sum())

    clean_df = (
        merged.loc[merged["_merge"] == "both"]
              .drop(columns=["_merge"])
              .sort_values("txn_id")
              .reset_index(drop=True)
    )
    log["final_clean_rows"] = int(len(clean_df))
    log["total_rows_removed"] = int(log["initial_txn_rows"] - log["final_clean_rows"])

    return clean_df, log


if __name__ == "__main__":
    agents_df = pd.read_csv("agents.csv")
    txns_df = pd.read_csv("agent_transactions.csv")
    cleaned, audit = clean_agent_data(txns_df, agents_df)
    for k, v in audit.items():
        print(f"{k}: {v}")
    print("\nCleaned shape:", cleaned.shape)
