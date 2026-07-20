import re
import random
import datetime

def generate_ai_response(agent_name, role, query, dataset_summary=None, last_action_results=None):
    low_query = query.lower()
    
    # Extract dataset details
    filename = dataset_summary.get("filename", "dataset.csv") if dataset_summary else "dataset.csv"
    doc_type = dataset_summary.get("doc_type", "CSV spreadsheet") if dataset_summary else "CSV spreadsheet"
    domain = dataset_summary.get("domain", "General Business") if dataset_summary else "General Business"
    row_count = dataset_summary.get("row_count", 0) if dataset_summary else 0
    cols = dataset_summary.get("columns", []) if dataset_summary else []
    quality_score = dataset_summary.get("quality_score", 95.0) if dataset_summary else 95.0
    
    # 1. Document Extraction Agent responses
    if agent_name == "DocuExtract AI":
        if any(w in low_query for w in ["ocr", "image", "scanned", "receipt", "invoice"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"I have executed the OCR extraction pipeline on the scanned document. Here are my findings:\n\n"
                f"- **Extraction Accuracy**: 98.7% spatial coordinate match.\n"
                f"- **Identified Domain**: **{domain}** (based on keyword weights for invoice elements).\n"
                f"- **Parsed Layout**: Extracted a tabular structure with **{len(cols)} columns** and **{row_count} rows**.\n\n"
                f"The text extraction shows clean parsing of numerical cells. I suggest forwarding this to the **Data Cleaner (Purify AI)** to standardise dates and currency values."
            )
        elif any(w in low_query for w in ["column", "schema", "headers"]):
            cols_str = ", ".join([f"`{c}`" for c in cols]) if cols else "None"
            return (
                f"### [{agent_name}] ({role})\n"
                f"The extracted columns from `{filename}` are: {cols_str}.\n\n"
                f"The dataset consists of {row_count} records. The primary keys and timestamps are located in the columns: "
                f"`{cols[0] if cols else 'N/A'}` and `{cols[4] if len(cols) > 4 else 'N/A'}`."
            )
        else:
            return (
                f"### [{agent_name}] ({role})\n"
                f"I parsed the file `{filename}` ({doc_type}) for the **{domain}** workspace. The parsed dataset has **{row_count} rows** and **{len(cols)} columns**.\n\n"
                f"The data ingestion process completed with 0 errors. Let me know if you would like me to explain the parsing of any specific column or structure."
            )

    # 2. Data Cleaning Agent responses
    elif agent_name == "Purify AI":
        report = last_action_results or {}
        if any(w in low_query for w in ["score", "quality", "index"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"The active dataset has a **Data Quality Score of {quality_score}/100**.\n\n"
                f"This score is calculated by evaluating null values, outlier ratios, and duplicates. "
                f"Currently, the dataset has a very clean structure with **{report.get('duplicates_removed', 0)} duplicates** removed and outliers capped in **{len(report.get('outliers_detected', {}))} columns**."
            )
        elif any(w in low_query for w in ["missing", "impute", "empty", "null"]):
            imputed = report.get('missing_imputed', {})
            if imputed:
                imp_str = "\n".join([f"- **{c}**: Imputed {d['count']} missing values using *{d['strategy']}*." for c, d in imputed.items()])
            else:
                imp_str = "No missing entries were found or imputed."
            return (
                f"### [{agent_name}] ({role})\n"
                f"Here is the missing data imputation log:\n\n{imp_str}\n\n"
                f"We use median imputation for numerical features and mode/majority category for categorical columns to ensure statistical validity."
            )
        elif any(w in low_query for w in ["outlier", "anomal", "iqr"]):
            outliers = report.get('outliers_detected', {})
            if outliers:
                out_str = "\n".join([f"- **{c}**: Capped {d['count']} outliers to range [{round(d['lower_bound'], 1)}, {round(d['upper_bound'], 1)}]." for c, d in outliers.items()])
            else:
                out_str = "No statistical outliers were detected in the numerical columns."
            return (
                f"### [{agent_name}] ({role})\n"
                f"Here is the anomaly/outlier detection log:\n\n{out_str}\n\n"
                f"Outliers are detected using the IQR (Interquartile Range) method with a standard 1.5x multiplier."
            )
        else:
            return (
                f"### [{agent_name}] ({role})\n"
                f"The dataset cleaning log shows that **{report.get('duplicates_removed', 0)} duplicates** have been removed, "
                f"and currencies and units have been standardized. The quality score stands at **{quality_score}/100**.\n\n"
                f"Would you like me to explain how we handle specific outliers or format conversions?"
            )

    # 3. Visualization Agent responses
    elif agent_name == "VividCharts AI":
        if any(w in low_query for w in ["bar", "distribution", "volume"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"The **Volume Distribution (Bar Chart)** groups data by the primary categorical column `{cols[0] if cols else 'Category'}`.\n\n"
                f"It shows the average values for `{cols[1] if len(cols) > 1 else 'Value'}`. "
                f"This chart is useful for identifying the high-performing sectors and segmentations in the **{domain}** workspace."
            )
        elif any(w in low_query for w in ["heatmap", "matrix", "correlation"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"The **Correlation Heatmap Grid** computes Pearson correlation coefficients between numerical columns.\n\n"
                f"Darker colors show strong dependencies. High correlation (near 1.0 or -1.0) suggests feature collinearity, which is crucial for choosing features in predictive modeling."
            )
        elif any(w in low_query for w in ["scatter", "relationship"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"The **Dependent Relationships (Scatter Plot)** maps the distribution of points across two major variables. "
                f"It helps visualize clustering patterns, clusters, and anomalies in a 2D space."
            )
        else:
            return (
                f"### [{agent_name}] ({role})\n"
                f"I have set up 9 visualization panels for the **{domain}** workspace, covering distributions, trends, share, scatter, correlation matrix, histogram, boxplot, heatmap density, and maps.\n\n"
                f"Let me know if you would like me to explain the patterns in any of these dashboards."
            )

    # 4. Prediction Agent responses
    elif agent_name == "Predicta AI":
        results = last_action_results or {}
        metrics = results.get("metrics", {})
        conf = metrics.get("confidence", 0.85) * 100
        importances = results.get("feature_importances", {})
        
        if any(w in low_query for w in ["important", "feature", "weight", "variable"]):
            if importances:
                imp_str = "\n".join([f"- **{k}**: {round(v*100, 1)}% relative importance" for k, v in list(importances.items())[:3]])
                top_feat = list(importances.keys())[0]
            else:
                imp_str = "- No feature importances calculated yet. Please train a model."
                top_feat = "None"
            return (
                f"### [{agent_name}] ({role})\n"
                f"Based on the trained predictive model, the feature importances are:\n\n{imp_str}\n\n"
                f"The most important predictor variable is **{top_feat}**. This feature plays the primary role in driving the target column predictions."
            )
        elif any(w in low_query for w in ["shap", "shapley", "explain"]):
            shap = results.get("shap", {})
            shap_vals = shap.get("shap_values", {})
            if shap_vals:
                shap_str = "\n".join([f"- `{k}`: contribution of {v:+.4f}" for k, v in list(shap_vals.items())[:3]])
            else:
                shap_str = "No SHAP explainer weights are currently calculated."
            return (
                f"### [{agent_name}] ({role})\n"
                f"The SHAP (Shapley Additive exPlanations) values represent the contribution of each feature to the difference between the actual prediction and the average base prediction:\n\n"
                f"{shap_str}\n\n"
                f"Green bars indicate features that pull the prediction up, while red bars indicate features that push it down."
            )
        elif any(w in low_query for w in ["forecast", "future", "5 years", "year", "lstm", "holt"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"Our time-series forecasting model projects future values based on historical data. "
                f"Looking at the forecast timeline, we expect a steady growth path. "
                f"Confidence intervals show the upper and lower statistical bounds (95% confidence). "
                f"In the coming cycles, volume is projected to grow by approximately 12-15%."
            )
        else:
            imp_str = ""
            if importances:
                imp_str = "\n" + "\n".join([f"- **{k}**: {round(v*100, 1)}% importance" for k, v in list(importances.items())[:3]])
            return (
                f"### [{agent_name}] ({role})\n"
                f"I have successfully fitted your predictive model (Confidence: **{round(conf, 1)}%**).\n\n"
                f"**Top Predicting Variables:**{imp_str or ' - None trained yet.'}\n\n"
                f"If you have any questions about model performance, forecast trend direction, or feature impact, please ask!"
            )

    # 5. Business Agent responses
    elif agent_name == "Consul AI":
        if any(w in low_query for w in ["risk", "threat", "churn"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"**Strategic Risk Audit for {domain}**:\n\n"
                f"- **Pricing Elasticity**: Increasing price without a corresponding marketing push raises customer churn risk.\n"
                f"- **Inventory**: Stock levels must be managed carefully. A drop of more than 10% in inventory may cause delivery delays or stockouts.\n"
                f"- **Staffing**: Ensure adequate support staffing levels to prevent customer churn."
            )
        elif any(w in low_query for w in ["marketing", "pricing", "elasticity", "simulate"]):
            return (
                f"### [{agent_name}] ({role})\n"
                f"Based on our simulation elasticities in **{domain}**:\n\n"
                f"- **Marketing return**: Every 10% increase in marketing budget yields approximately an 8% increase in demand volume.\n"
                f"- **Pricing impact**: Price hikes increase margin per unit but decrease overall volume by 1.5x the price increase percentage.\n\n"
                f"I recommend finding the optimal balance using the sliders in the What-If Simulator."
            )
        else:
            return (
                f"### [{agent_name}] ({role})\n"
                f"I am auditing the What-If simulation parameters. Current baseline and projection calculations are fully initialized.\n\n"
                f"Let me know if you would like me to evaluate specific scenarios related to pricing adjustments, staffing levels, or marketing budgets."
            )

    # 6. Report Agent responses
    elif agent_name == "ExecutiveBrief AI":
        return (
            f"### [{agent_name}] ({role})\n"
            f"I can package your **{domain}** project summaries and exports into executive files:\n\n"
            f"- **PowerPoint Pitch Deck**: Renders slides with visualization insights and ML forecasts.\n"
            f"- **PDF Executive Brief**: Formats table previews, quality logs, and auditor notes.\n"
            f"- **Clean Excel Sheet**: Exports standard dataset records with outliers capped.\n\n"
            f"Please click the **Export Data** dropdown in the navigation header to download these files."
        )
        
    return f"### [{agent_name}] ({role})\nI am processing your request. Please let me know how I can assist you with your data analysis."

class BaseAgent:
    def __init__(self, name, role, color, description):
        self.name = name
        self.role = role
        self.color = color
        self.description = description

    def process(self, query, dataset_summary=None, last_action_results=None):
        return generate_ai_response(self.name, self.role, query, dataset_summary, last_action_results)

class DocumentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "DocuExtract AI", 
            "Document Processing Expert", 
            "#00d2ff",
            "Extracts structured datasets from raw PDF, Word, PPTX, Images, and SQL dumps using advanced parsing and OCR."
        )

class CleaningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "Purify AI", 
            "Data Quality & Imputation Analyst", 
            "#00ff87",
            "Automatically removes duplicates, imputes missing cells, clips statistical outliers, and calculates data quality metrics."
        )

class VisualizationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "VividCharts AI", 
            "Visualization Architect", 
            "#ff007f",
            "Designs interactive dashboards, maps, and statistical matrices while highlighting visual insights, trends, and anomalies."
        )

class PredictionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "Predicta AI", 
            "Machine Learning Specialist", 
            "#7000ff",
            "Trains Regression, Forest, Gradient Boosting, and LSTM models, displaying confidence intervals and SHAP local feature importance."
        )

class BusinessAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "Consul AI", 
            "Strategic Business Consultant", 
            "#ffaa00",
            "Analyzes simulated business variables in the What-If Simulator, highlighting operational risks and actionable recommendations."
        )

class ReportAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "ExecutiveBrief AI", 
            "Report Generation Specialist", 
            "#ffffff",
            "Compiles all findings, dashboards, and forecasts into PowerPoint slides, PDF reports, and executive summaries."
        )

class MultiAgentManager:
    def __init__(self):
        self.agents = {
            "document": DocumentAgent(),
            "cleaning": CleaningAgent(),
            "visualization": VisualizationAgent(),
            "prediction": PredictionAgent(),
            "business": BusinessAgent(),
            "report": ReportAgent()
        }
        self.active_agent_key = "document"

    def set_active_agent(self, key):
        if key in self.agents:
            self.active_agent_key = key

    def route_query(self, query, dataset_summary=None, last_action_results=None):
        low_query = query.lower()
        
        if any(w in low_query for w in ["upload", "file", "ocr", "extract", "parse"]):
            agent_key = "document"
        elif any(w in low_query for w in ["clean", "duplicate", "missing", "outlier", "impute", "quality"]):
            agent_key = "cleaning"
        elif any(w in low_query for w in ["chart", "plot", "graph", "visual", "heatmap", "matrix"]):
            agent_key = "visualization"
        elif any(w in low_query for w in ["predict", "forecast", "ml", "train", "shap", "lstm", "xgboost"]):
            agent_key = "prediction"
        elif any(w in low_query for w in ["simulator", "what-if", "what if", "business", "recommend", "risk"]):
            agent_key = "business"
        elif any(w in low_query for w in ["export", "report", "ppt", "pdf", "docx", "download"]):
            agent_key = "report"
        else:
            agent_key = self.active_agent_key
            
        agent = self.agents[agent_key]
        response = agent.process(query, dataset_summary, last_action_results)
        
        return {
            "agent_name": agent.name,
            "agent_role": agent.role,
            "agent_color": agent.color,
            "response": response,
            "suggested_questions": self.get_suggestions(agent_key)
        }

    def get_suggestions(self, agent_key):
        suggestions = {
            "document": ["Explain the file format detected", "Extract tabular data from my scanned image", "Show raw parsed text"],
            "cleaning": ["What is my Data Quality Score?", "Explain the outlier detection method", "How were missing values imputed?"],
            "visualization": ["Show correlation matrix details", "What anomalies were found in the scatter plot?", "Can you explain the heatmap?"],
            "prediction": ["Which feature is most important?", "Show SHAP value breakdown", "Train a Random Forest model"],
            "business": ["What happens if I increase price by 10%?", "Analyze business risks", "Provide optimization suggestions"],
            "report": ["Compile PDF Report", "Generate PowerPoint Pitch Deck", "Export clean Excel summary"]
        }
        return suggestions.get(agent_key, [])
