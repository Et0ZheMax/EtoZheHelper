let sessionId = null;

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#chat-messages");
const sourcesList = document.querySelector("#sources-list");

function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    const strong = document.createElement("strong");
    strong.textContent = role === "user" ? "You" : role === "error" ? "Error" : "Assistant";
    const body = document.createElement("div");
    body.textContent = text;
    div.append(strong, body);
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function renderSources(sources) {
    sourcesList.innerHTML = "";
    sourcesList.classList.remove("empty");
    if (!sources.length) {
        sourcesList.classList.add("empty");
        sourcesList.textContent = "Совпадений в базе знаний не найдено.";
        return;
    }
    for (const source of sources) {
        const item = document.createElement("article");
        item.className = "source-item";
        const title = document.createElement("h3");
        title.textContent = source.title;
        const meta = document.createElement("code");
        meta.textContent = `${source.path} · score ${source.score}`;
        const snippet = document.createElement("p");
        snippet.textContent = source.snippet;
        item.append(title, meta, snippet);
        sourcesList.appendChild(item);
    }
}

form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;

    appendMessage("user", message);
    input.value = "";
    const button = form.querySelector("button");
    button.disabled = true;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({message, session_id: sessionId}),
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        const data = await response.json();
        sessionId = data.session_id;
        appendMessage("assistant", data.answer);
        renderSources(data.sources || []);
    } catch (error) {
        appendMessage("error", `Не удалось получить ответ: ${error.message}`);
    } finally {
        button.disabled = false;
        input.focus();
    }
});
