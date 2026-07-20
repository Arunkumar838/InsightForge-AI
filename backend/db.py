import os
import json
import datetime
import uuid
import threading
import shutil

import tempfile

IS_VERCEL = os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV") is not None

if IS_VERCEL:
    DB_DIR = os.path.join(tempfile.gettempdir(), ".insightforge_db")
else:
    DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".insightforge_db")

USERS_FILE = os.path.join(DB_DIR, "users.json")
PROJECTS_FILE = os.path.join(DB_DIR, "projects.json")
AUDIT_LOGS_FILE = os.path.join(DB_DIR, "audit_logs.json")

# Reentrant lock to prevent multi-thread write conflicts
db_lock = threading.RLock()

def sanitize_nan(val):
    if isinstance(val, float):
        if val != val or val == float('inf') or val == float('-inf'):
            return None
        return val
    elif isinstance(val, dict):
        return {k: sanitize_nan(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [sanitize_nan(x) for x in val]
    return val

def ensure_db():
    with db_lock:
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
        
        # Overwrite users with only Admin role to remove viewer and analyst options
        admin_user = {
            "admin": {
                "username": "admin",
                "password_hash": "admin123",
                "role": "Admin",
                "fullname": "System Administrator",
                "api_key": "if_admin_live_key_9901"
            }
        }
        with open(USERS_FILE, "w") as f:
            json.dump(admin_user, f, indent=4)
                
        # Initialize projects
        if not os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, "w") as f:
                json.dump({}, f, indent=4)
        else:
            # Clean existing projects.json from invalid floats, or recover if corrupted
            try:
                with open(PROJECTS_FILE, "r") as f:
                    projects = json.load(f)
                sanitized = sanitize_nan(projects)
                with open(PROJECTS_FILE, "w") as f:
                    json.dump(sanitized, f, indent=4)
            except Exception:
                try:
                    shutil.move(PROJECTS_FILE, PROJECTS_FILE + ".corrupted")
                except Exception:
                    pass
                with open(PROJECTS_FILE, "w") as f:
                    json.dump({}, f, indent=4)
                
        # Initialize audit logs
        if not os.path.exists(AUDIT_LOGS_FILE):
            with open(AUDIT_LOGS_FILE, "w") as f:
                json.dump([], f, indent=4)

ensure_db()

# User Management
def authenticate_user(username, password):
    ensure_db()
    with db_lock:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        if username in users and users[username]["password_hash"] == password:
            user_info = users[username].copy()
            user_info.pop("password_hash")
            return user_info
        return None

def verify_api_key(api_key):
    ensure_db()
    with db_lock:
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        for username, data in users.items():
            if data.get("api_key") == api_key:
                return {"username": username, "role": data["role"]}
        return None

# Project Management
def list_projects():
    ensure_db()
    with db_lock:
        with open(PROJECTS_FILE, "r") as f:
            return json.load(f)

def _write_projects(projects):
    sanitized = sanitize_nan(projects)
    temp_file = PROJECTS_FILE + ".tmp"
    with db_lock:
        with open(temp_file, "w") as f:
            json.dump(sanitized, f, indent=4)
        # Atomic rename to prevent database corruption under concurrency
        shutil.move(temp_file, PROJECTS_FILE)
    return sanitized

def get_project(project_id):
    ensure_db()
    with db_lock:
        projects = list_projects()
        project = projects.get(project_id)
        if not project:
            return None
        
        project = project.copy()
        # Dynamically load the active dataset from its separate file if needed
        if "active_dataset_file" in project and os.path.exists(project["active_dataset_file"]):
            try:
                with open(project["active_dataset_file"], "r") as f:
                    project["active_dataset"] = json.load(f)
            except Exception:
                project["active_dataset"] = []
        else:
            if "active_dataset" not in project:
                project["active_dataset"] = []
            
        # Dynamically populate the versioned datasets if needed
        if "datasets" in project:
            project["datasets"] = project["datasets"].copy()
            for ver, dataset_val in project["datasets"].items():
                dataset_val = dataset_val.copy()
                if "data_file" in dataset_val and os.path.exists(dataset_val["data_file"]):
                    try:
                        with open(dataset_val["data_file"], "r") as f:
                            dataset_val["data"] = json.load(f)
                    except Exception:
                        dataset_val["data"] = []
                else:
                    if "data" not in dataset_val:
                        dataset_val["data"] = []
                project["datasets"][ver] = dataset_val
                
        return project

def save_project(project_id, project_data):
    ensure_db()
    with db_lock:
        projects = list_projects()
        
        project_to_save = project_data.copy()
        # Decouple the large active dataset to a separate file
        if "active_dataset" in project_to_save and project_to_save["active_dataset"] is not None:
            dataset_dir = os.path.join(DB_DIR, "datasets")
            os.makedirs(dataset_dir, exist_ok=True)
            
            # Use version-based filename or general active filename
            ver = project_to_save.get("current_version", 0)
            dataset_file = os.path.join(dataset_dir, f"{project_id}_v{ver}.json")
            
            # Write dataset file atomically
            temp_dataset_file = dataset_file + ".tmp"
            with open(temp_dataset_file, "w") as f:
                json.dump(sanitize_nan(project_to_save["active_dataset"]), f)
            shutil.move(temp_dataset_file, dataset_file)
            
            project_to_save["active_dataset_file"] = dataset_file
            project_to_save.pop("active_dataset")
            
        # Decouple the versioned datasets data field
        if "datasets" in project_to_save:
            project_to_save["datasets"] = project_to_save["datasets"].copy()
            for ver, dataset_val in project_to_save["datasets"].items():
                dataset_val = dataset_val.copy()
                if "data" in dataset_val and dataset_val["data"] is not None:
                    dataset_dir = os.path.join(DB_DIR, "datasets")
                    os.makedirs(dataset_dir, exist_ok=True)
                    dataset_file = os.path.join(dataset_dir, f"{project_id}_v{ver}.json")
                    
                    if not os.path.exists(dataset_file):
                        temp_dataset_file = dataset_file + ".tmp"
                        with open(temp_dataset_file, "w") as f:
                            json.dump(sanitize_nan(dataset_val["data"]), f)
                        shutil.move(temp_dataset_file, dataset_file)
                        
                    dataset_val["data_file"] = dataset_file
                    dataset_val.pop("data")
                project_to_save["datasets"][ver] = dataset_val
                
        projects[project_id] = project_to_save
        _write_projects(projects)
        return project_data

def create_project(name, description, owner):
    project_id = str(uuid.uuid4())
    project_data = {
        "id": project_id,
        "name": name,
        "description": description,
        "owner": owner,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "files": [],
        "datasets": {}, # Version number -> dataset preview and stats
        "current_version": 0,
        "active_dataset": None, # JSON-serialized DataFrame
        "domain": "Unknown",
        "doc_type": "Unknown",
        "cleaning_history": [],
        "models": {},
        "simulator_state": {}
    }
    save_project(project_id, project_data)
    log_audit(owner, "CREATE_PROJECT", f"Created project {name} ({project_id})")
    return project_data

def delete_project(project_id, username):
    ensure_db()
    projects = list_projects()
    if project_id in projects:
        name = projects[project_id]["name"]
        del projects[project_id]
        _write_projects(projects)
        log_audit(username, "DELETE_PROJECT", f"Deleted project {name} ({project_id})")
        return True
    return False

# Dataset Versioning
def add_dataset_version(project_id, username, dataset_json, comment, file_metadata=None):
    project = get_project(project_id)
    if not project:
        return None
    
    new_version = project["current_version"] + 1
    project["current_version"] = new_version
    
    version_entry = {
        "version": new_version,
        "created_at": datetime.datetime.now().isoformat(),
        "created_by": username,
        "comment": comment,
        "row_count": len(dataset_json) if dataset_json else 0,
        "column_count": len(dataset_json[0].keys()) if dataset_json and len(dataset_json) > 0 else 0
    }
    
    project["datasets"][str(new_version)] = {
        "metadata": version_entry,
        "data": dataset_json
    }
    
    project["active_dataset"] = dataset_json
    project["updated_at"] = datetime.datetime.now().isoformat()
    
    if file_metadata:
        project["files"].append(file_metadata)
        
    save_project(project_id, project)
    log_audit(username, "ADD_DATASET_VERSION", f"Added version {new_version} to project {project['name']}: {comment}")
    return project

# Audit Logging
def log_audit(user, action, details):
    ensure_db()
    log_entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.now().isoformat(),
        "user": user,
        "action": action,
        "details": details
    }
    with db_lock:
        try:
            with open(AUDIT_LOGS_FILE, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []
        
        logs.append(log_entry)
        # Keep the last 1000 logs
        if len(logs) > 1000:
            logs = logs[-1000:]
            
        temp_file = AUDIT_LOGS_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(logs, f, indent=4)
        shutil.move(temp_file, AUDIT_LOGS_FILE)

def get_audit_logs():
    ensure_db()
    with db_lock:
        try:
            with open(AUDIT_LOGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
