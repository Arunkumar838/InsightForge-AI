import os
import json
import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd

# Import local backend modules
from backend.db import (
    authenticate_user, verify_api_key, list_projects, get_project,
    create_project, delete_project, add_dataset_version, log_audit, get_audit_logs, save_project
)
from backend.parser import parse_file
from backend.ocr import perform_ocr
from backend.cleaning import clean_dataset
from backend.ml_models import train_and_predict, forecast_time_series
from backend.agents import MultiAgentManager
from backend.exporters import export_excel, export_powerpoint, export_pdf

app = FastAPI(title="InsightForge AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Multi-Agent Manager Instance
agent_manager = MultiAgentManager()

# Ensure directories exist
os.makedirs("static", exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)

# ----------------- Models -----------------
class LoginRequest(BaseModel):
    username: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    description: str
    owner: str

class CleanConfigRequest(BaseModel):
    remove_duplicates: bool = True
    handle_missing: bool = True
    correct_dates: bool = True
    detect_outliers: bool = True
    standardize_units: bool = True

class TrainRequest(BaseModel):
    target_col: str
    feature_cols: List[str]
    model_type: str = "Random Forest"
    username: str

class ForecastRequest(BaseModel):
    date_col: str
    value_col: str
    steps: int = 12
    method: str = "LSTM"
    username: str

class ChatRequest(BaseModel):
    message: str
    active_agent: Optional[str] = "document"
    username: str

class SimulateRequest(BaseModel):
    pricing_adj: float = 0.0 # pct adjustment e.g. -10 to +30
    marketing_adj: float = 0.0 # pct adjustment
    staffing_adj: float = 0.0 # pct adjustment
    inventory_adj: float = 0.0 # pct
    demand_adj: float = 0.0 # pct
    target_metric: str # target column to simulate

# ----------------- Auth endpoints -----------------
@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    log_audit(req.username, "LOGIN", "Logged into InsightForge AI console")
    return user

# ----------------- Project endpoints -----------------
@app.get("/api/projects")
def get_all_projects():
    return list(list_projects().values())

@app.post("/api/projects")
def make_project(proj: ProjectCreate):
    return create_project(proj.name, proj.description, proj.owner)

@app.get("/api/projects/{project_id}")
def get_one_project(project_id: str):
    p = get_project(project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@app.delete("/api/projects/{project_id}")
def remove_project(project_id: str, username: str = "admin"):
    success = delete_project(project_id, username)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "success", "message": "Project deleted"}

# ----------------- Upload & OCR endpoints -----------------
@app.post("/api/projects/{project_id}/upload")
async def upload_document(
    project_id: str, 
    username: str = Form(...),
    file: UploadFile = File(...)
):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    contents = await file.read()
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    # Check if image or scanned document -> OCR
    is_ocr = ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]
    
    try:
        if is_ocr:
            df, domain, raw_text = await run_in_threadpool(perform_ocr, filename, contents)
            doc_type = "Scanned Image (OCR)"
        else:
            df, domain, doc_type, raw_text = await run_in_threadpool(parse_file, filename, contents)
            
        if df is None or df.empty:
            raise Exception("No readable tabular structure extracted from document.")
            
        # Convert df to JSON serializable list
        dataset_json = df.to_dict(orient="records")
        
        # Save file metadata
        file_metadata = {
            "filename": filename,
            "file_size": len(contents),
            "doc_type": doc_type,
            "uploaded_at": datetime.datetime.now().isoformat()
        }
        
        # Add to project as new dataset version
        project = add_dataset_version(
            project_id=project_id,
            username=username,
            dataset_json=dataset_json,
            comment=f"Initial upload of {filename} ({doc_type})",
            file_metadata=file_metadata
        )
        
        # Save domain and doc type to project root
        project["domain"] = domain
        project["doc_type"] = doc_type
        save_project(project_id, project)
        
        log_audit(username, "UPLOAD_FILE", f"Uploaded and structured {filename} under {domain} domain")
        
        return {
            "status": "success",
            "domain": domain,
            "doc_type": doc_type,
            "rows": len(dataset_json),
            "columns": list(df.columns),
            "preview": dataset_json[:10]
        }
        
    except Exception as e:
        log_audit(username, "UPLOAD_FAILED", f"Upload failed for {filename}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- Cleaning pipeline endpoint -----------------
@app.post("/api/projects/{project_id}/clean")
def clean_project_data(project_id: str, config: CleanConfigRequest, username: str = "admin"):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Get active dataset
    data = project.get("active_dataset")
    if not data:
        raise HTTPException(status_code=400, detail="No active dataset. Upload a file first.")
        
    df = pd.DataFrame(data)
    
    try:
        cleaned_df, report, quality_score = clean_dataset(df, config.dict())
        
        # Convert to serializable format
        cleaned_json = cleaned_df.to_dict(orient="records")
        
        # Update project with new cleaned version
        project = add_dataset_version(
            project_id=project_id,
            username=username,
            dataset_json=cleaned_json,
            comment="Automated pipeline cleaning & standardization"
        )
        
        # Update metadata details
        project["cleaning_history"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "score_after": quality_score,
            "report": report
        })
        save_project(project_id, project)
        
        log_audit(username, "CLEAN_DATASET", f"Executed cleaning pipeline. Quality score is now {quality_score}/100")
        
        return {
            "status": "success",
            "quality_score": quality_score,
            "report": report,
            "preview": cleaned_json[:10]
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cleaning failure: {str(e)}")

# ----------------- ML model endpoints -----------------
@app.post("/api/projects/{project_id}/train")
def train_project_model(project_id: str, req: TrainRequest):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    data = project.get("active_dataset")
    if not data:
        raise HTTPException(status_code=400, detail="No dataset loaded to train model.")
        
    df = pd.DataFrame(data)
    
    try:
        results = train_and_predict(df, req.target_col, req.feature_cols, req.model_type)
        
        # Save model metadata in project
        project["models"][req.target_col] = {
            "model_type": req.model_type,
            "features": req.feature_cols,
            "metrics": results["metrics"],
            "feature_importances": results["feature_importances"]
        }
        save_project(project_id, project)
        
        log_audit(req.username, "TRAIN_MODEL", f"Trained {req.model_type} model targeting '{req.target_col}'")
        
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Training failure: {str(e)}")

@app.post("/api/projects/{project_id}/forecast")
def forecast_project_data(project_id: str, req: ForecastRequest):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    data = project.get("active_dataset")
    if not data:
        raise HTTPException(status_code=400, detail="No dataset loaded.")
        
    df = pd.DataFrame(data)
    
    try:
        results = forecast_time_series(df, req.date_col, req.value_col, req.steps, req.method)
        log_audit(req.username, "FORECAST_DATA", f"Executed time-series forecast ({req.method}) for {req.value_col}")
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Forecasting failure: {str(e)}")

# ----------------- What-If Simulator -----------------
@app.post("/api/projects/{project_id}/simulate")
def run_simulation(project_id: str, req: SimulateRequest):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    data = project.get("active_dataset")
    if not data:
        raise HTTPException(status_code=400, detail="No dataset loaded.")
        
    df = pd.DataFrame(data)
    target = req.target_metric
    
    # Calculate simple base value
    if target not in df.columns:
        raise HTTPException(status_code=400, detail=f"Target metric '{target}' not found in dataset columns.")
        
    try:
        base_value = float(pd.to_numeric(df[target], errors='coerce').dropna().mean())
    except:
        base_value = 1000.0 # Fallback
        
    # Simulate outcome based on basic economic elasticity formulas
    # Pricing: -elasticity on demand. Default: price increase of 10% drops demand/quantity by 15%, but increases unit margins.
    # Marketing: +elasticity on demand. Default: +10% marketing increases demand by 8%.
    # Staffing: minor +elasticity on conversion/efficiency. +10% staffing increases output by 2%.
    # Inventory: stockout dampening. If inventory drops below -20%, demand falls due to stockouts.
    
    elasticity_price = -1.5 # -1.5 demand change for 1.0 price change
    elasticity_marketing = 0.8
    elasticity_staffing = 0.2
    elasticity_demand = 1.0
    
    # Compute multipliers
    p_mult = 1.0 + (req.pricing_adj / 100.0)
    m_mult = 1.0 + (req.marketing_adj / 100.0)
    s_mult = 1.0 + (req.staffing_adj / 100.0)
    i_mult = 1.0 + (req.inventory_adj / 100.0)
    d_mult = 1.0 + (req.demand_adj / 100.0)
    
    # Final volume factor
    volume_change = (
        (req.pricing_adj * elasticity_price) + 
        (req.marketing_adj * elasticity_marketing) + 
        (req.staffing_adj * elasticity_staffing) +
        (req.demand_adj * elasticity_demand)
    )
    
    # Stockout check
    if req.inventory_adj < -10.0:
        # stockouts penalty
        volume_change += (req.inventory_adj + 10.0) * 0.5
        
    volume_mult = max(0.1, 1.0 + (volume_change / 100.0))
    
    # Resulting value
    # If target is Revenue/Sales: volume * price
    if any(k in target.lower() for k in ["revenue", "sales", "total", "amount", "billing"]):
        predicted_value = base_value * volume_mult * p_mult
    # If target is Quantity/Volume: volume
    elif any(k in target.lower() for k in ["quantity", "volume", "produced", "units"]):
        predicted_value = base_value * volume_mult
    # If target is profit/margin: volume * price - costs (approximated)
    elif "profit" in target.lower() or "income" in target.lower() or "ebitda" in target.lower():
        # costs are marketing & staffing & inventory holding
        cost_change = (req.marketing_adj * 0.3) + (req.staffing_adj * 0.4) + (req.inventory_adj * 0.1)
        cost_mult = max(0.5, 1.0 + (cost_change / 100.0))
        predicted_value = (base_value * 1.3 * volume_mult * p_mult) - (base_value * 0.3 * cost_mult)
    else:
        # Generic change
        predicted_value = base_value * volume_mult
        
    # Return metrics for charts
    labels = ["Base Baseline", "Projected Scenario"]
    values = [round(base_value, 2), round(predicted_value, 2)]
    
    # Save simulated state
    project["simulator_state"] = {
        "pricing": req.pricing_adj,
        "marketing": req.marketing_adj,
        "staffing": req.staffing_adj,
        "inventory": req.inventory_adj,
        "demand": req.demand_adj,
        "predicted_value": predicted_value
    }
    save_project(project_id, project)
    
    return {
        "labels": labels,
        "values": values,
        "percentage_change": round(((predicted_value - base_value) / base_value) * 100, 2) if base_value > 0 else 0.0,
        "base_value": round(base_value, 2),
        "predicted_value": round(predicted_value, 2)
    }

# ----------------- Multi-agent AI Chat endpoint -----------------
@app.post("/api/projects/{project_id}/chat")
def agent_chat(project_id: str, req: ChatRequest):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    data = project.get("active_dataset")
    dataset_summary = None
    if data:
        df = pd.DataFrame(data)
        history = project.get("cleaning_history", [])
        score = history[-1]["score_after"] if history else 95.0
        
        dataset_summary = {
            "filename": project["files"][-1]["filename"] if project["files"] else "dataset.csv",
            "doc_type": project.get("doc_type", "CSV spreadsheet"),
            "domain": project.get("domain", "General Business"),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "quality_score": score
        }
        
    # Get last model training action details if any
    last_action_results = None
    if project.get("models"):
        target = list(project["models"].keys())[-1]
        last_action_results = {
            "metrics": project["models"][target]["metrics"],
            "feature_importances": project["models"][target]["feature_importances"]
        }
    elif project.get("cleaning_history"):
        last_action_results = project["cleaning_history"][-1]["report"]
        
    if req.active_agent:
        agent_manager.set_active_agent(req.active_agent)
        
    response_payload = agent_manager.route_query(req.message, dataset_summary, last_action_results)
    log_audit(req.username, "CHAT", f"Queried multi-agent console (Agent: {response_payload['agent_name']})")
    
    return response_payload

# ----------------- Exporters endpoints -----------------
@app.get("/api/projects/{project_id}/export/excel")
def get_excel_report(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    data = project.get("active_dataset")
    if not data:
        raise HTTPException(status_code=400, detail="No dataset loaded to export.")
        
    df = pd.DataFrame(data)
    
    # Get last cleaning logs
    history = project.get("cleaning_history", [])
    report = history[-1]["report"] if history else {}
    
    excel_bytes = export_excel(df, report)
    
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=InsightForge_Cleaned_{project_id[:6]}.xlsx"}
    )

@app.get("/api/projects/{project_id}/export/pptx")
def get_pptx_report(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    data = project.get("active_dataset")
    if not data:
        raise HTTPException(status_code=400, detail="No dataset loaded to export.")
        
    df = pd.DataFrame(data)
    history = project.get("cleaning_history", [])
    score = history[-1]["score_after"] if history else 95.0
    
    dataset_summary = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "quality_score": score
    }
    
    ml_results = None
    if project.get("models"):
        target = list(project["models"].keys())[-1]
        ml_results = {
            "metrics": project["models"][target]["metrics"],
            "feature_importances": project["models"][target]["feature_importances"]
        }
        
    ppt_bytes = export_powerpoint(project["name"], project.get("domain", "Retail"), dataset_summary, ml_results)
    
    return Response(
        content=ppt_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=InsightForge_Briefing_{project_id[:6]}.pptx"}
    )

@app.get("/api/projects/{project_id}/export/pdf")
def get_pdf_report(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    data = project.get("active_dataset")
    if not data:
        raise HTTPException(status_code=400, detail="No dataset loaded to export.")
        
    df = pd.DataFrame(data)
    history = project.get("cleaning_history", [])
    score = history[-1]["score_after"] if history else 95.0
    report = history[-1]["report"] if history else {}
    
    dataset_summary = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "quality_score": score
    }
    
    audit_logs = get_audit_logs()
    pdf_bytes = export_pdf(project["name"], project.get("domain", "Retail"), dataset_summary, report, audit_logs)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=InsightForge_ExecutiveReport_{project_id[:6]}.pdf"}
    )

@app.get("/api/audit")
def get_logs():
    return get_audit_logs()

# Serve static app
@app.get("/")
def get_index():
    return FileResponse("static/index.html")

app.mount("/", StaticFiles(directory="static"), name="static")
