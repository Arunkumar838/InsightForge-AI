import pandas as pd
import numpy as np
import re

def clean_dataset(df, config=None):
    """
    Cleans a pandas DataFrame based on the configuration or automatic heuristics.
    Returns:
        - cleaned_df (pd.DataFrame)
        - cleaning_report (dict)
        - quality_score (float)
    """
    if config is None:
        config = {
            "remove_duplicates": True,
            "handle_missing": True,
            "correct_dates": True,
            "detect_outliers": True,
            "standardize_units": True
        }
        
    report = {
        "duplicates_removed": 0,
        "missing_imputed": {},
        "outliers_detected": {},
        "dates_standardized": [],
        "standardizations": []
    }
    
    # Work on a copy of the dataframe
    cleaned_df = df.copy()
    original_rows = len(cleaned_df)
    original_cols = len(cleaned_df.columns)
    
    if original_rows == 0:
        return cleaned_df, report, 100.0

    # 1. Standardize Units and Currencies (Do this first so numeric cleaning runs on clean numbers)
    if config.get("standardize_units", True):
        for col in cleaned_df.columns:
            # Check if column is object type and contains currency or unit patterns
            if pd.api.types.is_string_dtype(cleaned_df[col]):
                # Sample non-null values
                sample = cleaned_df[col].dropna().head(10).astype(str)
                # Check for currency symbols or percent symbols
                has_currency = any(any(sym in val for sym in ['$', '€', '£', '¥']) for val in sample)
                has_pct = any('%' in val for val in sample)
                
                if has_currency or has_pct:
                    def clean_numeric_str(val):
                        if pd.isna(val) or val is None:
                            return np.nan
                        val_str = str(val).strip()
                        # Remove currency symbols, commas, and percentage signs
                        val_clean = re.sub(r'[^\d\.\-\+]', '', val_str)
                        try:
                            # If it was a percentage, convert to float division
                            num = float(val_clean)
                            if has_pct:
                                return num / 100.0
                            return num
                        except ValueError:
                            return val
                    
                    cleaned_df[col] = cleaned_df[col].apply(clean_numeric_str)
                    # Convert to numeric if possible
                    try:
                        cleaned_df[col] = pd.to_numeric(cleaned_df[col])
                        report["standardizations"].append(f"Standardized and converted column '{col}' to numeric format.")
                    except:
                        pass

    # 2. Correct Date Formats
    if config.get("correct_dates", True):
        for col in cleaned_df.columns:
            # Check if column name suggests date or contains date-like values
            col_lower = col.lower()
            is_date_name = any(k in col_lower for k in ["date", "time", "timestamp", "created", "updated"])
            
            if is_date_name or pd.api.types.is_string_dtype(cleaned_df[col]):
                sample = cleaned_df[col].dropna().head(10).astype(str)
                # Regex for common date patterns: YYYY-MM-DD, MM/DD/YYYY, DD-MM-YYYY, etc.
                date_pattern = re.compile(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}')
                if any(date_pattern.search(val) for val in sample):
                    try:
                        # Attempt pd.to_datetime
                        try:
                            parsed_dates = pd.to_datetime(cleaned_df[col], errors='coerce', format='mixed')
                        except:
                            parsed_dates = pd.to_datetime(cleaned_df[col], errors='coerce')
                            
                        null_pct_before = cleaned_df[col].isna().mean()
                        null_pct_after = parsed_dates.isna().mean()
                        
                        # If we didn't destroy too much data, keep the dates
                        if null_pct_after - null_pct_before < 0.2:
                            # Store date as standard string for JSON compatibility
                            cleaned_df[col] = parsed_dates.dt.strftime('%Y-%m-%d')
                            report["dates_standardized"].append(col)
                    except:
                        pass

    # 3. Remove Duplicates
    if config.get("remove_duplicates", True):
        initial_count = len(cleaned_df)
        cleaned_df = cleaned_df.drop_duplicates()
        removed = initial_count - len(cleaned_df)
        report["duplicates_removed"] = removed

    # 4. Handle Missing Values (Imputations)
    if config.get("handle_missing", True):
        for col in cleaned_df.columns:
            null_count = cleaned_df[col].isna().sum()
            if null_count > 0:
                if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    # Impute with median
                    median_val = cleaned_df[col].median()
                    if pd.isna(median_val):
                        median_val = 0
                    cleaned_df[col] = cleaned_df[col].fillna(median_val)
                    report["missing_imputed"][col] = {
                        "count": int(null_count),
                        "strategy": "Median Imputation",
                        "value": float(median_val)
                    }
                else:
                    # Impute with Mode or 'Unknown'
                    mode_series = cleaned_df[col].mode()
                    mode_val = mode_series[0] if not mode_series.empty else "Unknown"
                    cleaned_df[col] = cleaned_df[col].fillna(mode_val)
                    report["missing_imputed"][col] = {
                        "count": int(null_count),
                        "strategy": "Mode Imputation",
                        "value": str(mode_val)
                    }

    # 5. Detect and handle Outliers (using IQR method)
    if config.get("detect_outliers", True):
        for col in cleaned_df.columns:
            if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                # Skip IDs or zipcodes
                if any(k in col.lower() for k in ["id", "zip", "code", "phone"]):
                    continue
                
                q1 = cleaned_df[col].quantile(0.25)
                q3 = cleaned_df[col].quantile(0.75)
                iqr = q3 - q1
                
                if iqr > 0:
                    lower_bound = q1 - 1.5 * iqr
                    upper_bound = q3 + 1.5 * iqr
                    
                    outliers_lower = cleaned_df[cleaned_df[col] < lower_bound]
                    outliers_upper = cleaned_df[cleaned_df[col] > upper_bound]
                    total_outliers = len(outliers_lower) + len(outliers_upper)
                    
                    if total_outliers > 0:
                        # Clip outliers to bounds
                        cleaned_df[col] = cleaned_df[col].clip(lower_bound, upper_bound)
                        report["outliers_detected"][col] = {
                            "count": int(total_outliers),
                            "lower_bound": float(lower_bound),
                            "upper_bound": float(upper_bound),
                            "action": "Clipped to boundaries"
                        }

    # Calculate Data Quality Score
    # Initial score = 100
    quality_score = 100.0
    
    total_elements = original_rows * original_cols
    total_nulls = sum(item["count"] for item in report["missing_imputed"].values())
    
    if total_elements > 0:
        null_penalty = (total_nulls / total_elements) * 40.0 # up to 40 points penalty
        null_pct = min(null_penalty, 40.0)
        quality_score -= null_pct
        
    if original_rows > 0:
        dup_penalty = (report["duplicates_removed"] / original_rows) * 20.0 # up to 20 points penalty
        quality_score -= min(dup_penalty, 20.0)
        
        total_outliers = sum(item["count"] for item in report["outliers_detected"].values())
        outlier_penalty = (total_outliers / original_rows) * 15.0 # up to 15 points penalty
        quality_score -= min(outlier_penalty, 15.0)
        
    # Standardizations and other format improvements boost structure, but if there were too many corrections, slight penalty
    if len(report["dates_standardized"]) > 0 or len(report["standardizations"]) > 0:
        quality_score -= 5.0 # minor deduction for raw formatting consistency
        
    quality_score = max(0.0, min(100.0, quality_score))
    
    # Convert dataframe values to serializable types
    cleaned_df = cleaned_df.replace({np.nan: None})
    
    return cleaned_df, report, round(quality_score, 2)
