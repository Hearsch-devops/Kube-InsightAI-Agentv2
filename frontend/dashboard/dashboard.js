// Kube-InsightAI V2.0 — Dashboard interactions
// Dashboard mock data + live Kube-InsightAI assistant
// Backend: FastAPI → LangGraph → RAG

document.addEventListener("DOMContentLoaded", () => {
        const backToOverview = document.getElementById("backToOverview");
    const assistantLauncher = document.getElementById("assistantLauncher");
    const assistantPanel = document.getElementById("assistantPanel");
    const closeAssistant = document.getElementById("closeAssistant");
    const refreshButton = document.getElementById("refreshButton");
    const namespaceSelector = document.getElementById("namespaceSelector");
    const dashboardView = document.getElementById("dashboardView");
    const secondaryView = document.getElementById("secondaryView");
    const secondaryTitle = document.getElementById("secondaryTitle");
    const assistantForm = document.getElementById("assistantForm");
        const assistantInput = document.getElementById("assistantInput");
        const assistantSendButton = document.getElementById("assistantSendButton");
        const assistantMessages = document.getElementById("assistantMessages");

        console.log("Assistant launcher:", assistantLauncher);
        console.log("Assistant panel:", assistantPanel);
        console.log("Close button:", closeAssistant);

        if (assistantLauncher && assistantPanel) {
                assistantLauncher.addEventListener("click", () => {
                        console.log("Assistant launcher clicked");
                        assistantPanel.classList.toggle("open");
                        console.log("Panel classes:", assistantPanel.className);
                });
        }

        if (closeAssistant && assistantPanel) {
                closeAssistant.addEventListener("click", () => {
                        assistantPanel.classList.remove("open");
                });
        }

        const API_URL = "/api/chat";

        // Open the assistant panel
        assistantLauncher.addEventListener("click", () => {
                assistantPanel.classList.add("open");
        });

        // Close the assistant panel
        closeAssistant.addEventListener("click", () => {
                assistantPanel.classList.remove("open");
        });

    // Sidebar navigation
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", event => {
            event.preventDefault();

            document.querySelectorAll(".nav-item").forEach(nav => {
                nav.classList.remove("active");
            });

            item.classList.add("active");

            const page = item.dataset.page;

            if (page === "overview") {
                showOverview();
            } else {
                showPlaceholder(
                    page.charAt(0).toUpperCase() + page.slice(1)
                );
            }
        });
    });

// Top tabs
    document.querySelectorAll(".page-tab[data-tab]").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".page-tab").forEach(t => {
                t.classList.remove("active");
            });

            tab.classList.add("active");

            if (tab.dataset.tab === "overview") {
                showOverview();
            } else {
                showPlaceholder(
                    tab.textContent.replace(/[^\w\s]/g, "").trim()
                );
            }
        });
    });

