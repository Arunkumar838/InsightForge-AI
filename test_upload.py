import requests
import pandas as pd
import numpy as np
import io
import time
import os

# Create 50MB CSV
print("Generating 50MB CSV...")
# 500,000 rows, 10 columns -> approx 50MB
df = pd.DataFrame(np.random.rand(500000, 10), columns=[f"col_{i}" for i in range(10)])
csv_data = df.to_csv(index=False)
print(f"Generated CSV size: {len(csv_data) / 1024 / 1024:.2f} MB")

# Mock the project creation
print("Creating project...")
res = requests.post("http://localhost:8000/api/projects", json={
    "name": "Test 50MB",
    "description": "Testing large uploads",
    "owner": "admin"
})
project_id = res.json()["id"]
print(f"Project ID: {project_id}")

# Simulate chunked upload like app.js
lines = csv_data.split("\n")
header_line = lines[0]
chunk_size = 2500

print("Starting chunked upload...")
start_time = time.time()
for i in range(1, len(lines), chunk_size):
    chunk_lines = lines[i:i+chunk_size]
    if not chunk_lines or (len(chunk_lines) == 1 and chunk_lines[0].strip() == ""):
        continue
        
    chunk_text = header_line + "\n" + "\n".join(chunk_lines)
    
    # Simulate Vercel 4.5MB limit
    if len(chunk_text.encode('utf-8')) > 4.5 * 1024 * 1024:
        print(f"FAILED: Chunk size is {len(chunk_text.encode('utf-8')) / 1024 / 1024:.2f} MB! Exceeds 4.5MB!")
        exit(1)
        
    res = requests.post(f"http://localhost:8000/api/projects/{project_id}/upload_json", json={
        "filename": "test_50mb.csv",
        "doc_type": "CSV Spreadsheet",
        "text": chunk_text,
        "username": "admin",
        "append": i > 1
    })
    
    if not res.ok:
        print(f"Upload failed: {res.text}")
        exit(1)
    
    print(f"Uploaded chunk {(i // chunk_size) + 1} / {len(lines) // chunk_size}")

print(f"Upload complete in {time.time() - start_time:.2f} seconds!")

# Verify dataset size
res = requests.get(f"http://localhost:8000/api/projects/{project_id}")
project = res.json()
print(f"Active dataset length: {len(project['active_dataset'])}")
if len(project['active_dataset']) == 500000:
    print("SUCCESS: Full 50MB dataset was successfully uploaded and assembled!")
else:
    print("FAILED: Dataset size mismatch!")
