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

            // Load overview for the selected namespace
            await loadClusterOverview();
            await loadClusterMetrics();
            await loadIngresses();

        } catch (error) {
            console.error("Failed to load namespaces:", error);

            namespaceSelector.innerHTML =
                `<option value="">Unable to load</option>`;
        }
    }

// Load live Kubernetes cluster overview
    async function loadClusterOverview() {
        if (!namespaceSelector || !namespaceSelector.value) {
            return;
        }

        const namespace = namespaceSelector.value;

        try {
            const response = await fetch(
                `/api/cluster/overview?namespace=${encodeURIComponent(namespace)}`
            );

            if (!response.ok) {
                throw new Error("Failed to load cluster overview.");
            }

            const data = await response.json();

            console.log("Live cluster overview:", data);

            updatePods(data.pods || []);
            updateDeployments(data.deployments || []);
            updateServices(data.services || []);
            updateEvents(data.events || []);

        } catch (error) {
            console.error("Failed to load cluster overview:", error);
        }
    }

    async function loadClusterMetrics() {
        try {
            const response = await fetch("/api/cluster/metrics");
    
            if (!response.ok) {
                throw new Error("Failed to load cluster metrics.");
            }
    
            const data = await response.json();
    
            console.log("Live cluster metrics:", data);
    
            const totalNodes = data.nodes?.total ?? 0;
            const readyNodes = data.nodes?.ready ?? 0;
            const notReadyNodes = data.nodes?.not_ready ?? 0;
    
            const cpuCapacity = data.resources?.cpu?.capacity ?? "0";
            const memoryAllocatable = data.resources?.memory?.allocatable ?? "0Ki";
    
            const readyNodesElement = document.getElementById("readyNodes");
            const notReadyNodesElement = document.getElementById("notReadyNodes");
            const cpuCapacityElement = document.getElementById("cpuCapacity");
            const memoryAllocatableElement = document.getElementById("memoryAllocatable");
    
            if (readyNodesElement) {
                readyNodesElement.textContent = `${readyNodes} ready`;
            }
    
            if (notReadyNodesElement) {
                notReadyNodesElement.textContent = `${notReadyNodes} down`;
            }
    
            if (cpuCapacityElement) {
                cpuCapacityElement.textContent = `${cpuCapacity} cores`;
            }
    
            if (memoryAllocatableElement) {
                const memoryKi = parseInt(
                    String(memoryAllocatable).replace("Ki", ""),
                    10
                );
    
                const memoryGiB = memoryKi / (1024 * 1024);
    
                memoryAllocatableElement.textContent =
                    `${memoryGiB.toFixed(2)} GiB`;
            }
    
            updateHealthStatus(readyNodes, totalNodes);
    
        } catch (error) {
            console.error("Failed to load cluster metrics:", error);
        }
    }

    async function loadIngresses() {
        try {
            const response = await fetch(
                `/api/cluster/ingresses?namespace=${encodeURIComponent(namespaceSelector.value)}`
            );

            if (!response.ok) {
                throw new Error("Failed to load Kubernetes ingresses.");
            }

            const data = await response.json();

            console.log("Live Kubernetes ingresses:", data);

            updateIngresses(data.ingresses || []);

        } catch (error) {
            console.error("Failed to load Kubernetes ingresses:", error);
        }
    }

    function updateIngresses(ingresses) {
        const total = ingresses.length;

        /*
         * An Ingress is considered active when it has
         * a load balancer address assigned.
         */
        const active = ingresses.filter(ingress =>
            Array.isArray(ingress.addresses) &&
            ingress.addresses.length > 0
        ).length;

        const percentage = total > 0
            ? Math.round((active / total) * 100)
            : 0;

        const activeElement =
            document.getElementById("ingressesHealthy");

        const totalElement =
            document.getElementById("ingressesTotal");

        const percentageElement =
            document.getElementById("ingressesPercentage");

        const progressElement =
            document.getElementById("ingressesProgress");

        const listElement =
            document.getElementById("ingressesList");

        if (activeElement) {
            activeElement.textContent = active;
        }

        if (totalElement) {
            totalElement.textContent = total;
        }

        if (percentageElement) {
            percentageElement.textContent = `${percentage}%`;
        }

        if (progressElement) {
            progressElement.style.width = `${percentage}%`;
        }

        if (listElement) {
            listElement.innerHTML = ingresses.length
                ? ingresses.map(ingress => {
                    const isActive =
                        Array.isArray(ingress.addresses) &&
                        ingress.addresses.length > 0;

                    const status = isActive
                        ? "Active"
                        : "Pending";

                    return `
                        <div class="${isActive ? "" : "unhealthy"}">
                            <span class="status-dot"></span>
                            <span>${ingress.name}</span>
                            <b>${status}</b>
                        </div>
                    `;
                }).join("")
                : `
                    <div>
                        <span>No Ingress resources found</span>
                    </div>
                `;
        }
    }

    function updateHealthStatus(readyNodes, totalNodes) {
        const healthLabel = document.getElementById("healthLabel");
    
        if (!healthLabel) {
            return;
        }
    
        if (totalNodes === 0) {
            healthLabel.textContent = "Unavailable";
            return;
        }
    
        if (readyNodes === totalNodes) {
            healthLabel.textContent = "Healthy";
        } else if (readyNodes > 0) {
            healthLabel.textContent = "Degraded";
        } else {
            healthLabel.textContent = "Unavailable";
        }
    }

    function updatePods(pods) {
        const total = pods.length;
    
        const healthy = pods.filter(
            pod => pod.status === "Running"
        ).length;
    
        const percentage = total > 0
            ? Math.round((healthy / total) * 100)
            : 0;
    
        const healthyElement = document.getElementById("podsHealthy");
        const totalElement = document.getElementById("podsTotal");
        const percentageElement = document.getElementById("podsPercentage");
        const progressElement = document.getElementById("podsProgress");
        const listElement = document.getElementById("podsList");
    
        if (healthyElement) {
            healthyElement.textContent = healthy;
        }
    
        if (totalElement) {
            totalElement.textContent = total;
        }
    
        if (percentageElement) {
            percentageElement.textContent = `${percentage}%`;
        }
    
        if (progressElement) {
            progressElement.style.width = `${percentage}%`;
        }
    
        if (listElement) {
            listElement.innerHTML = pods.length
                ? pods.map(pod => {
                    const isRunning = pod.status === "Running";
    
                    return `
                        <div class="${isRunning ? "" : "unhealthy"}">
                            <span class="status-dot"></span>
                            <span>${pod.name}</span>
                            <b>${pod.status}</b>
                        </div>
                    `;
                }).join("")
                : `<div><span>No pods found</span></div>`;
        }
    }

    function updateDeployments(deployments) {
        const total = deployments.length;
    
        const healthy = deployments.filter(deployment =>
            deployment.ready_replicas === deployment.desired_replicas &&
            deployment.available_replicas === deployment.desired_replicas
        ).length;
    
        const percentage = total > 0
            ? Math.round((healthy / total) * 100)
            : 0;
    
        const healthyElement = document.getElementById("deploymentsHealthy");
        const totalElement = document.getElementById("deploymentsTotal");
        const percentageElement = document.getElementById("deploymentsPercentage");
        const progressElement = document.getElementById("deploymentsProgress");
        const listElement = document.getElementById("deploymentsList");
    
        if (healthyElement) {
            healthyElement.textContent = healthy;
        }
    
        if (totalElement) {
            totalElement.textContent = total;
        }
    
        if (percentageElement) {
            percentageElement.textContent = `${percentage}%`;
        }
    
        if (progressElement) {
            progressElement.style.width = `${percentage}%`;
        }
    
        if (listElement) {
            listElement.innerHTML = deployments.length
                ? deployments.map(deployment => {
                    const healthyDeployment =
                        deployment.ready_replicas === deployment.desired_replicas &&
                        deployment.available_replicas === deployment.desired_replicas;
    
                    return `
                        <div class="${healthyDeployment ? "" : "unhealthy"}">
                            <span class="status-dot"></span>
                            <span>${deployment.name}</span>
                            <b>
                                ${deployment.ready_replicas}/${deployment.desired_replicas}
                            </b>
                        </div>
                    `;
                }).join("")
                : `<div><span>No deployments found</span></div>`;
        }
    }

    function updateServices(services) {
        const total = services.length;
    
        /*
         * Kubernetes Services do not have a ready/healthy status
         * like Pods or Deployments.
         *
         * For this dashboard card, percentage represents
         * successfully returned Service objects.
         */
        const healthy = services.filter(
            service => !service.error
        ).length;
    
        const percentage = total > 0
            ? Math.round((healthy / total) * 100)
            : 0;
    
        const healthyElement = document.getElementById("servicesHealthy");
        const totalElement = document.getElementById("servicesTotal");
        const percentageElement = document.getElementById("servicesPercentage");
        const progressElement = document.getElementById("servicesProgress");
        const listElement = document.getElementById("servicesList");
    
        if (healthyElement) {
            healthyElement.textContent = healthy;
        }
    
        if (totalElement) {
            totalElement.textContent = total;
        }
    
        if (percentageElement) {
            percentageElement.textContent = `${percentage}%`;
        }
    
        if (progressElement) {
            progressElement.style.width = `${percentage}%`;
        }
    
        if (listElement) {
            listElement.innerHTML = services.length
                ? services.map(service => `
                    <div>
                        <span class="status-dot"></span>
                        <span>${service.name}</span>
                        <b>${service.type}</b>
                    </div>
                `).join("")
                : `<div><span>No services found</span></div>`;
        }
    }

    function updateEvents(events) {
        const listElement = document.getElementById("activityList");
    
        if (!listElement) {
            return;
        }
    
        if (!events.length) {
            listElement.innerHTML = `
                <div class="activity-item">
                    <div>
                        <strong>No recent Kubernetes events</strong>
                        <p>No events were returned for this namespace.</p>
                    </div>
                </div>
            `;
    
            return;
        }
    
        const recentEvents = [...events]
            .sort((a, b) => {
                const dateA = new Date(
                    a.last_timestamp || a.first_timestamp || 0
                );
    
                const dateB = new Date(
                    b.last_timestamp || b.first_timestamp || 0
                );
    
                return dateB - dateA;
            })
            .slice(0, 5);
    
        listElement.innerHTML = recentEvents.map(event => {
            const eventType = event.type || "Normal";
    
            let iconClass = "success";
            let icon = "✓";
    
            if (eventType === "Warning") {
                iconClass = "warning";
                icon = "△";
            }
    
            return `
                <div class="activity-item">
                    <span class="activity-icon ${iconClass}">
                        ${icon}
                    </span>
    
                    <div>
                        <strong>${event.reason || "Kubernetes Event"}</strong>
    
                        <p>
                            ${event.message || "No event message available."}
                        </p>
    
                        <small>
                            ${event.object_kind || "Object"}:
                            ${event.object || "Unknown"}
                        </small>
                    </div>
                </div>
            `;
        }).join("");
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

    // Refresh live dashboard data
    refreshButton.addEventListener("click", async () => {
        refreshButton.style.transform = "rotate(360deg)";
        refreshButton.disabled = true;

        try {
            await loadClusterOverview();
            await loadClusterMetrics();
            await loadIngresses();

            refreshButton.title =
                "Last refreshed: " +
                new Date().toLocaleTimeString();

        } catch (error) {
            console.error("Dashboard refresh failed:", error);
        } finally {
            setTimeout(() => {
                refreshButton.style.transform = "";
                refreshButton.disabled = false;
            }, 500);
        }
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
