// Master Application Manager for InsightForge AI
const App = {
    activeProjectId: null,
    projectData: null,
    numericCols: [],
    categoricalCols: [],
    dateCols: [],

    init() {
        // Initialize authentication
        const isLoggedIn = Auth.init();
        
        if (isLoggedIn) {
            this.onLogin();
        }

        // Initialize chart zoom event bindings
        Charts.bindEvents();

        // Sidebar Navigation
        const navItems = document.querySelectorAll(".nav-item");
        navItems.forEach(item => {
            item.onclick = (e) => {
                e.preventDefault();
                const tab = item.getAttribute("data-tab");
                this.switchTab(tab);
            };
        });

        // Modals listeners
        document.getElementById("new-project-btn").onclick = () => {
            document.getElementById("new-project-modal").style.display = "flex";
        };
        document.getElementById("new-project-cancel-btn").onclick = () => {
            document.getElementById("new-project-modal").style.display = "none";
        };
        
        // New project form submission
        document.getElementById("new-project-form").onsubmit = async (e) => {
            e.preventDefault();
            const name = document.getElementById("new-project-name").value;
            const desc = document.getElementById("new-project-desc").value;
            const owner = Auth.currentUser ? Auth.currentUser.username : "admin";
            
            try {
                const response = await fetch("/api/projects", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, description: desc, owner })
                });
                
                if (response.ok) {
                    const newProj = await response.json();
                    document.getElementById("new-project-modal").style.display = "none";
                    document.getElementById("new-project-name").value = "";
                    document.getElementById("new-project-desc").value = "";
                    await this.loadProjects(newProj.id);
                }
            } catch (err) {
                console.error("Failed to create project:", err);
            }
        };

        // Project select change
        document.getElementById("active-project-select").onchange = (e) => {
            const val = e.target.value;
            if (val) {
                this.selectProject(val);
            } else {
                this.activeProjectId = null;
                document.getElementById("project-dashboard-content").style.display = "none";
                document.getElementById("no-project-alert").style.display = "flex";
            }
        };

        // File Uploader click & drag drop
        const dropzone = document.getElementById("dropzone");
        const fileInput = document.getElementById("file-uploader");
        
        dropzone.onclick = () => fileInput.click();
        
        fileInput.onchange = (e) => {
            const file = e.target.files[0];
            if (file) this.uploadFile(file);
        };

        dropzone.ondragover = (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        };
        
        dropzone.ondragleave = () => {
            dropzone.classList.remove("dragover");
        };
        
        dropzone.ondrop = (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
            const file = e.dataTransfer.files[0];
            if (file) this.uploadFile(file);
        };

        // Cleaning Form trigger
        document.getElementById("cleaning-config-form").onsubmit = (e) => {
            e.preventDefault();
            this.runCleaningPipeline();
        };

        // ML train button
        document.getElementById("train-ml-btn").onclick = () => {
            this.trainMLModel();
        };

        // TS forecast button
        document.getElementById("forecast-ts-btn").onclick = () => {
            this.runForecasting();
        };

        // Export endpoints link setup
        this.setupExporters();
    },

    onLogin() {
        this.loadProjects();
        this.loadAuditLogs();
        this.switchTab("dashboard");
    },

    async loadProjects(selectId = null) {
        try {
            const response = await fetch("/api/projects");
            if (!response.ok) throw new Error("Projects fetch error");
            
            const projects = await response.json();
            const select = document.getElementById("active-project-select");
            
            // Keep first option
            select.innerHTML = '<option value="">-- Select Project --</option>';
            
            projects.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.innerText = p.name;
                select.appendChild(opt);
            });

            // Auto-select first or specified project
            if (selectId) {
                select.value = selectId;
                this.selectProject(selectId);
            } else if (projects.length > 0) {
                select.value = projects[0].id;
                this.selectProject(projects[0].id);
            }
        } catch (e) {
            console.error("Load projects failed", e);
        }
    },

    async selectProject(id) {
        this.activeProjectId = id;
        document.getElementById("no-project-alert").style.display = "none";
        document.getElementById("project-dashboard-content").style.display = "block";
        
        await this.refreshProjectData();
    },

    async refreshProjectData() {
        if (!this.activeProjectId) return;

        try {
            const response = await fetch(`/api/projects/${this.activeProjectId}`);
            if (!response.ok) throw new Error("Project refresh error");
            
            const p = await response.json();
            this.projectData = p;
            
            // 1. Update general project metadata diagnostics
            document.getElementById("meta-doc-type").innerText = p.doc_type || "-";
            document.getElementById("meta-domain").innerText = p.domain || "-";
            
            const history = p.cleaning_history || [];
            const score = history.length > 0 ? history[history.length - 1].score_after : 95.0;
            document.getElementById("meta-quality-score").innerText = `${score}/100`;
            document.getElementById("meta-quality-bar").style.width = `${score}%`;

            const activeDataset = p.active_dataset;
            if (activeDataset && activeDataset.length > 0) {
                document.getElementById("meta-rows-count").innerText = activeDataset.length;
                
                const sampleRow = activeDataset[0];
                const cols = Object.keys(sampleRow);
                document.getElementById("meta-columns-count").innerText = cols.length;
                document.getElementById("active-dataset-version-badge").innerText = `Version ${p.current_version}`;
                
                // Categorize columns
                const profile = Charts.getColumnsProfile(activeDataset);
                this.numericCols = profile.numeric;
                this.categoricalCols = profile.categorical;
                this.dateCols = profile.date;

                // Render preview table
                this.renderPreviewTable(activeDataset, cols);
                
                // Populate ML & forecasting parameters lists
                this.populateParametersSelects();

                // Render Visualizations charts
                Charts.renderDashboardCharts(activeDataset, p.domain);

                // Initialize simulator values
                Simulator.init(this.activeProjectId, this.numericCols);

                // Initialize agent chat workspace
                Chat.init(this.activeProjectId);
            } else {
                document.getElementById("meta-rows-count").innerText = "0";
                document.getElementById("meta-columns-count").innerText = "0";
                document.getElementById("active-dataset-version-badge").innerText = "Version 0";
                this.resetPreviewTable();
            }

            // Setup download attributes
            this.setupExporters();
            
        } catch (e) {
            console.error("Select project data failed", e);
        }
    },

    renderPreviewTable(data, cols) {
        const thead = document.querySelector("#dataset-preview-table thead");
        const tbody = document.querySelector("#dataset-preview-table tbody");
        
        thead.innerHTML = "";
        tbody.innerHTML = "";
        
        // Header
        const thr = document.createElement("tr");
        cols.forEach(col => {
            const th = document.createElement("th");
            th.innerText = col;
            thr.appendChild(th);
        });
        thead.appendChild(thr);
        
        // Rows (cap to 10 for performance)
        data.slice(0, 10).forEach(row => {
            const tr = document.createElement("tr");
            cols.forEach(col => {
                const td = document.createElement("td");
                const val = row[col];
                td.innerText = val !== null && val !== undefined ? val : "NULL";
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    },

    resetPreviewTable() {
        const thead = document.querySelector("#dataset-preview-table thead");
        const tbody = document.querySelector("#dataset-preview-table tbody");
        thead.innerHTML = "<tr><th>No data loaded</th></tr>";
        tbody.innerHTML = "<tr><td>Please ingest a structured file or receipt image to begin.</td></tr>";
    },

    populateParametersSelects() {
        // Target select
        const targetSelect = document.getElementById("ml-target-col");
        const currentTarget = targetSelect.value;
        targetSelect.innerHTML = "";
        this.numericCols.forEach(col => {
            const opt = document.createElement("option");
            opt.value = col;
            opt.innerText = col;
            if (col === currentTarget) opt.selected = true;
            targetSelect.appendChild(opt);
        });
        if (this.numericCols.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.innerText = "-- Upload a dataset first --";
            targetSelect.appendChild(opt);
        }

        // Features list checkboxes
        const featCont = document.getElementById("ml-features-container");
        const checkedFeats = new Set(
            Array.from(document.querySelectorAll("input[name='ml-feature']:checked")).map(cb => cb.value)
        );
        const hasExistingSelection = checkedFeats.size > 0;

        featCont.innerHTML = "";
        const allFeats = [...this.numericCols, ...this.categoricalCols];
        allFeats.forEach(col => {
            const isChecked = hasExistingSelection ? checkedFeats.has(col) : true;
            const label = document.createElement("label");
            label.innerHTML = `<input type="checkbox" name="ml-feature" value="${col}" ${isChecked ? 'checked' : ''}> ${col}`;
            featCont.appendChild(label);
        });
        if (allFeats.length === 0) {
            featCont.innerHTML = "<p class='micro-text text-gray' style='padding: 6px;'>No dataset columns found. Please upload a dataset in the Dashboard tab first.</p>";
        }

        // Time series date select
        const dateSelect = document.getElementById("ts-date-col");
        const currentDate = dateSelect.value;
        dateSelect.innerHTML = "";
        const allDateOptions = [...this.dateCols, ...this.categoricalCols];
        allDateOptions.forEach(col => {
            const opt = document.createElement("option");
            opt.value = col;
            opt.innerText = col;
            if (col === currentDate) opt.selected = true;
            dateSelect.appendChild(opt);
        });
        if (allDateOptions.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.innerText = "-- Upload a dataset first --";
            dateSelect.appendChild(opt);
        }

        // Time series value select
        const valSelect = document.getElementById("ts-value-col");
        const currentVal = valSelect.value;
        valSelect.innerHTML = "";
        this.numericCols.forEach(col => {
            const opt = document.createElement("option");
            opt.value = col;
            opt.innerText = col;
            if (col === currentVal) opt.selected = true;
            valSelect.appendChild(opt);
        });
        if (this.numericCols.length === 0) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.innerText = "-- Upload a dataset first --";
            valSelect.appendChild(opt);
        }
    },

    async uploadFile(file) {
        if (!this.activeProjectId) return;

        const uploaderContainer = document.getElementById("upload-progress-bar-container");
        const progressBar = document.getElementById("upload-progress-bar");
        const progressLabel = document.getElementById("upload-progress-label");
        
        uploaderContainer.style.display = "block";
        progressBar.style.width = "10%";
        progressLabel.innerText = "Processing file payload...";

        const username = Auth.currentUser ? Auth.currentUser.username : "admin";
        const fname = file.name.toLowerCase();

        try {
            let response = null;
            let uploadSuccess = false;
            
            // Tier 1: Client-side Excel parsing if SheetJS is available
            if ((fname.endsWith(".xlsx") || fname.endsWith(".xls") || fname.endsWith(".xlsm") || fname.endsWith(".ods")) && typeof XLSX !== "undefined") {
                try {
                    progressBar.style.width = "30%";
                    progressLabel.innerText = "Parsing Excel workbook...";
                    
                    const arrayBuffer = await file.arrayBuffer();
                    const workbook = XLSX.read(arrayBuffer, { type: "array" });
                    if (workbook && workbook.SheetNames && workbook.SheetNames.length > 0) {
                        const firstSheetName = workbook.SheetNames[0];
                        const worksheet = workbook.Sheets[firstSheetName];
                        const rawJson = XLSX.utils.sheet_to_json(worksheet);
                        
                        if (rawJson && rawJson.length > 0) {
                            progressBar.style.width = "60%";
                            progressLabel.innerText = "Transmitting Excel data...";
                            
                            const MAX_PAYLOAD_BYTES = 3.5 * 1024 * 1024;
                            let currentChunk = [];
                            let currentChunkBytes = 0;
                            let chunkIndex = 0;
                            
                            for (let i = 0; i < rawJson.length; i++) {
                                const row = rawJson[i];
                                const rowBytes = new Blob([JSON.stringify(row)]).size + 2;
                                
                                if (currentChunkBytes + rowBytes > MAX_PAYLOAD_BYTES && currentChunk.length > 0) {
                                    response = await fetch(`/api/projects/${this.activeProjectId}/upload_json`, {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({
                                            filename: file.name,
                                            doc_type: "Excel Spreadsheet",
                                            data: currentChunk,
                                            username: username,
                                            append: chunkIndex > 0
                                        })
                                    });
                                    if (!response.ok) break;
                                    chunkIndex++;
                                    progressBar.style.width = `${60 + (i / rawJson.length) * 30}%`;
                                    currentChunk = [];
                                    currentChunkBytes = 0;
                                }
                                
                                currentChunk.push(row);
                                currentChunkBytes += rowBytes;
                            }
                            
                            if (currentChunk.length > 0 && (!response || response.ok)) {
                                response = await fetch(`/api/projects/${this.activeProjectId}/upload_json`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({
                                        filename: file.name,
                                        doc_type: "Excel Spreadsheet",
                                        data: currentChunk,
                                        username: username,
                                        append: chunkIndex > 0
                                    })
                                });
                            }
                            if (response && response.ok) {
                                uploadSuccess = true;
                            }
                        }
                    }
                } catch (excelErr) {
                    console.warn("Client-side Excel parse failed, falling back to server parser:", excelErr);
                }
            }

            // Tier 2: Client-side CSV parsing if not handled
            if (!uploadSuccess && (fname.endsWith(".csv") || fname.endsWith(".txt") || fname.endsWith(".tsv"))) {
                try {
                    progressBar.style.width = "30%";
                    progressLabel.innerText = "Reading CSV stream...";
                    
                    const text = await file.text();
                    const lines = text.split(/\r?\n/);
                    if (lines.length > 0 && lines[0].trim() !== "") {
                        const headerLine = lines[0];
                        progressBar.style.width = "60%";
                        progressLabel.innerText = "Transmitting CSV data...";
                        
                        const MAX_PAYLOAD_BYTES = 3.5 * 1024 * 1024;
                        let currentChunkLines = [];
                        let currentChunkBytes = 0;
                        let chunkIndex = 0;
                        
                        for (let i = 1; i < lines.length; i++) {
                            const line = lines[i];
                            if (line.trim() === "") continue;
                            
                            const lineBytes = new Blob([line]).size;
                            
                            if (currentChunkBytes + lineBytes > MAX_PAYLOAD_BYTES && currentChunkLines.length > 0) {
                                const chunkText = [headerLine, ...currentChunkLines].join("\n");
                                response = await fetch(`/api/projects/${this.activeProjectId}/upload_json`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({
                                        filename: file.name,
                                        doc_type: "CSV Spreadsheet",
                                        text: chunkText,
                                        username: username,
                                        append: chunkIndex > 0
                                    })
                                });
                                if (!response.ok) break;
                                chunkIndex++;
                                progressBar.style.width = `${60 + (i / lines.length) * 30}%`;
                                currentChunkLines = [];
                                currentChunkBytes = 0;
                            }
                            
                            currentChunkLines.push(line);
                            currentChunkBytes += lineBytes;
                        }
                        
                        if (currentChunkLines.length > 0 && (!response || response.ok)) {
                            const chunkText = [headerLine, ...currentChunkLines].join("\n");
                            response = await fetch(`/api/projects/${this.activeProjectId}/upload_json`, {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    filename: file.name,
                                    doc_type: "CSV Spreadsheet",
                                    text: chunkText,
                                    username: username,
                                    append: chunkIndex > 0
                                })
                            });
                        }
                        if (response && response.ok) {
                            uploadSuccess = true;
                        }
                    }
                } catch (csvErr) {
                    console.warn("Client-side CSV parse failed, falling back to server parser:", csvErr);
                }
            }

            // Tier 3: Universal Chunked Binary Upload to Python Server (Handles Excel, CSV, PDF, Docx, SQL, Images, etc.)
            if (!uploadSuccess) {
                progressBar.style.width = "20%";
                progressLabel.innerText = "Transmitting file to analytical engine...";
                
                const chunkSize = 3.5 * 1024 * 1024; // 3.5MB per chunk
                const totalChunks = Math.ceil(file.size / chunkSize);
                
                for (let i = 0; i < totalChunks; i++) {
                    const chunk = file.slice(i * chunkSize, (i + 1) * chunkSize);
                    const formData = new FormData();
                    formData.append("file", chunk, file.name);
                    formData.append("username", username);
                    formData.append("chunk_index", i);
                    formData.append("total_chunks", totalChunks);
                    
                    response = await fetch(`/api/projects/${this.activeProjectId}/upload_chunk`, {
                        method: "POST",
                        body: formData
                    });
                    
                    if (!response.ok) break;
                    progressBar.style.width = `${20 + ((i + 1) / totalChunks) * 70}%`;
                }
            }

            progressBar.style.width = "90%";
            progressLabel.innerText = "Assembling virtual columns...";

            if (!response || !response.ok) {
                let errDetail = "Parse Failed";
                if (response) {
                    try {
                        const err = await response.json();
                        errDetail = err.detail || errDetail;
                    } catch (jsonErr) {
                        if (response.status === 413) {
                            errDetail = "File payload is too large. Please select a file under 50MB.";
                        } else {
                            const rawText = await response.text();
                            errDetail = rawText ? rawText.substring(0, 120) : `HTTP ${response.status} Error`;
                        }
                    }
                }
                throw new Error(errDetail);
            }

            const res = await response.json();
            
            progressBar.style.width = "100%";
            progressLabel.innerText = "Success! Forge operational.";

            setTimeout(() => {
                uploaderContainer.style.display = "none";
                this.refreshProjectData();
                this.loadAuditLogs();
            }, 800);

        } catch (e) {
            progressBar.style.width = "0%";
            progressLabel.innerText = `Error: ${e.message}`;
            console.error("Upload failed:", e);
        }
    },

    async runCleaningPipeline() {
        if (!this.activeProjectId) return;

        const config = {
            remove_duplicates: document.getElementById("clean-duplicates").checked,
            handle_missing: document.getElementById("clean-missing").checked,
            correct_dates: document.getElementById("clean-dates").checked,
            detect_outliers: document.getElementById("clean-outliers").checked,
            standardize_units: document.getElementById("clean-units").checked
        };

        const placeholder = document.getElementById("cleaning-operations-empty");
        const resultsBlock = document.getElementById("cleaning-operations-results");
        
        placeholder.innerHTML = "<p><i class='fa-solid fa-spinner fa-spin'></i> Purifying data cells, removing noise...</p>";
        resultsBlock.style.display = "none";

        try {
            const response = await fetch(`/api/projects/${this.activeProjectId}/clean`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(config)
            });

            if (!response.ok) throw new Error("Cleaning endpoint issue");

            const res = await response.json();
            
            // Render results audit log
            placeholder.style.display = "none";
            resultsBlock.style.display = "block";
            
            document.getElementById("clean-result-score").innerText = `${res.quality_score}/100`;
            
            // Standardizations
            const stdUl = document.getElementById("clean-report-standardized");
            stdUl.innerHTML = "";
            res.report.standardizations.forEach(item => {
                stdUl.insertAdjacentHTML('beforeend', `<li>${item}</li>`);
            });
            res.report.dates_standardized.forEach(col => {
                stdUl.insertAdjacentHTML('beforeend', `<li>Aligned date formats in column '${col}' to YYYY-MM-DD.</li>`);
            });
            if (res.report.standardizations.length === 0 && res.report.dates_standardized.length === 0) {
                stdUl.innerHTML = "<li>No standardizations needed.</li>";
            }

            // Imputations
            const impUl = document.getElementById("clean-report-imputed");
            impUl.innerHTML = "";
            Object.keys(res.report.missing_imputed).forEach(col => {
                const details = res.report.missing_imputed[col];
                impUl.insertAdjacentHTML('beforeend', `<li>Column '${col}': Imputed ${details.count} missing cells using ${details.strategy}.</li>`);
            });
            if (Object.keys(res.report.missing_imputed).length === 0) {
                impUl.innerHTML = "<li>No missing values detected.</li>";
            }

            // Outliers
            const outUl = document.getElementById("clean-report-outliers");
            outUl.innerHTML = "";
            Object.keys(res.report.outliers_detected).forEach(col => {
                const details = res.report.outliers_detected[col];
                outUl.insertAdjacentHTML('beforeend', `<li>Column '${col}': Capped ${details.count} statistical outliers bounds.</li>`);
            });
            if (Object.keys(res.report.outliers_detected).length === 0) {
                outUl.innerHTML = "<li>No anomalies / statistical outliers flagged.</li>";
            }

            // Refresh preview
            await this.refreshProjectData();
            await this.loadAuditLogs();

        } catch (e) {
            console.error("Clean failed:", e);
            placeholder.innerHTML = `<p class="text-red">⚠️ Pipeline failed: ${e.message}</p>`;
        }
    },

    async trainMLModel() {
        if (!this.activeProjectId) return;

        const targetSelect = document.getElementById("ml-target-col");
        const modelSelect = document.getElementById("ml-model-type");
        const target = targetSelect.value;
        const modelType = modelSelect.value;

        if (!target) {
            alert("No target variable selected. Please upload a dataset in the Dashboard tab first.");
            return;
        }

        // Get checked features
        const featureCheckboxes = document.querySelectorAll("input[name='ml-feature']:checked");
        const features = Array.from(featureCheckboxes).map(cb => cb.value).filter(val => val !== target);

        if (features.length === 0) {
            alert("Please select at least one feature column (X) to train the model.");
            return;
        }

        const resultsBlock = document.getElementById("ml-results-block");
        resultsBlock.style.display = "none";
        
        const trainBtn = document.getElementById("train-ml-btn");
        const oldBtnHtml = trainBtn.innerHTML;
        trainBtn.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i> Fitting weights...";
        trainBtn.disabled = true;

        try {
            const username = Auth.currentUser ? Auth.currentUser.username : "admin";
            const response = await fetch(`/api/projects/${this.activeProjectId}/train`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    target_col: target,
                    feature_cols: features,
                    model_type: modelType,
                    username: username
                })
            });

            trainBtn.innerHTML = oldBtnHtml;
            trainBtn.disabled = false;

            if (!response.ok) throw new Error("ML train endpoint error");

            const results = await response.json();
            resultsBlock.style.display = "block";
            
            // Metrics
            const confPct = Math.round(results.metrics.confidence * 100);
            document.getElementById("ml-res-confidence").innerText = `${confPct}%`;
            
            const metricName = results.is_classification ? "Accuracy Score" : "R-squared Variance";
            const metricVal = results.is_classification ? results.metrics.accuracy : results.metrics.r2;
            document.getElementById("ml-res-metric-name").innerText = metricName;
            document.getElementById("ml-res-metric-val").innerText = metricVal.toFixed(4);

            // Render prediction comparison chart
            const activeDataset = this.projectData.active_dataset;
            // Get actual target column array
            const actualValues = activeDataset.slice(0, 50).map(item => parseFloat(item[target]) || 0);
            
            Charts.renderMLPredictions(actualValues, results.predictions, target, "chart-ml-predictions");

            // Draw SHAP explainer bars
            this.drawShapBars(results.shap);
            
            await this.loadAuditLogs();

        } catch (e) {
            trainBtn.innerHTML = oldBtnHtml;
            trainBtn.disabled = false;
            console.error("ML failed", e);
            alert(`Training failed: ${e.message}`);
        }
    },

    drawShapBars(shap) {
        const container = document.getElementById("shap-bars-container");
        container.innerHTML = "";
        
        const shapVals = shap.shap_values;
        const maxVal = Math.max(...Object.values(shapVals).map(v => Math.abs(v))) || 1.0;
        
        Object.keys(shapVals).forEach(feat => {
            const val = shapVals[feat];
            const pct = Math.abs(val / maxVal) * 100;
            const signClass = val >= 0 ? "positive" : "negative";
            const signText = val >= 0 ? "+" : "";

            const row = document.createElement("div");
            row.className = "shap-row";
            row.innerHTML = `
                <span class="shap-feat-name" title="${feat}">${feat}</span>
                <div class="shap-bar-track">
                    <div class="shap-bar-val ${signClass}" style="width: ${pct}%; left: 0;">
                        <span class="shap-val-text">${signText}${val.toFixed(4)}</span>
                    </div>
                </div>
            `;
            container.appendChild(row);
        });
    },

    async runForecasting() {
        if (!this.activeProjectId) return;

        const dateSelect = document.getElementById("ts-date-col");
        const valSelect = document.getElementById("ts-value-col");
        const stepsInput = document.getElementById("ts-forecast-steps");
        const methodSelect = document.getElementById("ts-method");

        if (!dateSelect.value || !valSelect.value) {
            alert("Please select both a date variable and a target value column to run time-series forecasting. Upload a dataset first if empty.");
            return;
        }

        const payload = {
            date_col: dateSelect.value,
            value_col: valSelect.value,
            steps: parseInt(stepsInput.value),
            method: methodSelect.value,
            username: Auth.currentUser ? Auth.currentUser.username : "admin"
        };

        const resultsBlock = document.getElementById("ts-results-block");
        resultsBlock.style.display = "none";

        const forecastBtn = document.getElementById("forecast-ts-btn");
        const oldBtn = forecastBtn.innerHTML;
        forecastBtn.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i> Iterating networks...";
        forecastBtn.disabled = true;

        try {
            const response = await fetch(`/api/projects/${this.activeProjectId}/forecast`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            forecastBtn.innerHTML = oldBtn;
            forecastBtn.disabled = false;

            if (!response.ok) throw new Error("Forecast endpoint issue");

            const res = await response.json();
            resultsBlock.style.display = "block";

            // Render forecasting lines
            Charts.renderTSForecast(res.historical, res.forecast, payload.value_col, "chart-ts-forecast");
            
            await this.loadAuditLogs();

        } catch (e) {
            forecastBtn.innerHTML = oldBtn;
            forecastBtn.disabled = false;
            console.error("Forecasting failed:", e);
            alert(`Forecasting error: ${e.message}`);
        }
    },

    setupExporters() {
        const xlsBtn = document.getElementById("export-excel-btn");
        const pptBtn = document.getElementById("export-pptx-btn");
        const pdfBtn = document.getElementById("export-pdf-btn");

        if (this.activeProjectId) {
            xlsBtn.href = `/api/projects/${this.activeProjectId}/export/excel`;
            pptBtn.href = `/api/projects/${this.activeProjectId}/export/pptx`;
            pdfBtn.href = `/api/projects/${this.activeProjectId}/export/pdf`;
            
            // Remove disabling
            xlsBtn.style.pointerEvents = "auto";
            pptBtn.style.pointerEvents = "auto";
            pdfBtn.style.pointerEvents = "auto";
            xlsBtn.style.opacity = "1";
            pptBtn.style.opacity = "1";
            pdfBtn.style.opacity = "1";
        } else {
            xlsBtn.removeAttribute("href");
            pptBtn.removeAttribute("href");
            pdfBtn.removeAttribute("href");
            
            xlsBtn.style.pointerEvents = "none";
            pptBtn.style.pointerEvents = "none";
            pdfBtn.style.pointerEvents = "none";
            xlsBtn.style.opacity = "0.3";
            pptBtn.style.opacity = "0.3";
            pdfBtn.style.opacity = "0.3";
        }
    },

    async loadAuditLogs() {
        try {
            const response = await fetch("/api/audit");
            if (!response.ok) throw new Error("Audit endpoint error");

            const logs = await response.json();
            const list = document.getElementById("audit-log-items-list");
            list.innerHTML = "";

            logs.reverse().slice(0, 50).forEach(log => {
                const dateStr = log.timestamp.split("T")[0];
                const item = document.createElement("li");
                item.className = "audit-log-item animate-scale";
                item.innerHTML = `
                    <div class="audit-log-item-header">
                        <span class="action">${log.action}</span>
                        <span class="user"><i class="fa-solid fa-user-shield"></i> ${log.user}</span>
                        <span class="time">${dateStr}</span>
                    </div>
                    <div class="audit-log-item-body">${log.details}</div>
                `;
                list.appendChild(item);
            });

        } catch (e) {
            console.error("Load audit failed", e);
        }
    },

    switchTab(tabId) {
        // Toggle screen views
        const screens = document.querySelectorAll(".app-screen");
        screens.forEach(s => {
            s.style.display = "none";
        });
        
        const targetScreen = document.getElementById(`screen-${tabId}`);
        if (targetScreen) targetScreen.style.display = "block";

        // Toggle nav items active state
        const navItems = document.querySelectorAll(".nav-item");
        navItems.forEach(item => {
            if (item.getAttribute("data-tab") === tabId) {
                item.classList.add("active");
            } else {
                item.classList.remove("active");
            }
        });
        
        // Refresh items on navigation
        if (tabId === "admin") {
            this.loadAuditLogs();
        }
    }
};

window.App = App;

// Initial start on window load
window.addEventListener("DOMContentLoaded", () => {
    App.init();
});
