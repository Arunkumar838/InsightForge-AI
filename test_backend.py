import os
import pandas as pd
import numpy as np

# Test imports
from backend.db import create_project, get_project, list_projects, log_audit, get_audit_logs
from backend.parser import detect_domain, parse_sql_dump
from backend.cleaning import clean_dataset
from backend.ml_models import train_and_predict, forecast_time_series
from backend.agents import MultiAgentManager

def run_tests():
    print("--------------------------------------------------")
    print("          INSIGHTFORGE TEST SUITE START           ")
    print("--------------------------------------------------")
    
    # 1. Test Database Operations
    print("[TEST 1] Database Operations...")
    proj = create_project("Test Automation", "Mock tests running", "test_runner")
    assert proj["name"] == "Test Automation"
    assert proj["owner"] == "test_runner"
    
    fetched = get_project(proj["id"])
    assert fetched["id"] == proj["id"]
    
    log_audit("test_runner", "RUN_TESTS", "Verifying system modules integrity")
    logs = get_audit_logs()
    assert len(logs) > 0
    assert any(log["user"] == "test_runner" for log in logs)
    print(">> DB Operations: PASS")

    # 2. Test Parser Domain Detection
    print("\n[TEST 2] Document Parser Domain Detection...")
    text_retail = "We have tracked high sales margins on SKU-9901 and general retail stores this quarter."
    domain_retail = detect_domain(text_retail)
    assert domain_retail == "Retail", f"Expected Retail, got {domain_retail}"
    
    text_medical = "Patient P-128 reported to the doctor with clinical diagnoses symptoms."
    domain_med = detect_domain(text_medical)
    assert domain_med == "Healthcare", f"Expected Healthcare, got {domain_med}"
    print(">> Domain Detection: PASS")

    # 3. Test SQL dump parser
    print("\n[TEST 3] SQL Dump Parser...")
    sql_text = "INSERT INTO test_table (id, val, rate) VALUES (1, 'demo', 3.4), (2, 'sample', NULL);"
    res_sql = parse_sql_dump(sql_text)
    assert "test_table" in res_sql
    assert res_sql["test_table"]["cols"] == ["id", "val", "rate"]
    assert len(res_sql["test_table"]["rows"]) == 2
    assert res_sql["test_table"]["rows"][0] == [1, "demo", 3.4]
    print(">> SQL Dump Parser: PASS")

    # 4. Test Cleaning Pipeline
    print("\n[TEST 4] Data Cleaning Pipeline...")
    mock_data = pd.DataFrame({
        "Date": ["2026/05/12", "2026-05-12", "2026/05/12", "2026/05/13", "2026/05/14", "2026/05/15", "2026/05/16", "2026/05/17", None], # duplicate, formats, missing
        "Revenue": ["$1,250.00", "$1,250.00", "$1,250.00", "$1,300.00", "$1,200.00", "$1,250.00", "$1,310.00", "$1,220.00", "$5,000.00"], # currency removal
        "Volume": [10, 10, 10, 12, 11, 10, 13, 11, 500] # outlier
    })
    
    cleaned_df, report, score = clean_dataset(mock_data)
    # Check duplicate row removed (9 rows -> 2 duplicates removed -> 7 unique rows)
    assert len(cleaned_df) == 7, f"Expected 7 rows, got {len(cleaned_df)}"
    # Check currency conversion to float
    assert cleaned_df["Revenue"].dtype in [np.float64, np.float32, float, int]
    # Check missing date imputed
    assert cleaned_df["Date"].isna().sum() == 0
    # Check outliers clipped (IQR limits for 10 and 500)
    assert cleaned_df["Volume"].max() < 500
    assert score > 0
    print(">> Cleaning Pipeline: PASS")

    # 5. Test ML Engine & SHAP Explainer
    print("\n[TEST 5] Predictive AI & SHAP calculations...")
    np.random.seed(42)
    # Create regression dataset
    df_ml = pd.DataFrame({
        "FeatA": np.random.uniform(1, 10, 50),
        "FeatB": np.random.uniform(10, 20, 50),
        "Target": np.zeros(50)
    })
    # Target = 2 * FeatA + 0.5 * FeatB
    df_ml["Target"] = 2 * df_ml["FeatA"] + 0.5 * df_ml["FeatB"] + np.random.normal(0, 0.1, 50)
    
    res_ml = train_and_predict(df_ml, "Target", ["FeatA", "FeatB"], "Linear Regression")
    assert "metrics" in res_ml
    assert res_ml["metrics"]["confidence"] > 0.8
    assert "feature_importances" in res_ml
    assert "shap" in res_ml
    # FeatA should have higher importance
    importances = res_ml["feature_importances"]
    assert importances["FeatA"] > importances["FeatB"]
    
    # Check SHAP sum matches offset
    shap = res_ml["shap"]
    shap_sum = sum(shap["shap_values"].values())
    pred_diff = shap["prediction"] - shap["base_value"]
    assert abs(shap_sum - pred_diff) < 1e-4
    print(">> ML Engine & SHAP: PASS")

    # 6. Test Forecasting
    print("\n[TEST 6] Time-Series Forecasting...")
    dates = pd.date_range(start="2026-01-01", periods=10, freq="D")
    vals = np.array([10, 12, 11, 13, 14, 16, 15, 17, 18, 20])
    df_ts = pd.DataFrame({"Date": dates.strftime("%Y-%m-%d"), "Value": vals})
    
    res_ts = forecast_time_series(df_ts, "Date", "Value", forecast_steps=5, method="LSTM")
    assert len(res_ts["historical"]) == 10
    assert len(res_ts["forecast"]) == 5
    assert "lower" in res_ts["forecast"][0]
    assert "upper" in res_ts["forecast"][0]
    print(">> Forecasting Engine: PASS")

    # 7. Test Multi-Agent routing
    print("\n[TEST 7] Multi-Agent AI Core Router...")
    mgr = MultiAgentManager()
    
    # Query for prediction
    res_chat = mgr.route_query("Train a random forest classifier to forecast churn")
    assert res_chat["agent_name"] == "Predicta AI"
    
    # Query for cleaning
    res_chat2 = mgr.route_query("Clean empty columns and compute quality")
    assert res_chat2["agent_name"] == "Purify AI"
    print(">> Multi-Agent Console: PASS")

    print("\n--------------------------------------------------")
    print("          INSIGHTFORGE TEST SUITE PASSED          ")
    print("--------------------------------------------------")

if __name__ == "__main__":
    run_tests()
