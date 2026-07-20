import os
import random
import datetime
import pandas as pd
from backend.parser import detect_domain

def perform_ocr(filename, file_bytes):
    """
    Simulates high-fidelity OCR with table detection, returning:
    - dataframe (pd.DataFrame)
    - domain (str)
    - text_content (str)
    """
    name = filename.lower()
    
    # 1. Determine Domain based on Filename
    if any(k in name for k in ["invoice", "receipt", "bill", "retail", "sales", "store", "order"]):
        domain = "Retail"
    elif any(k in name for k in ["finance", "financial", "balance", "profit", "bank", "revenue", "income", "tax"]):
        domain = "Finance"
    elif any(k in name for k in ["patient", "health", "medical", "clinical", "hospital", "doctor", "diagnosis"]):
        domain = "Healthcare"
    elif any(k in name for k in ["student", "education", "class", "grade", "school", "course", "exam"]):
        domain = "Education"
    elif any(k in name for k in ["manufacturing", "defect", "production", "factory", "machine", "sensor", "batch"]):
        domain = "Manufacturing"
    else:
        domain = "Retail" # Fallback default
        
    # 2. Generate appropriate structured data based on the identified domain
    data = []
    text_lines = []
    
    if domain == "Retail":
        # Generate a simulated OCR table of retail transactions
        text_lines = [
            "=================== INVOICE DETAILS ===================",
            "Store: InsightForge HyperMarket #401",
            "Address: 42 Ocean Breeze Blvd, Tech City",
            f"Date: {(datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')}",
            "Terminal: POS-09 | Operator: Sarah Connor",
            "-----------------------------------------------------",
            "SKU        Description       Qty     Price     Total",
            "SKU-491    Eco-Sphere Bulb    3      12.99     38.97",
            "SKU-882    Quantum Pad 10\"    1     299.99    299.99",
            "SKU-012    Ultra Fast Charger 2      24.50     49.00",
            "SKU-311    USB-C Steel Cable  4       9.99     39.96",
            "SKU-775    Glass screen prot  2      15.00     30.00",
            "SKU-902    Bluetooth Headset  1      89.99     89.99",
            "-----------------------------------------------------",
            "Subtotal:                                     547.91",
            "Tax (8.25%):                                   45.20",
            "Total Amount Due:                             593.11",
            "Payment Method: VISA CREDIT (xxxx-xxxx-xxxx-4491)",
            "====================================================="
        ]
        
        products = [
            ("Eco-Sphere Bulb", 12.99, "Lighting"),
            ("Quantum Pad 10\"", 299.99, "Electronics"),
            ("Ultra Fast Charger", 24.50, "Accessories"),
            ("USB-C Steel Cable", 9.99, "Accessories"),
            ("Glass screen prot", 15.00, "Accessories"),
            ("Bluetooth Headset", 89.99, "Electronics")
        ]
        
        # Build DataFrame with multiple rows to simulate a cleaned transaction report
        for i in range(1, 21):
            prod = random.choice(products)
            qty = random.randint(1, 5)
            price = prod[1]
            total = round(qty * price, 2)
            date_val = (datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
            data.append({
                "Transaction_ID": f"TXN-{1000 + i}",
                "Date": date_val,
                "Product_Name": prod[0],
                "Category": prod[2],
                "Quantity": qty,
                "Unit_Price": price,
                "Total_Amount": total,
                "Store_Location": random.choice(["Tech City", "Neo Tokyo", "Silicon Valley", "Cyber Port"]),
                "Payment_Method": random.choice(["Visa", "Mastercard", "Apple Pay", "Cash"])
            })
            
    elif domain == "Finance":
        text_lines = [
            "================= BALANCE SHEET STATEMENTS =================",
            "Entity: InsightForge Holdings Inc.",
            "Period Ending: December 31, 2025",
            "Currency: USD ($)",
            "-----------------------------------------------------------",
            "Asset Category          Sub-Category       Amount ($)",
            "Current Assets          Cash & Equivalents   1,245,600",
            "Current Assets          Accounts Receivable    480,900",
            "Current Assets          Inventory              320,000",
            "Long-Term Assets        Equipment & Property 3,450,000",
            "Long-Term Assets        Intangible Goodwill    850,000",
            "Liabilities             Accounts Payable       210,000",
            "Liabilities             Short-Term Loans       150,000",
            "Liabilities             Long-Term Debt       1,800,000",
            "Equity                  Retained Earnings    2,946,500",
            "Equity                  Common Stock         1,240,000",
            "-----------------------------------------------------------",
            "Audit Check: Passed",
            "Prepared by: FinTech Auditors LLP",
            "==========================================================="
        ]
        
        financial_items = [
            ("Current Assets", "Cash & Equivalents", 1245600),
            ("Current Assets", "Accounts Receivable", 480900),
            ("Current Assets", "Inventory", 320000),
            ("Long-Term Assets", "Equipment & Property", 3450000),
            ("Long-Term Assets", "Intangible Goodwill", 850000),
            ("Liabilities", "Accounts Payable", 210000),
            ("Liabilities", "Short-Term Loans", 150000),
            ("Liabilities", "Long-Term Debt", 1800000),
            ("Equity", "Retained Earnings", 2946500),
            ("Equity", "Common Stock", 1240000)
        ]
        
        # Build detailed balance sheets over multiple quarters for analytics
        for i, item in enumerate(financial_items):
            base_amt = item[2]
            for q in ["Q1", "Q2", "Q3", "Q4"]:
                # Introduce some slight variations (+/- 5%) across quarters
                var = random.uniform(0.95, 1.05)
                q_amt = round(base_amt * var, 2)
                data.append({
                    "Account_Category": item[0],
                    "Account_Name": item[1],
                    "Quarter": q,
                    "Amount": q_amt,
                    "Currency": "USD",
                    "Status": "Audited" if random.random() > 0.1 else "Unverified"
                })

    elif domain == "Healthcare":
        text_lines = [
            "================ CLINICAL OUTPATIENT RECORDS ================",
            "Facility: St. Jude AI Medical Center",
            "Records Range: Past 90 Days",
            "-----------------------------------------------------------",
            "PatientID    Name            Age   Diagnosis      Doctor      Billing",
            "P-0912       John Doe        45    Hypertension   Dr. Smith   $1,250",
            "P-1289       Alice Johnson   32    Diabetes Type 2 Dr. Brown   $2,100",
            "P-8801       Michael Chang   58    Cardiomyopathy Dr. Davis   $8,400",
            "P-4012       Sarah Jenkins   24    Migraine        Dr. Wilson  $450",
            "P-3101       Robert Miller   67    Osteoarthritis Dr. Miller  $1,850",
            "-----------------------------------------------------------",
            "Data Security: HIPAA Compliant, Encrypted Database",
            "==========================================================="
        ]
        
        diagnoses = [
            ("Hypertension", "Dr. Smith", 1250),
            ("Diabetes Type 2", "Dr. Brown", 2100),
            ("Cardiomyopathy", "Dr. Davis", 8400),
            ("Migraine", "Dr. Wilson", 450),
            ("Osteoarthritis", "Dr. Miller", 1850),
            ("Asthma Chronic", "Dr. Smith", 950),
            ("Bronchitis", "Dr. Wilson", 600)
        ]
        
        names = ["John Doe", "Alice Johnson", "Michael Chang", "Sarah Jenkins", "Robert Miller", "Emma Watson", "Liam Neeson", "Bruce Wayne", "Clark Kent", "Peter Parker"]
        
        for i in range(1, 26):
            diag = random.choice(diagnoses)
            age = random.randint(18, 80)
            date_val = (datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d")
            data.append({
                "Patient_ID": f"P-{1000 + i}",
                "Full_Name": random.choice(names) if i < len(names) else f"Patient {i}",
                "Age": age,
                "Admission_Date": date_val,
                "Diagnosis": diag[0],
                "Attending_Physician": diag[1],
                "Room_Number": f"Ward-{random.randint(101, 399)}",
                "Insurance_Provider": random.choice(["Blue Cross", "Aetna", "UnitedHealth", "Medicare", "None"]),
                "Billing_Amount": round(diag[2] * random.uniform(0.9, 1.2), 2)
            })

    elif domain == "Education":
        text_lines = [
            "================ STUDENT ACADEMIC SCORE SHEET ================",
            "Institution: Neo-Academy of Science & Technology",
            "Semester: Fall 2025 | Class: Advanced Statistics",
            "-------------------------------------------------------------",
            "StudentID  Student Name    Subject        Grade  Attendance Remarks",
            "ST-101     Alan Turing     Data Science   98     99%        Excellent",
            "ST-102     Ada Lovelace    Coding Theory  97     98%        Outstanding",
            "ST-103     Grace Hopper    Compiler Opt   94     95%        Superb",
            "ST-104     John McCarthy   Artificial Int 91     92%        Highly Comm.",
            "ST-105     Claude Shannon  Info Theory    96     96%        Excellent",
            "-------------------------------------------------------------",
            "Prepared by: Registrar Department",
            "============================================================="
        ]
        
        students = ["Alan Turing", "Ada Lovelace", "Grace Hopper", "John McCarthy", "Claude Shannon", "Nikola Tesla", "Marie Curie", "Albert Einstein", "Richard Feynman", "Stephen Hawking"]
        subjects = ["Data Science", "Coding Theory", "Compiler Opt", "Artificial Int", "Info Theory"]
        
        for i, name in enumerate(students):
            for sub in subjects:
                score = random.randint(65, 100)
                att = random.randint(80, 100)
                if score >= 90:
                    grade = "A"
                    remarks = "Excellent"
                elif score >= 80:
                    grade = "B"
                    remarks = "Good Progress"
                elif score >= 70:
                    grade = "C"
                    remarks = "Average"
                else:
                    grade = "D"
                    remarks = "Needs Help"
                    
                data.append({
                    "Student_ID": f"ST-10{i+1}",
                    "Student_Name": name,
                    "Subject": sub,
                    "Test_Score": score,
                    "Attendance_Rate": att,
                    "Grade_Letter": grade,
                    "Remarks": remarks
                })
                
    elif domain == "Manufacturing":
        text_lines = [
            "================ FACTORY OEE & DEFECT REPORT ================",
            "Location: Plant 7 - Assembly Line Alpha",
            "Shift: Night Shift | Manager: Marcus Vance",
            "-----------------------------------------------------------",
            "BatchID   MachineID  Operator   UnitsProduced DefectCount Status",
            "BT-901    CNC-01     Jane Doe   1,200         4           Pass",
            "BT-902    CNC-02     Bob Smith  980           18          Warning",
            "BT-903    ROBO-01    Auto-Sys   3,400         2           Pass",
            "BT-904    LASER-09   Carl Jones 550           12          Warning",
            "BT-905    CNC-01     Jane Doe   1,150         3           Pass",
            "-----------------------------------------------------------",
            "Audit Status: Factory Standard Met",
            "==========================================================="
        ]
        
        machines = ["CNC-01", "CNC-02", "ROBO-01", "LASER-09", "PRESS-04"]
        operators = ["Jane Doe", "Bob Smith", "Auto-Sys", "Carl Jones", "Alice Green"]
        
        for i in range(1, 21):
            mach = random.choice(machines)
            op = "Auto-Sys" if "ROBO" in mach else random.choice(operators)
            produced = random.randint(500, 4000)
            defects = int(produced * random.uniform(0.001, 0.03)) if "ROBO" in mach else int(produced * random.uniform(0.005, 0.05))
            def_rate = round((defects / produced) * 100, 2)
            status = "Pass" if def_rate < 2.0 else ("Warning" if def_rate < 4.0 else "Fail")
            
            data.append({
                "Batch_ID": f"BT-90{i}",
                "Production_Line": "Line Alpha" if i % 2 == 0 else "Line Beta",
                "Machine_ID": mach,
                "Units_Produced": produced,
                "Defect_Count": defects,
                "Defect_Rate_Pct": def_rate,
                "Operator_Name": op,
                "Machine_Run_Hours": round(random.uniform(4.0, 12.0), 1),
                "Quality_Status": status
            })

    df = pd.DataFrame(data)
    text_content = "\n".join(text_lines)
    
    return df, domain, text_content
