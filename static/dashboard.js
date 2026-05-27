const API_KEY_STORAGE = "agrovision_api_key";

const img = document.getElementById("live-frame");
const statusEl = document.getElementById("status");
const eventsContainer = document.getElementById("events-container");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatHistoryEl = document.getElementById("chat-history");
const weatherContainer = document.getElementById("weather-container");
const weatherStatus = document.getElementById("weather-status");
const apiKeyCard = document.getElementById("api-key-card");
const apiKeyForm = document.getElementById("api-key-form");
const apiKeyInput = document.getElementById("api-key-input");
const apiKeyStatus = document.getElementById("api-key-status");
const apiKeyClear = document.getElementById("api-key-clear");

const apiKeyRequired = document.body.dataset.apiKeyRequired === "true";
const chatHistory = [];

if (apiKeyRequired) {
    apiKeyCard.hidden = false;
    refreshApiKeyStatus();
}

function getApiKey() {
    try {
        return localStorage.getItem(API_KEY_STORAGE) || "";
    } catch {
        return "";
    }
}

function setApiKey(value) {
    try {
        if (value) {
            localStorage.setItem(API_KEY_STORAGE, value);
        } else {
            localStorage.removeItem(API_KEY_STORAGE);
        }
    } catch {
        // ignore storage failures (private mode etc.)
    }
}

function refreshApiKeyStatus() {
    if (!apiKeyStatus) return;
    const stored = getApiKey();
    apiKeyStatus.textContent = stored
        ? "Chave salva neste navegador."
        : "Nenhuma chave salva. Funcoes protegidas ficarao indisponiveis.";
}

function authHeaders(extra) {
    const headers = Object.assign({}, extra || {});
    const key = getApiKey();
    if (key) {
        headers["X-API-Key"] = key;
    }
    return headers;
}

async function authFetch(url, options) {
    const opts = Object.assign({}, options || {});
    opts.headers = authHeaders(opts.headers);
    return fetch(url, opts);
}

function addChatMessage(role, content, kind = "") {
    const div = document.createElement("div");
    div.className = `chat-message ${role}${kind ? " " + kind : ""}`;
    div.textContent = `${role === "user" ? "Você" : "Agente"}: ${content}`;
    chatHistoryEl.appendChild(div);
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    return div;
}

function handleProtectedStatus(response) {
    if (response.status === 401) {
        statusEl.textContent = "Acesso negado. Verifique a API key.";
        return true;
    }
    if (response.status === 429) {
        statusEl.textContent = "Muitas requisicoes. Aguarde alguns segundos.";
        return true;
    }
    return false;
}

