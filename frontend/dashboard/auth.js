


(() => {
    "use strict";

    const TOKEN_KEY = "kubeInsightAccessToken";
    const USER_KEY = "kubeInsightUser";

    function getToken() {
        return sessionStorage.getItem(TOKEN_KEY);
    }

    function getUser() {
        try {
            const value = sessionStorage.getItem(USER_KEY);
            return value ? JSON.parse(value) : null;
        } catch {
            return null;
        }
    }

    function saveSession(token, user) {
        sessionStorage.setItem(TOKEN_KEY, token);
        sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    }

    function clearSession() {
        sessionStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(USER_KEY);
    }

    async function login(username, password) {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok || !data.access_token) {
            throw new Error(data.detail || "Unable to sign in.");
        }

        const userResponse = await fetch("/api/auth/me", {
            headers: {
                Authorization: `Bearer ${data.access_token}`
            }
        });

        const user = await userResponse.json().catch(() => ({}));

        if (!userResponse.ok || !user.username || !user.is_active) {
            throw new Error("Unable to verify your session. Please sign in again.");
        }

        saveSession(data.access_token, user);
        return user;
    }

    async function restoreSession() {
        const token = getToken();

        if (!token) {
            clearSession();
            return null;
        }

        try {
            const response = await fetch("/api/auth/me", {
                headers: { Authorization: `Bearer ${token}` }
            });

            if (!response.ok) {
                clearSession();
                return null;
            }

            const user = await response.json();

            if (!user.username || !user.is_active) {
                clearSession();
                return null;
            }

            sessionStorage.setItem(USER_KEY, JSON.stringify(user));
            return user;
        } catch {
            // Preserve the token if this was a temporary network failure.
            return null;
        }
    }

    async function apiFetch(url, options = {}) {
        const token = getToken();

        if (!token) {
            throw new Error("Please sign in to continue.");
        }

        const headers = new Headers(options.headers || {});
        headers.set("Authorization", `Bearer ${token}`);

        const response = await fetch(url, {
            ...options,
            headers
        });

        if (response.status === 401) {
            clearSession();
            window.dispatchEvent(new Event("auth:unauthorized"));
        }

        return response;
    }

    window.KubeAuth = {
        login,
        restoreSession,
        apiFetch,
        getToken,
        getUser,
        clearSession
    };
})();