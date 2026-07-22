// Chat Manager for D2D
const Chat = {
    projectId: null,
    activeAgent: "document",
    agents: {
        document: { name: "DocuExtract AI", role: "Document Processing Expert", color: "#00d2ff" },
        cleaning: { name: "Purify AI", role: "Data Quality Imputation Specialist", color: "#00ff87" },
        visualization: { name: "VividCharts AI", role: "Visualization Architect", color: "#ff007f" },
        prediction: { name: "Predicta AI", role: "Machine Learning Specialist", color: "#7000ff" },
        business: { name: "Consul AI", role: "Strategic Business Consultant", color: "#ffaa00" },
        report: { name: "ExecutiveBrief AI", role: "Report Generation Specialist", color: "#ffffff" }
    },

    init(projectId) {
        this.projectId = projectId;
        this.renderAgentRoster();
        this.selectAgent("document");
        
        // Clear message logs
        const chatBox = document.getElementById("chat-messages");
        chatBox.innerHTML = `
            <div class="chat-bubble agent-msg">
                <div class="bubble-header">
                    <strong style="color: #00d2ff;">DocuExtract AI</strong>
                    <span>Just now</span>
                </div>
                <div class="bubble-body">
                    Active Project detected. Please submit your data query or let me extract tabular formats from your uploaded documents!
                </div>
            </div>
        `;

        // Bind events
        document.getElementById("chat-send-btn").onclick = () => this.sendMessage();
        document.getElementById("chat-user-input").onkeypress = (e) => {
            if (e.key === "Enter") this.sendMessage();
        };
    },

    renderAgentRoster() {
        const roster = document.getElementById("chat-agent-list");
        roster.innerHTML = "";

        Object.keys(this.agents).forEach(key => {
            const agent = this.agents[key];
            const card = document.createElement("div");
            card.className = `agent-card ${key === this.activeAgent ? 'active' : ''}`;
            card.onclick = () => this.selectAgent(key);

            card.innerHTML = `
                <span class="agent-dot" style="background: ${agent.color};"></span>
                <div class="agent-name-role">
                    <h4>${agent.name}</h4>
                    <span>${agent.role}</span>
                </div>
            `;
            roster.appendChild(card);
        });
    },

    selectAgent(key) {
        this.activeAgent = key;
        const agent = this.agents[key];

        // Update active UI card class
        const cards = document.querySelectorAll(".agent-card");
        cards.forEach((c, idx) => {
            const cardKey = Object.keys(this.agents)[idx];
            c.className = `agent-card ${cardKey === key ? 'active' : ''}`;
        });

        // Update active top banner
        document.getElementById("active-agent-dot").style.backgroundColor = agent.color;
        document.getElementById("active-agent-dot").style.color = agent.color;
        document.getElementById("active-agent-name").innerText = agent.name;
        document.getElementById("active-agent-role").innerText = agent.role;

        // Load specific default suggestions
        this.loadSuggestions(this.getDefaultSuggestions(key));
    },

    getDefaultSuggestions(key) {
        const defaults = {
            document: ["Explain raw parsed text", "Show dataset columns", "Parse scanned document"],
            cleaning: ["What is my Data Quality Score?", "Impute missing cells", "Show outlier counts"],
            visualization: ["Explain Bar chart values", "Show heatmap correlation", "Plot a scatter correlation"],
            prediction: ["Train Random Forest model", "Show top predictions", "Calculate SHAP values"],
            business: ["Analyze pricing elasticity", "Show What-If margins", "Explain business risks"],
            report: ["Export PDF Briefing", "Build PowerPoint Slides", "Download clean Excel"]
        };
        return defaults[key] || [];
    },

    loadSuggestions(list) {
        const container = document.getElementById("chat-suggestions");
        container.innerHTML = "";
        
        list.forEach(text => {
            const pill = document.createElement("button");
            pill.className = "suggestion-pill";
            pill.innerText = text;
            pill.onclick = () => {
                document.getElementById("chat-user-input").value = text;
                this.sendMessage();
            };
            container.appendChild(pill);
        });
    },

    async sendMessage() {
        const input = document.getElementById("chat-user-input");
        const query = input.value.trim();
        if (!query) return;

        input.value = "";
        
        // Append User Bubble
        const chatBox = document.getElementById("chat-messages");
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        const userHtml = `
            <div class="chat-bubble user-msg animate-scale">
                <div class="bubble-header">
                    <strong>User</strong>
                    <span>${time}</span>
                </div>
                <div class="bubble-body">${query}</div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', userHtml);
        chatBox.scrollTop = chatBox.scrollHeight;

        // Append loader
        const loaderId = "msg-loader-temp";
        const loaderHtml = `
            <div class="chat-bubble agent-msg" id="${loaderId}">
                <div class="bubble-body" style="font-style: italic; color: var(--text-muted);">
                    <i class="fa-solid fa-spinner fa-spin"></i> Coordinating agent response parameters...
                </div>
            </div>
        `;
        chatBox.insertAdjacentHTML('beforeend', loaderHtml);
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const session = JSON.parse(localStorage.getItem("if_user_session"));
            const username = session ? session.username : "admin";

            const response = await fetch(`/api/projects/${this.projectId}/chat`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: query,
                    active_agent: this.activeAgent,
                    username: username
                })
            });

            // Remove loader
            const loaderEl = document.getElementById(loaderId);
            if (loaderEl) loaderEl.remove();

            if (!response.ok) {
                throw new Error("Failed to contact agents");
            }

            const data = await response.json();
            
            // Switch active agent indicator if routed
            const agentKey = Object.keys(this.agents).find(k => this.agents[k].name === data.agent_name) || this.activeAgent;
            this.selectAgent(agentKey);

            // Render Markdown response
            // marked is loaded via CDN in index.html
            const parsedMarkdown = marked.parse(data.response);
            
            const agentHtml = `
                <div class="chat-bubble agent-msg animate-scale">
                    <div class="bubble-header">
                        <strong style="color: ${data.agent_color};">${data.agent_name}</strong>
                        <span>${time}</span>
                    </div>
                    <div class="bubble-body">${parsedMarkdown}</div>
                </div>
            `;
            chatBox.insertAdjacentHTML('beforeend', agentHtml);
            chatBox.scrollTop = chatBox.scrollHeight;

            // Load new suggestions
            if (data.suggested_questions && data.suggested_questions.length > 0) {
                this.loadSuggestions(data.suggested_questions);
            }

        } catch (error) {
            console.error("Chat error:", error);
            const loaderEl = document.getElementById(loaderId);
            if (loaderEl) loaderEl.remove();
            
            const errHtml = `
                <div class="chat-bubble agent-msg animate-scale" style="border-color: var(--neon-red);">
                    <div class="bubble-body text-red">
                        ⚠️ <b>Operational Error:</b> Failed to execute agent connection. Please confirm backend server links are operational.
                    </div>
                </div>
            `;
            chatBox.insertAdjacentHTML('beforeend', errHtml);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }
};

window.Chat = Chat;
