const img = document.getElementById("live-frame");
const statusEl = document.getElementById("status");
const eventsContainer = document.getElementById("events-container");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatHistoryEl = document.getElementById("chat-history");

const chatHistory = [];

function addChatMessage(role, content, kind = "") {
    const div = document.createElement("div");
    div.className = `chat-message ${role}${kind ? " " + kind : ""}`;
    div.textContent = `${role === "user" ? "Você" : "Agente"}: ${content}`;
    chatHistoryEl.appendChild(div);
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
    return div;
}

function refreshFrame() {
    const newImg = new Image();
    newImg.onload = function () {
        img.src = newImg.src;
        statusEl.textContent = "Conectado";
    };
    newImg.onerror = function () {
        statusEl.textContent = "Aguardando câmera...";
    };
    newImg.src = "/frame?" + Date.now();
}

async function refreshEvents() {
    try {
        const response = await fetch("/events");
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
    } catch (error) {
        eventsContainer.innerHTML = "<p class='no-events'>Falha ao carregar eventos.</p>";
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
        const response = await fetch("/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, history: chatHistory }),
        });
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || "Falha no chat");
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

chatForm.addEventListener("submit", submitChat);

refreshEvents();
setInterval(refreshFrame, 250);
setInterval(refreshEvents, 3000);