// Load Kubernetes namespaces
    async function loadNamespaces() {
        if (!namespaceSelector) return;

        try {
            namespaceSelector.innerHTML = `<option value="">Loading...</option>`;

            const response = await fetch("/api/cluster/namespaces");

            if (!response.ok) {
                throw new Error("Failed to load namespaces.");
            }

            const data = await response.json();

            namespaceSelector.innerHTML = "";

            if (!data.namespaces || data.namespaces.length === 0) {
                namespaceSelector.innerHTML =
                    `<option value="">No namespaces found</option>`;
                return;
            }

            data.namespaces.forEach(namespace => {
                const option = document.createElement("option");

                option.value = namespace.name;
                option.textContent = namespace.name;

                namespaceSelector.appendChild(option);
            });

            const preferredNamespace = data.namespaces.find(
                namespace => namespace.name === "kube-insightaiv2"
            );

            if (preferredNamespace) {
                namespaceSelector.value = preferredNamespace.name;
            } else {
                namespaceSelector.selectedIndex = 0;
            }

        } catch (error) {
            console.error("Failed to load namespaces:", error);

            namespaceSelector.innerHTML =
                `<option value="">Unable to load</option>`;
        }
    }

    // Overview
    function showOverview() {
        dashboardView.classList.remove("hidden");
        secondaryView.classList.add("hidden");
    }

    function showPlaceholder(title) {
        dashboardView.classList.add("hidden");
        secondaryView.classList.remove("hidden");
        secondaryTitle.textContent = title;
    }

    backToOverview.addEventListener("click", showOverview);

    // Refresh mock dashboard data
    refreshButton.addEventListener("click", () => {
        refreshButton.textContent = "↻";
        refreshButton.style.transform = "rotate(360deg)";

        setTimeout(() => {
            refreshButton.style.transform = "";
            refreshButton.title = "Last refreshed: " + new Date().toLocaleTimeString();
        }, 500);
    });

    // Export a simple JSON snapshot
    document.getElementById("exportButton").addEventListener("click", () => {
        const snapshot = {
            project: "Kube-InsightAI V2.0",
            mode: "Demo",
            health: 73,
            criticalAlerts: 2,
            warningAlerts: 5,
            cpuUsage: "68%",
            memoryUsage: "74%",
            exportedAt: new Date().toISOString()
        };

        const blob = new Blob(
            [JSON.stringify(snapshot, null, 2)],
            { type: "application/json" }
        );

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "kube-insightai-dashboard.json";
        link.click();
        URL.revokeObjectURL(url);
    });

        // ==========================================
        // AI ASSISTANT INTEGRATION
        // ==========================================

        function appendAssistantMessage(sender, text) {
                const message = document.createElement("div");

                message.className =
                        sender === "user"
                                ? "assistant-message assistant-user-message"
                                : "assistant-message assistant-bot-message";

                if (sender === "user") {
                        // Display user messages as plain text
                        message.textContent = text;
                } else {
                        // Render AI responses as sanitized Markdown
                        if (typeof marked !== "undefined" && typeof DOMPurify !== "undefined") {
                                message.innerHTML = DOMPurify.sanitize(marked.parse(text));
                        } else {
                                // Fallback if the libraries are unavailable
                                message.textContent = text;
                                console.warn("Markdown libraries are not available.");
                        }
                }

                assistantMessages.appendChild(message);
                assistantMessages.scrollTop = assistantMessages.scrollHeight;
        }

        function showTypingIndicator() {
                const typingMessage = document.createElement("div");

                typingMessage.id = "typingIndicator";
                typingMessage.className = "assistant-message assistant-bot-message";
                typingMessage.textContent = "Kube-InsightAI is thinking...";

                assistantMessages.appendChild(typingMessage);
                assistantMessages.scrollTop = assistantMessages.scrollHeight;
        }

        function removeTypingIndicator() {
                const typingIndicator = document.getElementById("typingIndicator");

                if (typingIndicator) {
                        typingIndicator.remove();
                }
        }

        async function fetchBotReply(userMessage) {
                try {
                        const response = await fetch(API_URL, {
                                method: "POST",
                                headers: {
                                        "Content-Type": "application/json"
                                },
                                body: JSON.stringify({
                                        message: userMessage
                                })
                        });

                        if (!response.ok) {
                                let errorMessage = "Backend request failed.";

                                try {
                                        const errorData = await response.json();

                                        errorMessage =
                                                errorData.detail ||
                                                errorData.error ||
                                                errorMessage;
                                } catch {
                                        // Ignore JSON parsing errors
                                }

                                throw new Error(errorMessage);
                        }

                        const data = await response.json();

                        if (!data.response) {
                                throw new Error("Backend returned an empty response.");
                        }

                        return data.response;

                } catch (error) {
                        console.error("Kube-InsightAI API Error:", error);
                        return `Error: ${error.message}`;
                }
        }

        // Assistant form submission
        assistantForm.addEventListener("submit", async event => {
                event.preventDefault();

                const message = assistantInput.value.trim();

                if (!message || assistantSendButton.disabled) {
                        return;
                }

                appendAssistantMessage("user", message);

                assistantInput.value = "";
                assistantInput.disabled = true;
                assistantSendButton.disabled = true;

                showTypingIndicator();

                const botReply = await fetchBotReply(message);

                removeTypingIndicator();
                appendAssistantMessage("bot", botReply);

                assistantInput.disabled = false;
                assistantSendButton.disabled = false;
                assistantInput.focus();
        });

        // Quick actions → real AI assistant
        document.querySelectorAll("[data-assistant-query]").forEach(button => {
                button.addEventListener("click", async () => {
                        const query = button.dataset.assistantQuery;

                        assistantPanel.classList.add("open");
                        assistantInput.value = query;

                        // Automatically submit the quick action
                        assistantForm.requestSubmit();
                });
        });

        // Load Kubernetes namespaces
        loadNamespaces();
});
