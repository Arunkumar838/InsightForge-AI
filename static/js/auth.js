// Auth Manager for InsightForge AI
const Auth = {
    currentUser: null,

    init() {
        // Check if user is already logged in
        const storedUser = localStorage.getItem("if_user_session");
        if (storedUser) {
            try {
                this.currentUser = JSON.parse(storedUser);
                this.applySessionUI();
                return true;
            } catch (e) {
                localStorage.removeItem("if_user_session");
            }
        }
        return false;
    },

    async login(username, password) {
        try {
            const response = await fetch("/api/auth/login", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Authentication Failed");
            }

            const user = await response.json();
            this.currentUser = user;
            localStorage.setItem("if_user_session", JSON.stringify(user));
            this.applySessionUI();
            return user;
        } catch (error) {
            console.error("Login error:", error);
            throw error;
        }
    },

    logout() {
        this.currentUser = null;
        localStorage.removeItem("if_user_session");
        
        // Reset UI
        document.getElementById("app-container").style.display = "none";
        document.getElementById("login-modal").style.display = "flex";
        
        // Reset password field
        document.getElementById("password").value = "";
    },

    applySessionUI() {
        if (!this.currentUser) return;

        // Hide Login Modal and Show App Layout
        document.getElementById("login-modal").style.display = "none";
        document.getElementById("app-container").style.display = "grid";

        // Update Avatar Letter
        const avatarLetter = this.currentUser.fullname ? this.currentUser.fullname.charAt(0) : "U";
        document.getElementById("nav-user-avatar").innerText = avatarLetter;

        // Update Name & Role
        document.getElementById("nav-user-fullname").innerText = this.currentUser.fullname || this.currentUser.username;
        document.getElementById("nav-user-role").innerText = "Admin";

        // Update RBAC Profile Screen values
        document.getElementById("rbac-val-user").innerText = this.currentUser.username;
        document.getElementById("rbac-val-role").innerText = "Admin";
        document.getElementById("api-key-field").value = this.currentUser.api_key || "No Key Available";

        // Style the Role Badge
        const roleBadge = document.getElementById("rbac-val-role");
        roleBadge.className = "badge badge-red";

        // Apply UI status (Admin has full privileges)
        this.applyRbacRestrictions();
    },

    applyRbacRestrictions() {
        // Restore dropzone and full privileges
        const dropzone = document.getElementById("dropzone");
        if (dropzone) {
            dropzone.style.pointerEvents = "auto";
            const dropzoneSpan = dropzone.querySelector("p span");
            if (dropzoneSpan) {
                dropzoneSpan.innerText = "click to browse";
            }
        }
    },

    getAuthHeader() {
        return this.currentUser ? { "Authorization": `Bearer ${this.currentUser.api_key}` } : {};
    }
};

// Event listener for login form submit
document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const u = document.getElementById("username").value;
    const p = document.getElementById("password").value;
    const errorMsg = document.createElement("p");
    errorMsg.style.color = "var(--neon-red)";
    errorMsg.style.fontSize = "11px";
    errorMsg.style.marginTop = "8px";
    errorMsg.id = "login-err-alert";

    const oldAlert = document.getElementById("login-err-alert");
    if (oldAlert) oldAlert.remove();

    try {
        await Auth.login(u, p);
        // Start App Initializations
        if (window.App && typeof window.App.onLogin === "function") {
            window.App.onLogin();
        }
    } catch (err) {
        errorMsg.innerText = err.message;
        document.getElementById("login-form").appendChild(errorMsg);
    }
});

// Logout action
document.getElementById("logout-btn").addEventListener("click", () => {
    Auth.logout();
});