async function refreshFrame() {
    try {
        const response = await authFetch("/frame");
        if (handleProtectedStatus(response)) return;
        if (response.status === 503) {
            statusEl.textContent = "Aguardando camera...";
            return;
        }
        if (!response.ok) {
            statusEl.textContent = "Falha temporaria no feed.";
            return;
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const previous = img.dataset.objectUrl;
        if (previous) URL.revokeObjectURL(previous);
        img.dataset.objectUrl = url;
        img.src = url;
        statusEl.textContent = "Conectado";
    } catch {
        statusEl.textContent = "Aguardando camera...";
    }
}

async function refreshEvents() {
    try {
        const response = await authFetch("/events");
        if (response.status === 401) {
            eventsContainer.innerHTML = "<p class='no-events'>Acesso negado. Configure a API key.</p>";
            return;
        }
        if (!response.ok) {
            eventsContainer.innerHTML = "<p class='no-events'>Falha ao carregar eventos.</p>";
            return;
        }
        const events = await response.json();
        if (!events.length) {
            eventsContainer.innerHTML = "<p class='no-events'>Nenhum evento registrado ainda.</p>";
            return;
        }

        let html = "<table><thead><tr><th>Data/Hora</th><th>Classe</th><th>Confianca</th><th>Imagem</th></tr></thead><tbody>";
        events.forEach((event) => {
            html += `<tr>
                <td>${event.event_time}</td>
                <td>${event.label}</td>
                <td>${Number(event.confidence || 0).toFixed(2)}</td>
                <td><img class="capture-img" src="${event.image_path}" alt="${event.label}"
                     onerror="this.outerHTML='<div class=\\'capture-placeholder\\'>Sem imagem</div>'"></td>
            </tr>`;
        });
        html += "</tbody></table>";
        eventsContainer.innerHTML = html;
    } catch {
        eventsContainer.innerHTML = "<p class='no-events'>Falha ao carregar eventos.</p>";
    }
}

function renderWeatherAlerts(payload) {
    if (!weatherContainer) return;
    if (!payload || !Array.isArray(payload.alerts)) {
        weatherContainer.innerHTML = "<p class='no-events'>Sem dados climaticos.</p>";
        return;
    }

    if (!payload.alerts.length) {
        weatherContainer.innerHTML = "<p class='no-events'>Nenhum alerta ativo.</p>";
        return;
    }

    let html = "<ul class='weather-alerts'>";
    payload.alerts.forEach((alert) => {
        const title = alert.title || "Alerta";
        const severity = alert.severity ? ` - ${alert.severity}` : "";
        const area = alert.area ? `<div class='weather-area'>${alert.area}</div>` : "";
        const link = alert.link ? `<a href='${alert.link}' target='_blank' rel='noopener'>Detalhes</a>` : "";
        html += `<li><strong>${title}${severity}</strong>${area}${link}</li>`;
    });
    html += "</ul>";
    weatherContainer.innerHTML = html;
}

async function refreshWeatherAlerts() {
    if (!weatherContainer) return;
    try {
        const response = await authFetch("/weather/alerts");
        if (response.status === 401) {
            weatherContainer.innerHTML = "<p class='no-events'>Acesso negado. Configure a API key.</p>";
            return;
        }
        if (!response.ok) {
            weatherContainer.innerHTML = "<p class='no-events'>Falha ao carregar alertas.</p>";
            return;
        }
        const payload = await response.json();
        renderWeatherAlerts(payload);
        if (weatherStatus) {
            const status = payload.status || "desconhecido";
            weatherStatus.textContent = `Fonte: INMET | Status: ${status}`;
        }
    } catch {
        weatherContainer.innerHTML = "<p class='no-events'>Falha ao carregar alertas.</p>";
    }
}

async function submitChat(event) {
    event.preventDefault();
    const question = chatInput.value.trim();
    if (!question) {
        return;
    }

    addChatMessage("user", question);
    chatHistory.push({ role: "user", content: question });
    chatInput.value = "";

    const assistantMessageEl = addChatMessage("assistant", "");
    assistantMessageEl.textContent = "Agente: ";
    let fullAnswer = "";

    try {
        const response = await authFetch("/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, history: chatHistory }),
        });

        if (response.status === 401) {
            throw new Error("Credenciais ausentes ou invalidas. Configure a API key.");
        }
        if (response.status === 429) {
            throw new Error("Muitas perguntas em sequencia. Aguarde alguns segundos.");
        }
        if (!response.ok) {
            throw new Error("Falha temporaria ao gerar resposta.");
        }
        if (!response.body) {
            throw new Error("Resposta sem stream.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            const chunk = decoder.decode(value, { stream: true });
            fullAnswer += chunk;
            assistantMessageEl.textContent = `Agente: ${fullAnswer}`;
            chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
        }

        const finalAnswer = fullAnswer.trim();
        if (!finalAnswer) {
            throw new Error("Sem resposta do agente.");
        }
        chatHistory.push({ role: "assistant", content: finalAnswer });
    } catch (error) {
        assistantMessageEl.className = "chat-message assistant error";
        assistantMessageEl.textContent = `Agente: ${error.message}`;
    }
}

if (apiKeyForm) {
    apiKeyForm.addEventListener("submit", (event) => {
        event.preventDefault();
        const value = apiKeyInput.value.trim();
        setApiKey(value);
        apiKeyInput.value = "";
        refreshApiKeyStatus();
        refreshEvents();
        refreshFrame();
        refreshWeatherAlerts();
    });
}

if (apiKeyClear) {
    apiKeyClear.addEventListener("click", () => {
        setApiKey("");
        apiKeyInput.value = "";
        refreshApiKeyStatus();
        refreshEvents();
        refreshFrame();
        refreshWeatherAlerts();
    });
}

chatForm.addEventListener("submit", submitChat);

refreshEvents();
refreshFrame();
refreshWeatherAlerts();
setInterval(refreshFrame, 250);
setInterval(refreshEvents, 3000);
setInterval(refreshWeatherAlerts, 5 * 60 * 1000);
