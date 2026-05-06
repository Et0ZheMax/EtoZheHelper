let sessionId = null;

const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#chat-messages");
const sourcesList = document.querySelector("#sources-list");
const reloadButton = document.querySelector("#reload-kb");
const reloadStatus = document.querySelector("#reload-status");
const documentsCount = document.querySelector("#documents-count");
const knowledgeBaseDir = document.querySelector("#knowledge-base-dir");
const domainsList = document.querySelector("#domains-list");
const typesList = document.querySelector("#types-list");

function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    const strong = document.createElement("strong");
    strong.textContent = role === "user" ? "You" : role === "error" ? "Error" : "Assistant";
    const body = document.createElement("div");
    body.className = "message-body";
    body.textContent = text;
    div.append(strong, body);
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function renderTaxonomy(container, items, emptyText) {
    if (!container) return;
    container.innerHTML = "";
    const entries = Object.entries(items || {});
    if (!entries.length) {
        const empty = document.createElement("span");
        empty.className = "muted small";
        empty.textContent = emptyText;
        container.appendChild(empty);
        return;
    }
    for (const [name, count] of entries) {
        const pill = document.createElement("span");
        pill.className = "pill";
        const label = document.createElement("span");
        label.textContent = name;
        const value = document.createElement("strong");
        value.textContent = count;
        pill.append(label, value);
        container.appendChild(pill);
    }
}

function renderStats(stats) {
    if (documentsCount) documentsCount.textContent = stats.documents_count;
    if (knowledgeBaseDir) knowledgeBaseDir.textContent = stats.knowledge_base_dir;
    renderTaxonomy(domainsList, stats.domains, "Нет domain metadata.");
    renderTaxonomy(typesList, stats.types, "Нет type metadata.");
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

        const path = document.createElement("code");
        path.textContent = source.path;

        const score = document.createElement("span");
        score.className = "score";
        score.textContent = `score ${source.score}`;

        const snippet = document.createElement("p");
        snippet.className = "snippet";
        snippet.textContent = source.snippet || "Snippet отсутствует.";

        item.append(title, path, score, snippet);
        sourcesList.appendChild(item);
    }
}

reloadButton?.addEventListener("click", async () => {
    reloadButton.disabled = true;
    reloadStatus.textContent = "Reloading knowledge base…";
    try {
        const reloadResponse = await fetch("/api/kb/reload", {method: "POST"});
        if (!reloadResponse.ok) {
            throw new Error(`Reload failed: ${reloadResponse.status}`);
        }
        const reloadData = await reloadResponse.json();
        const statsResponse = await fetch("/api/kb/stats");
        if (!statsResponse.ok) {
            throw new Error(`Stats failed: ${statsResponse.status}`);
        }
        renderStats(await statsResponse.json());
        reloadStatus.textContent = `KB reloaded: ${reloadData.documents_count} documents.`;
    } catch (error) {
        reloadStatus.textContent = `Не удалось обновить KB: ${error.message}`;
    } finally {
        reloadButton.disabled = false;
    }
});

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
            let details = `API error: ${response.status}`;
            try {
                const payload = await response.json();
                if (payload.detail) details = payload.detail;
            } catch (_) {
                // Keep the generic HTTP status when the response is not JSON.
            }
            throw new Error(details);
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
