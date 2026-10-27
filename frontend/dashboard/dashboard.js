// Kube-InsightAI V2.0 — Dashboard interactions
// Dashboard mock data + live Kube-InsightAI assistant
// Backend: FastAPI → LangGraph → RAG

document.addEventListener("DOMContentLoaded", async () => {

    
    const logsNamespace = document.getElementById("logsNamespace");
    const logsPod = document.getElementById("logsPod");
    const logsContainer = document.getElementById("logsContainer");
    const loginView = document.getElementById("loginView");
    const loginForm = document.getElementById("loginForm");
    const loginUsername = document.getElementById("loginUsername");
    const loginPassword = document.getElementById("loginPassword");
    const loginError = document.getElementById("loginError");
    const loginButton = document.getElementById("loginButton");
    const appShell = document.querySelector(".app-shell");

    function showLogin(message = "") {
        loginView.classList.remove("hidden");
        appShell.classList.add("hidden");
        loginError.textContent = message;
        loginError.classList.toggle("hidden", !message);
    }

    function showDashboard() {
        const user = window.KubeAuth.getUser();

        loginView.classList.add("hidden");
        appShell.classList.remove("hidden");

        document.getElementById("userSession").classList.remove("hidden");
        document.getElementById("currentUsername").textContent =
            user?.username || "";
        document.getElementById("currentUserRole").textContent =
            user?.role || "";
    }

    document.getElementById("logoutButton").addEventListener("click", () => {
        window.KubeAuth.clearSession();
        loginPassword.value = "";
        showLogin();
    });

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        loginError.textContent = "";
        loginError.classList.add("hidden");
        loginButton.disabled = true;
        loginButton.textContent = "Signing in...";

        try {
            await window.KubeAuth.login(
                loginUsername.value.trim(),
                loginPassword.value
            );

            // Reload so the existing dashboard initializes
            // only after the saved session is restored.
            window.location.reload();
        } catch (error) {
            showLogin(error.message || "Unable to sign in.");
        } finally {
            loginButton.disabled = false;
            loginButton.textContent = "Sign in";
        }
    });

    window.addEventListener("auth:unauthorized", () => {
        window.KubeAuth.clearSession();

        if (assistantPanel) {
            assistantPanel.classList.remove("open");
        }

        loginPassword.value = "";
        showLogin("Your session has expired. Please sign in again.");
    });

    const currentUser = await window.KubeAuth.restoreSession();

    if (!currentUser) {
        showLogin();
        return;
    }

    showDashboard();

    const backToOverview = document.getElementById("backToOverview");
    const assistantLauncher = document.getElementById("assistantLauncher");
    const assistantPanel = document.getElementById("assistantPanel");
    const closeAssistant = document.getElementById("closeAssistant");
    const refreshButton = document.getElementById("refreshButton");
    const namespaceSelector = document.getElementById("namespaceSelector");
    const dashboardView = document.getElementById("dashboardView");
    const secondaryView = document.getElementById("secondaryView");
    const secondaryTitle = document.getElementById("secondaryTitle");
    const clustersPage = document.getElementById("clustersPage");
    const placeholderPage = document.getElementById("placeholderPage");
    const historyPage = document.getElementById("historyPage");
    const historyList = document.getElementById("historyList");
    const historyStatus = document.getElementById("historyStatus");
    const historySearch = document.getElementById("historySearch");
    const refreshHistoryButton = document.getElementById("refreshHistory");

    let investigationHistory = [];
    const logsPage = document.getElementById("logsPage");
    const recommendationsPage = document.getElementById(
        "recommendationsPage"
    );
    const clustersNamespaceSelector =
        document.getElementById("clustersNamespaceSelector");
    const clustersStatus = document.getElementById("clustersStatus");
    const clustersPodsTable = document.getElementById("clustersPodsTable");
    const clustersDeploymentsTable =
        document.getElementById("clustersDeploymentsTable");
    const clustersServicesTable =
        document.getElementById("clustersServicesTable");
    const queryPage = document.getElementById("queryPage");
    const queryForm = document.getElementById("queryForm");
    const queryInput = document.getElementById("queryInput");
    const querySubmitButton = document.getElementById("querySubmitButton");
    const queryStatus = document.getElementById("queryStatus");
    const queryAnswerPanel = document.getElementById("queryAnswerPanel");
    const queryAnswer = document.getElementById("queryAnswer");
    const queryRoute = document.getElementById("queryRoute");
    const querySourcesSection = document.getElementById("querySourcesSection");
    const querySources = document.getElementById("querySources");
    const queryError = document.getElementById("queryError");
    async function submitQuery(question) {
        const message = question.trim();

        if (!message || querySubmitButton.disabled) {
            return;
        }

        queryInput.value = message;
        queryAnswerPanel.classList.remove("hidden");
        queryAnswer.textContent = "";
        queryRoute.textContent = "";
        querySources.replaceChildren();
        querySourcesSection.classList.add("hidden");
        queryError.textContent = "";
        queryError.classList.add("hidden");

        queryStatus.textContent = "Kube-InsightAI is thinking...";
        querySubmitButton.disabled = true;
        queryInput.disabled = true;
        querySubmitButton.textContent = "Processing...";

        try {
            const response = await window.KubeAuth.apiFetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail ||
                    data.error_message ||
                    data.error ||
                    "The AI request failed."
                );
            }

            if (!data.response) {
                throw new Error("The AI returned an empty response.");
            }

            // Display the answer as plain text for safe rendering.
            queryAnswer.textContent = data.response;

            if (data.route) {
                queryRoute.textContent = `Route: ${data.route}`;
            }

            if (Array.isArray(data.sources) && data.sources.length > 0) {
                data.sources.forEach(source => {
                    const item = document.createElement("li");
                    item.textContent = source;
                    querySources.appendChild(item);
                });

                querySourcesSection.classList.remove("hidden");
            }

            if (data.error || data.error_message) {
                queryError.textContent =
                    data.error_message || data.error;
                queryError.classList.remove("hidden");
            }

            queryStatus.textContent = "Response received";

        } catch (error) {
            console.error("Query request failed:", error);

            queryError.textContent = error.message ||
                "Unable to contact Kube-InsightAI.";

            queryError.classList.remove("hidden");
            queryStatus.textContent = "Request failed";

        } finally {
            querySubmitButton.disabled = false;
            queryInput.disabled = false;
            querySubmitButton.textContent = "✦ Ask AI";
            queryInput.focus();
        }
    }
    queryForm.addEventListener("submit", event => {
        event.preventDefault();
        submitQuery(queryInput.value);
    });

    // Suggested questions automatically submit to the AI.
    document.querySelectorAll(".query-suggestion").forEach(button => {
        button.addEventListener("click", () => {
            if (querySubmitButton.disabled) {
                return;
            }

            submitQuery(button.dataset.query || "");
        });
    });

    // Return to the Dashboard.
    document.getElementById("backFromQuery").addEventListener(
        "click",
        showOverview
    );

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
            } else if (page === "clusters") {
                showClusters();
            } else if (page === "query") {
                showQuery();
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
            } else if (tab.dataset.tab === "logs") {
                showLogs();
            } else if (tab.dataset.tab === "recommendations") {
                showRecommendations();
            } else if (tab.dataset.tab === "history") {
                showHistory();
            } else {
                showPlaceholder(
                    tab.textContent.replace(/[^\w\s]/g, "").trim()
                );
            }
        });
    });

    // Load namespaces for Logs Explorer
    async function loadLogsNamespaces() {
        const logsNamespace = document.getElementById("logsNamespace");

        if (!logsNamespace) return;

        logsNamespace.innerHTML =
            '<option value="">Loading namespaces...</option>';

        try {
            const response = await window.KubeAuth.apiFetch(
                "/api/cluster/namespaces"
            );

            if (!response.ok) {
                throw new Error("Failed to load namespaces.");
            }

            const data = await response.json();
            const namespaces = data.namespaces || [];

            logsNamespace.replaceChildren();

            if (namespaces.length === 0) {
                logsNamespace.add(
                    new Option("No namespaces found", "")
                );
                return;
            }

            namespaces.forEach(namespace => {
                logsNamespace.add(
                    new Option(namespace.name, namespace.name)
                );
            });

            const preferredNamespace = namespaces.find(
                namespace => namespace.name === "kube-insightaiv2"
            );

            logsNamespace.value = preferredNamespace
                ? preferredNamespace.name
                : namespaces[0].name;

            logsNamespace.dispatchEvent(
                new Event("change", { bubbles: true })
            );

        } catch (error) {
            console.error(
                "Failed to load Logs namespaces:",
                error
            );

            logsNamespace.replaceChildren(
                new Option("Unable to load namespaces", "")
            );
        }
    }

    async function loadLogsPods() {
        if (!logsNamespace || !logsPod || !logsContainer) return;

        const namespace = logsNamespace.value;

        logsPod.replaceChildren(
            new Option(
                namespace ? "Loading pods..." : "Select a namespace first",
                ""
            )
        );
        logsPod.disabled = true;

        logsContainer.replaceChildren(
            new Option("Select a pod first", "")
        );
        logsContainer.disabled = true;

        if (!namespace) return;

        try {
            const response = await window.KubeAuth.apiFetch(
                `/api/cluster/overview?namespace=${encodeURIComponent(namespace)}`
            );

            if (!response.ok) {
                throw new Error("Failed to load pods.");
            }

            const data = await response.json();
            const pods = data.pods || [];

            logsPod.replaceChildren();

            if (pods.some(pod => pod.error)) {
                throw new Error(pods.find(pod => pod.error).error);
            }

            if (pods.length === 0) {
                logsPod.add(new Option("No pods found", ""));
                return;
            }

            logsPod.add(new Option("Select a pod", ""));

            pods.forEach(pod => {
                logsPod.add(new Option(pod.name, pod.name));
            });

            logsPod.disabled = false;

        } catch (error) {
            console.error("Failed to load Logs pods:", error);
            logsPod.replaceChildren(
                new Option("Unable to load pods", "")
            );
        }
    }

    function loadLogsContainers() {
        if (!logsPod || !logsContainer) return;

        const namespace = logsNamespace.value;
        const podName = logsPod.value;

        logsContainer.replaceChildren(
            new Option(
                podName ? "Loading containers..." : "Select a pod first",
                ""
            )
        );
        logsContainer.disabled = true;

        if (!namespace || !podName) return;

        // The existing overview response includes container names.
        // Fetch it again for the selected namespace to find this pod.
        window.KubeAuth.apiFetch(
            `/api/cluster/overview?namespace=${encodeURIComponent(namespace)}`
        )
            .then(async response => {
                if (!response.ok) {
                    throw new Error("Failed to load container details.");
                }

                const data = await response.json();
                const pod = (data.pods || []).find(
                    item => item.name === podName
                );

                logsContainer.replaceChildren();

                const containers = pod?.containers || [];

                if (containers.length === 0) {
                    logsContainer.add(
                        new Option("No container details available", "")
                    );
                    return;
                }

                logsContainer.add(new Option("Select a container", ""));

                containers.forEach(container => {
                    logsContainer.add(
                        new Option(container.name, container.name)
                    );
                });

                logsContainer.disabled = false;
            })
            .catch(error => {
                console.error("Failed to load Logs containers:", error);
                logsContainer.replaceChildren(
                    new Option("Unable to load containers", "")
                );
            });
    }

    // Update dependent selectors when selections change.
    logsNamespace.addEventListener("change", loadLogsPods);
    logsPod.addEventListener("change", loadLogsContainers);

    // Load Kubernetes namespaces
    async function loadNamespaces() {
        if (!namespaceSelector) return;

        try {
            namespaceSelector.innerHTML = `<option value="">Loading...</option>`;

            const response = await window.KubeAuth.apiFetch("/api/cluster/namespaces");

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

    // Initialize the dashboard with live Kubernetes data.
    await loadNamespaces();
    loadLogsNamespaces();

    // Load live Kubernetes cluster overview
    async function loadClusterOverview() {
        if (!namespaceSelector || !namespaceSelector.value) {
            return;
        }

        const namespace = namespaceSelector.value;

        try {
            const response = await window.KubeAuth.apiFetch(
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
            const response = await window.KubeAuth.apiFetch(
                "/api/cluster/metrics"
            );

            if (!response.ok) {
                throw new Error("Failed to load cluster metrics.");
            }

            const data = await response.json();

            console.log("Live cluster metrics:", data);

            const totalNodes = data.nodes?.total ?? 0;
            const readyNodes = data.nodes?.ready ?? 0;
            const notReadyNodes = data.nodes?.not_ready ?? 0;

            const cpuCapacity = data.resources?.cpu?.capacity ?? "0";
            const memoryAllocatable =
                data.resources?.memory?.allocatable ?? "0Ki";

            const cpuUsagePercent =
                data.resources?.cpu?.usage_percent;
            const memoryUsagePercent =
                data.resources?.memory?.usage_percent;

            const readyNodesElement =
                document.getElementById("readyNodes");
            const notReadyNodesElement =
                document.getElementById("notReadyNodes");
            const cpuCapacityElement =
                document.getElementById("cpuCapacity");
            const memoryAllocatableElement =
                document.getElementById("memoryAllocatable");
            const cpuUsageElement =
                document.getElementById("cpuUsage");
            const memoryUsageElement =
                document.getElementById("memoryUsage");

            if (readyNodesElement) {
                readyNodesElement.textContent = `${readyNodes} ready`;
            }

            if (notReadyNodesElement) {
                notReadyNodesElement.textContent =
                    `${notReadyNodes} down`;
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

            if (cpuUsageElement) {
                cpuUsageElement.textContent =
                    Number.isFinite(Number(cpuUsagePercent))
                        ? `${Number(cpuUsagePercent).toFixed(1)}%`
                        : "N/A";
            }

            if (memoryUsageElement) {
                memoryUsageElement.textContent =
                    Number.isFinite(Number(memoryUsagePercent))
                        ? `${Number(memoryUsagePercent).toFixed(1)}%`
                        : "N/A";
            }

            updateHealthStatus(readyNodes, totalNodes);

        } catch (error) {
            console.error(
                "Failed to load cluster metrics:",
                error
            );
        }
    }

    async function loadIngresses() {
        try {
            const response = await window.KubeAuth.apiFetch(
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
        const healthScoreElement = document.getElementById("healthScore");
        const healthLabel = document.getElementById("healthLabel");

        if (!healthScoreElement || !healthLabel) {
            return;
        }

        if (totalNodes === 0) {
            healthScoreElement.textContent = "0";
            healthLabel.textContent = "Unavailable";
            return;
        }

        // Calculate health from the percentage of Ready nodes.
        const score = Math.round((readyNodes / totalNodes) * 100);

        healthScoreElement.textContent = score;

        if (score === 100) {
            healthLabel.textContent = "Healthy";
        } else if (score >= 50) {
            healthLabel.textContent = "Degraded";
        } else {
            healthLabel.textContent = "Critical";
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

    function escapeRecommendationHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character]);
    }

    async function loadRecommendations() {
        const list = document.getElementById("recommendationsList");
        const status = document.getElementById("recommendationsStatus");
        const total = document.getElementById("recommendationTotal");
        const critical = document.getElementById("recommendationCritical");
        const warning = document.getElementById("recommendationWarning");

        if (!list || !status) {
            console.error("Recommendations HTML elements were not found.");
            return;
        }

        status.textContent = "Loading recommendations...";
        list.innerHTML = "";

        try {
            const response = await window.KubeAuth.apiFetch(
                "/api/recommendations"
            );

            if (!response.ok) {
                throw new Error(`API request failed: HTTP ${response.status}`);
            }

            const data = await response.json();
            const recommendations = data.recommendations || [];

            total.textContent = data.summary?.total ?? recommendations.length;
            critical.textContent = data.summary?.critical ?? 0;
            warning.textContent = data.summary?.warning ?? 0;

            const severityFilter =
                document.getElementById("recommendationSeverity").value;
            const namespaceFilter =
                document.getElementById("recommendationNamespace").value;

            const namespaces = [
                ...new Set(
                    recommendations
                        .map(item => item.resource?.namespace)
                        .filter(Boolean)
                )
            ].sort();

            const namespaceSelect =
                document.getElementById("recommendationNamespace");

            const previousNamespace = namespaceSelect.value;

            namespaceSelect.replaceChildren(
                new Option("All namespaces", "all"),
                ...namespaces.map(ns => new Option(ns, ns))
            );

            if (namespaces.includes(previousNamespace)) {
                namespaceSelect.value = previousNamespace;
            }

            const filtered = recommendations.filter(item => {
                const severityMatches =
                    severityFilter === "all" ||
                    item.severity === severityFilter;

                const namespaceMatches =
                    namespaceSelect.value === "all" ||
                    item.resource?.namespace === namespaceSelect.value;

                return severityMatches && namespaceMatches;
            });

            if (!filtered.length) {
                list.textContent = "No recommendations match these filters.";
                status.textContent = "No matching recommendations.";
                return;
            }

            list.innerHTML = filtered.map((item, index) => {
                const resource = item.resource || {};
                const severity = item.severity || "warning";
                const evidence = (item.evidence || [])
                    .map(text => `<li>${escapeRecommendationHTML(text)}</li>`)
                    .join("");

                const causes = (item.likely_causes || [])
                    .map(text => `<li>${escapeRecommendationHTML(text)}</li>`)
                    .join("");

                const actions = (item.recommended_actions || [])
                    .map(text => `<li>${escapeRecommendationHTML(text)}</li>`)
                    .join("");

                const commands = (item.commands || [])
                    .map(command => `
                        <div class="recommendation-command">
                            <code>${escapeRecommendationHTML(command)}</code>
                            <button type="button"
                                    class="copy-recommendation-command"
                                    data-command="${escapeRecommendationHTML(command)}">
                                Copy
                            </button>
                        </div>
                    `).join("");

                return `
                    <article class="panel recommendation-card">
                        <div class="panel-header">
                            <div>
                                <strong>${escapeRecommendationHTML(
                                    resource.name || "Unknown resource"
                                )}</strong>
                                <p>${escapeRecommendationHTML(
                                    resource.namespace || "Unknown namespace"
                                )} · ${escapeRecommendationHTML(
                                    resource.kind || "Resource"
                                )}</p>
                            </div>
                            <span class="recommendation-severity">
                                ${escapeRecommendationHTML(severity.toUpperCase())}
                            </span>
                        </div>

                        <p>${escapeRecommendationHTML(item.observation)}</p>

                        <details>
                            <summary>Evidence, causes and remediation</summary>
                            <h4>Evidence</h4>
                            <ul>${evidence || "<li>No evidence provided.</li>"}</ul>

                            <h4>Likely causes</h4>
                            <ul>${causes || "<li>No causes provided.</li>"}</ul>

                            <h4>Recommended actions</h4>
                            <ul>${actions || "<li>No actions provided.</li>"}</ul>

                            <h4>Troubleshooting commands</h4>
                            ${commands || "<p>No commands provided.</p>"}
                        </details>

                        <p><small>Read-only recommendations. Changes require approval.</small></p>
                    </article>
                `;
            }).join("");

            status.textContent =
                `Showing ${filtered.length} of ${recommendations.length} recommendations.`;

        } catch (error) {
            console.error("Failed to load recommendations:", error);
            status.textContent =
                "Unable to load recommendations. Check the API and browser console.";
            list.textContent = error.message;
        }
    }

    // Overview
    function showOverview() {
        dashboardView.classList.remove("hidden");
        secondaryView.classList.add("hidden");
        clustersPage.classList.add("hidden");
        logsPage.classList.add("hidden");
        placeholderPage.classList.add("hidden");
        queryPage.classList.add("hidden");
        recommendationsPage.classList.add("hidden");
        historyPage.classList.add("hidden");
    }

    function showLogs() {
        dashboardView.classList.add("hidden");
        secondaryView.classList.remove("hidden");
        clustersPage.classList.add("hidden");
        logsPage.classList.remove("hidden");
        placeholderPage.classList.add("hidden");
        queryPage.classList.add("hidden");
    } 
    
    function showHistory() {
        dashboardView.classList.add("hidden");
        secondaryView.classList.remove("hidden");

        clustersPage.classList.add("hidden");
        logsPage.classList.add("hidden");
        recommendationsPage.classList.add("hidden");
        placeholderPage.classList.add("hidden");
        queryPage.classList.add("hidden");
  
        historyPage.classList.remove("hidden");

        secondaryTitle.textContent = "Investigation History";

        loadInvestigationHistory();
    }

    function renderHistory() {
        if (!historyList || !historySearch) return;

        const searchTerm = historySearch.value.trim().toLowerCase();

        const filteredHistory = investigationHistory.filter(item => {
            return (
                (item.question || "").toLowerCase().includes(searchTerm) ||
                (item.response || "").toLowerCase().includes(searchTerm) ||
                (item.route || "").toLowerCase().includes(searchTerm) ||
                (item.namespace || "").toLowerCase().includes(searchTerm)
            );
        });

        historyList.replaceChildren();

        if (filteredHistory.length === 0) {
            const emptyMessage = document.createElement("p");

            emptyMessage.textContent = investigationHistory.length
                ? "No investigations match your search."
                : "No investigation history found yet.";

            historyList.appendChild(emptyMessage);
            return;
        }

        filteredHistory.forEach(item => {
            const card = document.createElement("article");
            card.className = "history-card";

            const question = document.createElement("h3");
            question.className = "history-question";
            question.textContent = item.question || "Untitled investigation";

            const timestamp = document.createElement("p");
            timestamp.className = "history-timestamp";

            const date = item.timestamp ? new Date(item.timestamp) : null;

            timestamp.textContent = date && !Number.isNaN(date.getTime())
                ? date.toLocaleString()
                : "Date unavailable";

            const metadata = document.createElement("p");
            metadata.className = "history-metadata";

            const details = [];

            if (item.route) details.push(`Route: ${item.route}`);
            if (item.namespace) details.push(`Namespace: ${item.namespace}`);

            metadata.textContent = details.join(" • ");

            const answer = document.createElement("p");
            answer.className = "history-response";
            answer.textContent = item.response || "No response recorded.";

            const toggleButton = document.createElement("button");
            toggleButton.type = "button";
            toggleButton.className = "history-toggle";
            toggleButton.textContent = "View response";

            const answerContainer = document.createElement("div");
            answerContainer.className = "history-answer hidden";
            answerContainer.appendChild(answer);

            if (Array.isArray(item.sources) && item.sources.length > 0) {
                const sourcesHeading = document.createElement("h4");
                sourcesHeading.textContent = "Sources";

                const sourcesList = document.createElement("ul");

                item.sources.forEach(source => {
                    const li = document.createElement("li");
                    li.textContent = typeof source === "string"
                        ? source
                        : JSON.stringify(source);

                    sourcesList.appendChild(li);
                });

                answerContainer.append(sourcesHeading, sourcesList);
            }

            toggleButton.addEventListener("click", () => {
                const isHidden = answerContainer.classList.toggle("hidden");

                toggleButton.textContent = isHidden
                    ? "View response"
                    : "Hide response";
            });

            card.append(
                question,
                timestamp,
                metadata,
                toggleButton,
                answerContainer
            );

            historyList.appendChild(card);
        });
    }

    async function loadInvestigationHistory() {
        if (!historyList || !historyStatus) return;

        if (refreshHistoryButton) {
            refreshHistoryButton.disabled = true;
            refreshHistoryButton.textContent = "Loading...";
        }

        historyStatus.textContent = "Loading investigation history...";

        try {
            const response = await window.KubeAuth.apiFetch("/api/history");

            if (!response.ok) {
                let message = "Unable to load investigation history.";

                try {
                    const errorData = await response.json();
                    message = errorData.detail || message;
                } catch {
                    // Keep the default error message.
                }

                throw new Error(message);
            }

            const data = await response.json();

            if (!Array.isArray(data.history)) {
                throw new Error("Unexpected response from the History API.");
            }

            investigationHistory = data.history;

            historyStatus.textContent =
                `${investigationHistory.length} investigation(s) loaded.`;

            renderHistory();

        } catch (error) {
            console.error("Failed to load investigation history:", error);

            historyStatus.textContent =
                error.message || "Unable to load investigation history.";

            historyList.replaceChildren();

            const errorMessage = document.createElement("p");
            errorMessage.textContent =
                "Please check your session and try refreshing.";

            historyList.appendChild(errorMessage);

        } finally {
            if (refreshHistoryButton) {
                refreshHistoryButton.disabled = false;
                refreshHistoryButton.textContent = "↻ Refresh";
            }
        }
    }
    if (refreshHistoryButton) {
        refreshHistoryButton.addEventListener(
            "click",
            loadInvestigationHistory
        );
    }

    if (historySearch) {
        historySearch.addEventListener("input", renderHistory);
    }

    function showRecommendations() {
        dashboardView.classList.add("hidden");
        secondaryView.classList.remove("hidden");
        clustersPage.classList.add("hidden");
        logsPage.classList.add("hidden");
        placeholderPage.classList.add("hidden");
        queryPage.classList.add("hidden");
        recommendationsPage.classList.remove("hidden");

        loadRecommendations();
    }
    
    document.getElementById("refreshRecommendations")
        .addEventListener("click", loadRecommendations);

    document.getElementById("recommendationSeverity")
        .addEventListener("change", loadRecommendations);

    document.getElementById("recommendationNamespace")
        .addEventListener("change", loadRecommendations);

    document.getElementById("recommendationsList")
        .addEventListener("click", async event => {
            const button = event.target.closest(
                ".copy-recommendation-command"
            );

            if (!button) return;

            try {
                await navigator.clipboard.writeText(
                    button.dataset.command
                );
                button.textContent = "Copied!";
                setTimeout(() => {
                    button.textContent = "Copy";
                }, 1500);
            } catch (error) {
                console.error("Could not copy command:", error);
            }
        });

    function showClusters() {
        dashboardView.classList.add("hidden");
        secondaryView.classList.remove("hidden");
        clustersPage.classList.remove("hidden");
        placeholderPage.classList.add("hidden");
        queryPage.classList.add("hidden");

        loadClustersPage();
    }
    
    function showQuery() {
        dashboardView.classList.add("hidden");
        secondaryView.classList.remove("hidden");
        clustersPage.classList.add("hidden");
        placeholderPage.classList.add("hidden");
        queryPage.classList.remove("hidden");
    }

    function showPlaceholder(title) {
        dashboardView.classList.add("hidden");
        secondaryView.classList.remove("hidden");
        clustersPage.classList.add("hidden");
        placeholderPage.classList.remove("hidden");
        logsPage.classList.add("hidden");

        secondaryTitle.textContent = title;
    }

    backToOverview.addEventListener("click", showOverview);

    document.getElementById("backToOverviewPlaceholder")
        .addEventListener("click", showOverview);

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

    // Logs Explorer: time-range controls
    const logsFrom = document.getElementById("logsFrom");
    const logsTo = document.getElementById("logsTo");
    const logsRangeStatus = document.getElementById("logsRangeStatus");
    const logsRangeButtons = document.querySelectorAll(
        "#logsPage .logs-range-button"
    );

    function formatDateTimeLocal(date) {
        const pad = value => String(value).padStart(2, "0");

        return (
            `${date.getFullYear()}-${pad(date.getMonth() + 1)}-` +
            `${pad(date.getDate())}T${pad(date.getHours())}:` +
            `${pad(date.getMinutes())}:${pad(date.getSeconds())}`
        );
    }

    function setLogsTimeRange(range, updateStatus = true) {
        const durations = {
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "3h": 180,
            "6h": 360,
            "12h": 720,
            "24h": 1440
        };

        const minutes = durations[range];

        if (!minutes || !logsFrom || !logsTo) {
            return;
        }

        const end = new Date();
        const start = new Date(end.getTime() - minutes * 60 * 1000);

        logsFrom.value = formatDateTimeLocal(start);
        logsTo.value = formatDateTimeLocal(end);

        logsRangeButtons.forEach(button => {
            const active = button.dataset.range === range;

            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });

        if (updateStatus && logsRangeStatus) {
            logsRangeStatus.textContent =
                `Selected range: last ${range}. Apply the range to query logs.`;
        }
    }

    // Quick-range buttons
    logsRangeButtons.forEach(button => {
        button.setAttribute(
            "aria-pressed",
            String(button.classList.contains("active"))
        );

        button.addEventListener("click", () => {
            setLogsTimeRange(button.dataset.range);
        });
    });

    // Initialize the default range to the last hour.
    setLogsTimeRange("1h");

    // ==========================================
    // LOGS EXPLORER: FETCH, FILTER, AND DISPLAY
    // ==========================================
    const logsRefreshButton = document.getElementById("logsRefreshButton");
    const logsApplyRange = document.getElementById("logsApplyRange");
    const logsTableBody = document.getElementById("logsTableBody");
    const logsTableContainer = document.getElementById("logsTableContainer");
    const logsEntryCount = document.getElementById("logsEntryCount");
    const logsLoading = document.getElementById("logsLoading");
    const logsError = document.getElementById("logsError");
    const logsEmpty = document.getElementById("logsEmpty");
    const logsSearch = document.getElementById("logsSearch");
    const logsLevel = document.getElementById("logsLevel");
    const logsDownloadButton = document.getElementById("logsDownloadButton");
    const logsAutoRefresh = document.getElementById("logsAutoRefresh");
    const logsRefreshInterval = document.getElementById("logsRefreshInterval");

    let fetchedLogEntries = [];
    let logsAutoRefreshTimer = null;
    let logsRequestInProgress = false;

    function setLogsMessage(element, message, visible) {
        if (!element) return;
        element.textContent = message;
        element.classList.toggle("hidden", !visible);
    }

    function parseLogEntries(rawLogs) {
        const text = String(rawLogs || "");
        const marker = "\nLogs:";
        const markerIndex = text.indexOf(marker);

        // Remove the MCP tool's metadata header when present.
        const body = markerIndex >= 0
            ? text.slice(markerIndex + marker.length)
            : text;

        return body
            .split(/\r?\n/)
            .filter(line => line.trim().length > 0)
            .map(line => {
                const match = line.match(
                    /^(\d{4}-\d{2}-\d{2}T\S+)\s+(.*)$/
                );

                const timestamp = match ? match[1] : "";
                const message = match ? match[2] : line;
                const levelMatch = message.match(
                    /\b(CRITICAL|FATAL|ERROR|WARN(?:ING)?|INFO|DEBUG|TRACE)\b/i
                );

                let level = levelMatch
                    ? levelMatch[1].toUpperCase()
                    : "OTHER";

                if (level === "WARNING") level = "WARN";

                return { timestamp, level, message };
            });
    }

    function renderLogs() {
        if (!logsTableBody) return;

        const searchTerm = (logsSearch?.value || "").trim().toLowerCase();
        const selectedLevel = (logsLevel?.value || "all").toLowerCase();

        const filteredLogs = fetchedLogEntries.filter(entry => {
            const matchesSearch =
                !searchTerm ||
                `${entry.timestamp} ${entry.level} ${entry.message}`
                    .toLowerCase()
                    .includes(searchTerm);

            const matchesLevel =
                selectedLevel === "all" ||
                entry.level.toLowerCase() === selectedLevel;

            return matchesSearch && matchesLevel;
        });

        logsTableBody.replaceChildren();

        filteredLogs.forEach(entry => {
            const row = document.createElement("tr");

            const timestampCell = document.createElement("td");
            timestampCell.textContent = entry.timestamp || "—";

            const levelCell = document.createElement("td");
            levelCell.textContent = entry.level;
            levelCell.className = `log-level-${entry.level.toLowerCase()}`;

            const messageCell = document.createElement("td");
            messageCell.textContent = entry.message;

            row.append(timestampCell, levelCell, messageCell);
            logsTableBody.appendChild(row);
        });

        if (logsEntryCount) {
            logsEntryCount.textContent =
                `${filteredLogs.length} of ${fetchedLogEntries.length} log entries`;
        }

        logsTableContainer?.classList.toggle(
            "hidden",
            filteredLogs.length === 0
        );

        setLogsMessage(
            logsEmpty,
            fetchedLogEntries.length === 0
                ? "No log entries returned for this pod and time range."
                : "No logs match the current search or level filter.",
            filteredLogs.length === 0
        );
    }

    async function loadLogs() {
        if (logsRequestInProgress) return;

        const namespace = logsNamespace?.value;
        const podName = logsPod?.value;

        if (!namespace || !podName) {
            fetchedLogEntries = [];
            renderLogs();
            setLogsMessage(
                logsError,
                "Select a namespace and pod before loading logs.",
                true
            );
            return;
        }

        const startValue = logsFrom?.value;
        const endValue = logsTo?.value;

        if (!startValue || !endValue) {
            setLogsMessage(
                logsError,
                "Select both the start and end times.",
                true
            );
            return;
        }

        const startDate = new Date(startValue);
        const endDate = new Date(endValue);

        if (
            Number.isNaN(startDate.getTime()) ||
            Number.isNaN(endDate.getTime()) ||
            startDate > endDate
        ) {
            setLogsMessage(
                logsError,
                "Enter a valid time range where From is earlier than To.",
                true
            );
            return;
        }

        const params = new URLSearchParams({
            pod_name: podName,
            namespace,
            start_time: startDate.toISOString(),
            end_time: endDate.toISOString()
        });

        if (logsContainer?.value) {
            params.set("container", logsContainer.value);
        }

        logsRequestInProgress = true;
        if (logsRefreshButton) logsRefreshButton.disabled = true;

        setLogsMessage(logsError, "", false);
        setLogsMessage(logsEmpty, "", false);
        setLogsMessage(logsLoading, "Loading Kubernetes logs...", true);

        try {
            const response = await window.KubeAuth.apiFetch(
                `/api/cluster/logs?${params.toString()}`
            );

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(
                    errorData.detail || `Log request failed (${response.status}).`
                );
            }

            const data = await response.json();
            fetchedLogEntries = parseLogEntries(data.logs);

            renderLogs();

            if (logsRangeStatus) {
                logsRangeStatus.textContent =
                    `Loaded ${fetchedLogEntries.length} log entries for ${podName}.`;
            }
        } catch (error) {
            console.error("Failed to load Kubernetes logs:", error);
            setLogsMessage(
                logsError,
                error.message || "Unable to load Kubernetes logs.",
                true
            );
        } finally {
            logsRequestInProgress = false;
            if (logsRefreshButton) logsRefreshButton.disabled = false;
            setLogsMessage(logsLoading, "", false);
        }
    }

    // Refresh and apply selected time range.
    logsRefreshButton?.addEventListener("click", loadLogs);
    logsApplyRange?.addEventListener("click", loadLogs);

    // Re-render locally when search or level filters change.
    logsSearch?.addEventListener("input", renderLogs);
    logsLevel?.addEventListener("change", renderLogs);

    // Clear stale entries when the selected pod or namespace changes.
    function clearDisplayedLogs() {
        fetchedLogEntries = [];
        if (logsTableBody) logsTableBody.replaceChildren();
        if (logsEntryCount) logsEntryCount.textContent = "No logs loaded";

        logsTableContainer?.classList.add("hidden");
        setLogsMessage(logsError, "", false);
        setLogsMessage(logsLoading, "", false);
        setLogsMessage(
            logsEmpty,
            "Select a namespace and pod, then apply a time range to load logs.",
            true
        );
    }

    logsNamespace?.addEventListener("change", clearDisplayedLogs);
    logsPod?.addEventListener("change", clearDisplayedLogs);
    logsContainer?.addEventListener("change", clearDisplayedLogs);

    // Automatically refresh at the selected interval.
    function configureLogsAutoRefresh() {
        if (logsAutoRefreshTimer !== null) {
            clearInterval(logsAutoRefreshTimer);
            logsAutoRefreshTimer = null;
        }

        if (logsAutoRefresh?.checked) {
            const seconds = Math.max(
                5,
                Number(logsRefreshInterval?.value || 10)
            );

            logsAutoRefreshTimer = setInterval(loadLogs, seconds * 1000);
        }
    }

    logsAutoRefresh?.addEventListener("change", configureLogsAutoRefresh);
    logsRefreshInterval?.addEventListener("change", configureLogsAutoRefresh);

    // Download the currently filtered entries.
    logsDownloadButton?.addEventListener("click", () => {
        const searchTerm = (logsSearch?.value || "").trim().toLowerCase();
        const selectedLevel = (logsLevel?.value || "all").toLowerCase();

        const entries = fetchedLogEntries.filter(entry => {
            const matchesSearch =
                !searchTerm ||
                `${entry.timestamp} ${entry.level} ${entry.message}`
                    .toLowerCase()
                    .includes(searchTerm);

            const matchesLevel =
                selectedLevel === "all" ||
                entry.level.toLowerCase() === selectedLevel;

            return matchesSearch && matchesLevel;
        });

        if (entries.length === 0) {
            setLogsMessage(
                logsError,
                "There are no log entries to download.",
                true
            );
            return;
        }

        const content = entries.map(entry =>
            `${entry.timestamp || "—"} [${entry.level}] ${entry.message}`
        ).join("\n");

        const blob = new Blob([content], {
            type: "text/plain;charset=utf-8"
        });

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "kube-insightai-pod-logs.txt";
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

                        // Copy button
                        const copyButton = document.createElement("button");

                        copyButton.className = "assistant-copy-button";
                        copyButton.type = "button";
                        copyButton.innerHTML = "📋 Copy";

                        copyButton.addEventListener("click", async () => {
                                try {
                                        if (navigator.clipboard && window.isSecureContext) {
                                                await navigator.clipboard.writeText(text);
                                        } else {
                                                const textArea = document.createElement("textarea");

                                                textArea.value = text;
                                                textArea.style.position = "fixed";
                                                textArea.style.left = "-9999px";
                                                textArea.style.top = "0";

                                                document.body.appendChild(textArea);

                                                textArea.focus();
                                                textArea.select();

                                                const copied = document.execCommand("copy");

                                                document.body.removeChild(textArea);

                                                if (!copied) {
                                                        throw new Error("Fallback copy command failed");
                                                }
                                        }

                                        copyButton.innerHTML = "✓ Copied";

                                        setTimeout(() => {
                                                copyButton.innerHTML = "📋 Copy";
                                        }, 2000);

                                } catch (error) {
                                        console.error("Failed to copy response:", error);
                                        copyButton.innerHTML = "⚠ Copy failed";

                                        setTimeout(() => {
                                                copyButton.innerHTML = "📋 Copy";
                                        }, 2000);
                                }
                        });
                        message.appendChild(copyButton);
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
                        const response = await window.KubeAuth.apiFetch(API_URL, {
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
        async function loadClustersNamespaces() {
            if (!clustersNamespaceSelector) return;

            try {
                clustersNamespaceSelector.innerHTML =
                    `<option value="">Loading namespaces...</option>`;

                const response = await window.KubeAuth.apiFetch(
                    "/api/cluster/namespaces"
                );

                if (!response.ok) {
                    throw new Error("Failed to load namespaces.");
                }

                const data = await response.json();
                const namespaces = data.namespaces || [];

                clustersNamespaceSelector.innerHTML = "";

                if (namespaces.length === 0) {
                    clustersNamespaceSelector.innerHTML =
                        `<option value="">No namespaces found</option>`;
                    return;
                }

                namespaces.forEach(namespace => {
                    const option = document.createElement("option");
                    option.value = namespace.name;
                    option.textContent = namespace.name;
                    clustersNamespaceSelector.appendChild(option);
                });

                // Prefer the namespace already used by the dashboard.
                const preferredNamespace = namespaceSelector?.value;

                if (
                    preferredNamespace &&
                    namespaces.some(ns => ns.name === preferredNamespace)
                ) {
                    clustersNamespaceSelector.value = preferredNamespace;
                } else {
                    clustersNamespaceSelector.value = namespaces[0].name;
                }

            } catch (error) {
                console.error("Failed to load Clusters namespaces:", error);

                clustersNamespaceSelector.innerHTML =
                    `<option value="">Failed to load namespaces</option>`;

                clustersStatus.textContent =
                    "Unable to load namespaces. Check the API and try again.";
            }
        }
        
        // render Clusters Pods
        function renderClustersPods(pods) {
            if (!pods.length || pods.every(p => p.error)) {
                clustersPodsTable.innerHTML =
                    `<tr><td colspan="4">No pods found.</td></tr>`;
                return;
            }

            clustersPodsTable.innerHTML = pods.map(pod => {
                const restarts = (pod.containers || []).reduce(
                    (total, container) => total + (container.restart_count || 0),
                    0
                );

                const ready = `${pod.ready_containers || 0}/${pod.total_containers || 0}`;

                return `
                    <tr>
                        <td>${escapeHTML(pod.name || "Unknown")}</td>
                        <td>${escapeHTML(pod.status || "Unknown")}</td>
                        <td>${ready}</td>
                        <td>${restarts}</td>
                    </tr>
                `;
            }).join("");
        }

        function renderClustersDeployments(deployments) {
            if (!deployments.length || deployments.every(d => d.error)) {
                clustersDeploymentsTable.innerHTML =
                    `<tr><td colspan="3">No deployments found.</td></tr>`;
                return;
            }

            clustersDeploymentsTable.innerHTML = deployments.map(deployment => `
                <tr>
                    <td>${escapeHTML(deployment.name || "Unknown")}</td>
                    <td>${deployment.ready_replicas ?? 0}</td>
                    <td>${deployment.desired_replicas ?? 0}</td>
                </tr>
            `).join("");
        }

        function renderClustersServices(services) {
            if (!services.length || services.every(s => s.error)) {
                clustersServicesTable.innerHTML =
                    `<tr><td colspan="3">No services found.</td></tr>`;
                return;
            }

            clustersServicesTable.innerHTML = services.map(service => `
                <tr>
                    <td>${escapeHTML(service.name || "Unknown")}</td>
                    <td>${escapeHTML(service.type || "Unknown")}</td>
                    <td>${escapeHTML(service.cluster_ip || "None")}</td>
                </tr>
            `).join("");
        }

        function escapeHTML(value) {
            return String(value).replace(/[&<>"']/g, character => ({
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            })[character]);
        }

        async function loadClustersPage() {
            clustersStatus.textContent = "Loading Kubernetes resources...";

            clustersPodsTable.innerHTML =
                `<tr><td colspan="4">Loading pods...</td></tr>`;

            clustersDeploymentsTable.innerHTML =
                `<tr><td colspan="3">Loading deployments...</td></tr>`;

            clustersServicesTable.innerHTML =
                `<tr><td colspan="3">Loading services...</td></tr>`;

            try {
                // Load namespaces before retrieving resources.
                if (!clustersNamespaceSelector.options.length ||
                    !clustersNamespaceSelector.value) {
                    await loadClustersNamespaces();
                }

                const namespace = clustersNamespaceSelector.value;

                if (!namespace) {
                    throw new Error("No namespace is selected.");
                }

                const response = await window.KubeAuth.apiFetch(
                    `/api/cluster/overview?namespace=${encodeURIComponent(namespace)}`
                );

                if (!response.ok) {
                    throw new Error("Failed to retrieve cluster resources.");
                }

                const data = await response.json();

                if (data.detail) {
                    throw new Error(data.detail);
                }

                const pods = data.pods || [];
                const deployments = data.deployments || [];
                const services = data.services || [];

                // Update summary counts.
                document.getElementById("clustersPodCount").textContent =
                    pods.filter(item => !item.error).length;

                document.getElementById("clustersDeploymentCount").textContent =
                    deployments.filter(item => !item.error).length;

                document.getElementById("clustersServiceCount").textContent =
                    services.filter(item => !item.error).length;

                // Render resource tables.
                renderClustersPods(pods);
                renderClustersDeployments(deployments);
                renderClustersServices(services);

                clustersStatus.textContent =
                    `Showing resources in namespace: ${namespace}`;

            } catch (error) {
                console.error("Failed to load Clusters page:", error);

                clustersStatus.textContent =
                    `Failed to load resources: ${error.message}`;

                clustersPodsTable.innerHTML =
                    `<tr><td colspan="4">Unable to load pods.</td></tr>`;

                clustersDeploymentsTable.innerHTML =
                    `<tr><td colspan="3">Unable to load deployments.</td></tr>`;

                clustersServicesTable.innerHTML =
                    `<tr><td colspan="3">Unable to load services.</td></tr>`;
            }
        }

        clustersNamespaceSelector.addEventListener("change", () => {
            loadClustersPage();
        });

        document.getElementById("refreshClusters").addEventListener("click", () => {
            loadClustersPage();
        });



});