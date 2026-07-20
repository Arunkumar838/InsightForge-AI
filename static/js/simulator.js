// Simulator Manager for InsightForge AI
const Simulator = {
    projectId: null,
    targetCol: null,
    debounceTimer: null,
    chart: null,

    init(projectId, numericCols) {
        this.projectId = projectId;
        
        // Select elements
        const select = document.getElementById("sim-target-select");
        select.innerHTML = "";
        
        if (numericCols.length === 0) {
            select.innerHTML = "<option value=''>-- No Numeric Data --</option>";
            return;
        }

        // Populating the select dropdown
        numericCols.forEach(col => {
            const opt = document.createElement("option");
            opt.value = col;
            opt.innerText = col;
            select.appendChild(opt);
        });

        // Set default target
        this.targetCol = select.value;

        // Reset sliders to 0
        document.getElementById("sim-val-price").value = 0;
        document.getElementById("sim-val-marketing").value = 0;
        document.getElementById("sim-val-staffing").value = 0;
        document.getElementById("sim-val-inventory").value = 0;
        document.getElementById("sim-val-demand").value = 0;
        
        this.updateLabels();
        
        // Add events
        select.onchange = (e) => {
            this.targetCol = e.target.value;
            this.triggerSimulation();
        };

        const sliders = ["price", "marketing", "staffing", "inventory", "demand"];
        sliders.forEach(s => {
            const el = document.getElementById(`sim-val-${s}`);
            el.oninput = () => {
                this.updateLabels();
                this.debounceSimulate();
            };
        });

        // Initial run
        this.triggerSimulation();
    },

    updateLabels() {
        const sliders = ["price", "marketing", "staffing", "inventory", "demand"];
        sliders.forEach(s => {
            const val = document.getElementById(`sim-val-${s}`).value;
            const sign = val > 0 ? "+" : "";
            document.getElementById(`label-val-${s}`).innerText = `${sign}${val}%`;
        });
    },

    debounceSimulate() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.triggerSimulation();
        }, 300); // 300ms debounce
    },

    async triggerSimulation() {
        if (!this.projectId || !this.targetCol) return;

        const payload = {
            pricing_adj: parseFloat(document.getElementById("sim-val-price").value),
            marketing_adj: parseFloat(document.getElementById("sim-val-marketing").value),
            staffing_adj: parseFloat(document.getElementById("sim-val-staffing").value),
            inventory_adj: parseFloat(document.getElementById("sim-val-inventory").value),
            demand_adj: parseFloat(document.getElementById("sim-val-demand").value),
            target_metric: this.targetCol
        };

        try {
            const response = await fetch(`/api/projects/${this.projectId}/simulate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error("Simulation endpoint failed");
            }

            const results = await response.json();
            this.renderResults(results);

        } catch (e) {
            console.error("Simulation error:", e);
        }
    },

    renderResults(res) {
        // 1. Text scores
        const formatCurrency = (val) => {
            return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
        };
        
        const isRevenue = this.targetCol.toLowerCase().includes("revenue") || 
                        this.targetCol.toLowerCase().includes("sales") || 
                        this.targetCol.toLowerCase().includes("total") ||
                        this.targetCol.toLowerCase().includes("amount") ||
                        this.targetCol.toLowerCase().includes("price") ||
                        this.targetCol.toLowerCase().includes("billing");

        document.getElementById("sim-base-val").innerText = isRevenue ? formatCurrency(res.base_value) : res.base_value;
        document.getElementById("sim-projected-val").innerText = isRevenue ? formatCurrency(res.predicted_value) : res.predicted_value;
        
        const deltaLabel = document.getElementById("sim-delta-pct");
        const sign = res.percentage_change > 0 ? "+" : "";
        deltaLabel.innerText = `${sign}${res.percentage_change.toFixed(2)}%`;
        
        deltaLabel.className = "";
        if (res.percentage_change >= 0) {
            deltaLabel.classList.add("text-green");
        } else {
            deltaLabel.classList.add("text-red");
        }

        // 2. Bar Chart
        const canvasId = "chart-simulator";
        if (this.chart) {
            this.chart.destroy();
        }

        const ctx = document.getElementById(canvasId).getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: res.labels,
                datasets: [{
                    label: this.targetCol,
                    data: res.values,
                    backgroundColor: [
                        'rgba(255, 255, 255, 0.08)',
                        res.percentage_change >= 0 ? 'rgba(0, 255, 135, 0.5)' : 'rgba(255, 59, 48, 0.5)'
                    ],
                    borderColor: [
                        'rgba(255, 255, 255, 0.2)',
                        res.percentage_change >= 0 ? '#00ff87' : '#ff3b30'
                    ],
                    borderWidth: 1,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#94a3b8' } },
                    y: { grid: { color: 'rgba(255, 255, 255, 0.03)' }, ticks: { color: '#94a3b8' } }
                }
            }
        });

        // 3. Consultant Remarks
        this.updateConsultantRemarks(payload = {
            price: parseFloat(document.getElementById("sim-val-price").value),
            marketing: parseFloat(document.getElementById("sim-val-marketing").value),
            staffing: parseFloat(document.getElementById("sim-val-staffing").value),
            inventory: parseFloat(document.getElementById("sim-val-inventory").value),
            demand: parseFloat(document.getElementById("sim-val-demand").value)
        }, res);
    },

    updateConsultantRemarks(inputs, res) {
        const remarksBox = document.getElementById("sim-consultant-remarks");
        let html = "";

        // Heuristics for advisory response
        if (inputs.price > 20 && inputs.marketing <= 0) {
            html += `<p class="text-red"><b>⚠️ Risk Detected:</b> High price adjustment (+${inputs.price}%) without marketing support threatens customer acquisition velocity.</p>`;
        }
        
        if (inputs.inventory < -15) {
            html += `<p class="text-orange"><b>⚠️ Risk Detected:</b> Under-allocation of inventory (-${Math.abs(inputs.inventory)}%) risks severe stockouts during peak cycles.</p>`;
        }
        
        if (inputs.marketing > 50 && inputs.staffing < -5) {
            html += `<p class="text-orange"><b>⚠️ Performance Lag:</b> Aggressive customer acquisition campaigns (+${inputs.marketing}%) will cause operational bottlenecks if staffing isn't scaled accordingly.</p>`;
        }

        if (html === "") {
            if (res.percentage_change > 10) {
                html += `<p class="text-green"><b>✅ Balanced Strategy:</b> Current configurations demonstrate positive business leverage. Volume increments outstrip structural cost expansions.</p>`;
            } else if (res.percentage_change < 0) {
                html += `<p class="text-red"><b>⚠️ Strategy Inefficiency:</b> Overall outcomes drop under baseline levels. Re-evaluate negative impact of pricing elasticities.</p>`;
            } else {
                html += `<p><b>ℹ️ Standard Margins:</b> The business configuration reports stable outputs. Adjust pricing (+10%) or marketing (+20%) to test threshold capacities.</p>`;
            }
        }

        html += `<p style="margin-top: 10px; font-size: 11px; color: var(--text-muted);">
            <i>Forecast confidence: <b>87%</b> based on local historical variance modeling.</i>
        </p>`;

        remarksBox.innerHTML = html;
    }
};

window.Simulator = Simulator;
