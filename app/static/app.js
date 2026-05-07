let sessionId = null;
let currentSessionTitle = "";
let selectedHostId = null;
let selectedHostName = "";

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
const sessionsList = document.querySelector("#sessions-list");
const newSessionButton = document.querySelector("#new-session-button");
const currentSessionTitleNode = document.querySelector("#current-session-title");
const renameSessionButton = document.querySelector("#rename-session-button");
const deleteSessionButton = document.querySelector("#delete-session-button");
const currentHostTitleNode = document.querySelector("#current-host-title");
const newHostButton = document.querySelector("#new-host-button");
const hostsList = document.querySelector("#hosts-list");
const hostsStatus = document.querySelector("#hosts-status");
const kbSearchInput = document.querySelector("#kb-search-input");
const kbDomainFilter = document.querySelector("#kb-domain-filter");
const kbTypeFilter = document.querySelector("#kb-type-filter");
const kbRiskFilter = document.querySelector("#kb-risk-filter");
const kbTagFilter = document.querySelector("#kb-tag-filter");
const kbTagOptions = document.querySelector("#kb-tag-options");
const kbSearchButton = document.querySelector("#kb-search-button");
const kbBrowserStatus = document.querySelector("#kb-browser-status");
const kbResults = document.querySelector("#kb-results");
const kbDocumentDetail = document.querySelector("#kb-document-detail");
const kbDocumentTitle = document.querySelector("#kb-document-title");
const kbDocumentPath = document.querySelector("#kb-document-path");
const kbDocumentContent = document.querySelector("#kb-document-content");
const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel-section");

function appendMessage(role, text, actions = []) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    const strong = document.createElement("strong");
    strong.textContent = role === "user" ? "You" : role === "error" ? "Error" : "Assistant";
    const body = document.createElement("div");
    body.className = "message-body";
    body.textContent = text;
    div.append(strong, body);
    if (role === "assistant" && actions.length) {
        div.appendChild(renderActionCards(actions));
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
}

function renderActionCards(actions) {
    const wrapper = document.createElement("section");
    wrapper.className = "action-cards";

    const title = document.createElement("h3");
    title.textContent = "Suggested safe actions";
    wrapper.appendChild(title);

    for (const action of actions) {
        const card = document.createElement("article");
        card.className = "action-card";

        const heading = document.createElement("div");
        heading.className = "action-card-heading";
        heading.textContent = `[${action.action}] risk: ${action.risk} read-only: ${action.read_only}`;

        const label = document.createElement("div");
        label.className = "action-label";
        label.textContent = action.label || action.action;

        const previewLabel = document.createElement("span");
        previewLabel.className = "muted small";
        previewLabel.textContent = "command preview:";

        const preview = document.createElement("code");
        preview.textContent = action.command_preview || "";

        const disabled = document.createElement("div");
        disabled.className = "execution-disabled";
        disabled.textContent = "Execution disabled in this stage";

        card.append(heading, label, previewLabel, preview);
        if (selectedHostName) {
            const hostContext = document.createElement("div");
            hostContext.className = "target-host-context";
            hostContext.textContent = `Target host context: ${selectedHostName}`;
            card.appendChild(hostContext);
        }
        card.appendChild(disabled);
        wrapper.appendChild(card);
    }
    return wrapper;
}

function showWelcomeMessage() {
    messages.replaceChildren();
    appendMessage("assistant", "Привет! Опиши проблему. Я поищу по локальной Markdown-базе и предложу безопасный старт диагностики.");
}

function setCurrentSession(id, title) {
    sessionId = id;
    currentSessionTitle = title || "";
    currentSessionTitleNode.textContent = id ? `Current investigation: ${currentSessionTitle}` : "No investigation selected";
    if (renameSessionButton) renameSessionButton.disabled = !id;
    if (deleteSessionButton) deleteSessionButton.disabled = !id;
}

function renderMessages(history) {
    messages.replaceChildren();
    if (!history.length) {
        appendMessage("assistant", "Новая investigation создана. Опиши проблему, чтобы начать диагностику.");
        return;
    }
    for (const item of history) {
        appendMessage(item.role, item.content);
    }
}

function formatSessionDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
}


function setSelectedHost(host) {
    selectedHostId = host?.id || null;
    selectedHostName = host?.name || "";
    if (currentHostTitleNode) {
        currentHostTitleNode.textContent = selectedHostName ? `Current host: ${selectedHostName}` : "Current host: none";
    }
    if (hostsList) {
        for (const item of hostsList.querySelectorAll(".host-item")) {
            item.classList.toggle("active", Number(item.dataset.hostId) === selectedHostId);
        }
    }
}

function renderHosts(items) {
    if (!hostsList) return;
    hostsList.replaceChildren();
    hostsList.classList.remove("empty");
    if (!items.length) {
        hostsList.classList.add("empty");
        hostsList.textContent = "No hosts yet.";
        setSelectedHost(null);
        return;
    }
    if (selectedHostId && !items.some((item) => item.id === selectedHostId)) {
        setSelectedHost(null);
    }
    for (const host of items) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "host-item";
        button.dataset.hostId = String(host.id);
        button.classList.toggle("active", host.id === selectedHostId);
        button.addEventListener("click", () => setSelectedHost(host));

        const title = document.createElement("span");
        title.className = "host-title";
        title.textContent = host.name;

        const endpoint = document.createElement("span");
        endpoint.className = "host-meta";
        endpoint.textContent = `${host.hostname}:${host.port}`;

        const tags = document.createElement("span");
        tags.className = "host-meta";
        tags.textContent = host.tags?.length ? `tags: ${host.tags.join(", ")}` : "tags: —";

        const status = document.createElement("span");
        status.className = "host-meta";
        status.textContent = host.enabled ? "enabled" : "disabled";

        button.append(title, endpoint, tags, status);
        hostsList.appendChild(button);
    }
}

async function loadHosts() {
    if (!hostsList) return null;
    const response = await fetch("/api/hosts?limit=50&offset=0");
    if (!response.ok) throw new Error(`Hosts failed: ${response.status}`);
    const data = await response.json();
    renderHosts(data.items || []);
    if (hostsStatus) hostsStatus.textContent = "Inventory only. No SSH connection is performed in this stage.";
    return data;
}

async function createHostFromPrompt() {
    if (!newHostButton) return;
    const name = prompt("Host display name, e.g. app01");
    if (name === null) return;
    const hostname = prompt("Hostname or IP, e.g. app01.example.local");
    if (hostname === null) return;
    const tagsInput = prompt("Tags comma-separated, e.g. nginx,prod", "") || "";
    const tags = tagsInput.split(",").map((item) => item.trim()).filter(Boolean);
    newHostButton.disabled = true;
    try {
        const response = await fetch("/api/hosts", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name: name.trim(), hostname: hostname.trim(), port: 22, os_family: "linux", enabled: true, tags}),
        });
        if (!response.ok) {
            let details = `Create host failed: ${response.status}`;
            try {
                const payload = await response.json();
                if (payload.detail) details = Array.isArray(payload.detail) ? JSON.stringify(payload.detail) : payload.detail;
            } catch (_) {
                // Keep generic status if response is not JSON.
            }
            throw new Error(details);
        }
        const host = await response.json();
        await loadHosts();
        setSelectedHost(host);
        if (hostsStatus) hostsStatus.textContent = `Host added: ${host.name}. No SSH connection was performed.`;
    } catch (error) {
        if (hostsStatus) hostsStatus.textContent = `Не удалось добавить host: ${error.message}`;
    } finally {
        newHostButton.disabled = false;
    }
}

function renderSessions(items) {
    sessionsList.replaceChildren();
    sessionsList.classList.remove("empty");
    if (!items.length) {
        sessionsList.classList.add("empty");
        sessionsList.textContent = "Истории пока нет.";
        return;
    }

    for (const item of items) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "session-item";
        button.classList.toggle("active", item.id === sessionId);
        button.addEventListener("click", () => openSession(item.id));

        const title = document.createElement("span");
        title.className = "session-title";
        title.textContent = item.title;

        const meta = document.createElement("span");
        meta.className = "session-meta";
        meta.textContent = `updated: ${formatSessionDate(item.updated_at)} · ${item.messages_count} messages`;

        const preview = document.createElement("span");
        preview.className = "session-meta session-preview";
        preview.textContent = item.preview || "No messages yet.";

        button.append(title, meta, preview);
        sessionsList.appendChild(button);
    }
}

async function loadSessions(options = {}) {
    const {openNewest = false} = options;
    const response = await fetch("/api/chat/sessions?limit=50&offset=0");
    if (!response.ok) throw new Error(`Sessions failed: ${response.status}`);
    const data = await response.json();
    renderSessions(data.items || []);
    if (openNewest && data.items?.length) {
        await openSession(data.items[0].id);
    }
    return data;
}

async function createNewSession() {
    if (newSessionButton) newSessionButton.disabled = true;
    try {
        const response = await fetch("/api/chat/session", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({title: "New investigation"}),
        });
        if (!response.ok) throw new Error(`Create failed: ${response.status}`);
        const data = await response.json();
        setCurrentSession(data.id, data.title);
        renderMessages([]);
        await loadSessions();
        input?.focus();
    } catch (error) {
        appendMessage("error", `Не удалось создать investigation: ${error.message}`);
    } finally {
        if (newSessionButton) newSessionButton.disabled = false;
    }
}

async function openSession(id) {
    const response = await fetch(`/api/chat/session/${id}`);
    if (!response.ok) throw new Error(`Session failed: ${response.status}`);
    const data = await response.json();
    setCurrentSession(data.id, data.title);
    renderMessages(data.messages || []);
    await loadSessions();
    input?.focus();
}

async function renameCurrentSession() {
    if (!sessionId) return;
    const newTitle = prompt("New investigation title", currentSessionTitle);
    if (newTitle === null) return;
    const title = newTitle.trim();
    if (!title) {
        alert("Investigation title must not be empty.");
        return;
    }
    try {
        const response = await fetch(`/api/chat/session/${sessionId}`, {
            method: "PATCH",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({title}),
        });
        if (!response.ok) throw new Error(`Rename failed: ${response.status}`);
        const data = await response.json();
        setCurrentSession(data.id, data.title);
        await loadSessions();
    } catch (error) {
        appendMessage("error", `Не удалось переименовать investigation: ${error.message}`);
    }
}

async function deleteCurrentSession() {
    if (!sessionId) return;
    if (!confirm("Delete this investigation?")) return;
    const deletedId = sessionId;
    try {
        const response = await fetch(`/api/chat/session/${deletedId}`, {method: "DELETE"});
        if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
        setCurrentSession(null, "");
        showWelcomeMessage();
        const data = await loadSessions();
        if (data.items?.length) {
            await openSession(data.items[0].id);
        }
    } catch (error) {
        appendMessage("error", `Не удалось удалить investigation: ${error.message}`);
    }
}

function replaceOptions(select, items, allText) {
    if (!select) return;
    const selected = select.value;
    select.replaceChildren();
    const allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = allText;
    select.appendChild(allOption);
    for (const name of Object.keys(items || {})) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
    }
    if ([...select.options].some((option) => option.value === selected)) {
        select.value = selected;
    }
}

function replaceDatalist(datalist, items) {
    if (!datalist) return;
    datalist.replaceChildren();
    for (const name of Object.keys(items || {})) {
        const option = document.createElement("option");
        option.value = name;
        datalist.appendChild(option);
    }
}

function renderTaxonomy(container, items, emptyText) {
    if (!container) return;
    container.replaceChildren();
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
    replaceOptions(kbDomainFilter, stats.domains, "All domains");
    replaceOptions(kbTypeFilter, stats.types, "All types");
    replaceOptions(kbRiskFilter, stats.risks, "All risks");
    replaceDatalist(kbTagOptions, stats.tags);
}

function sourceArticle(source, clickable = false) {
    const item = document.createElement("article");
    item.className = "source-item";
    const metadata = source.metadata || {};
    const domain = source.domain || metadata.domain || "";
    const docType = source.doc_type || metadata.doc_type || metadata.type || "";
    const risk = source.risk || metadata.risk || "";
    const sourceTags = source.tags || metadata.tags || [];
    const normalizedTags = Array.isArray(sourceTags) ? sourceTags : [];

    const title = document.createElement("h3");
    title.textContent = source.title;

    const path = document.createElement("code");
    path.textContent = source.path;

    const meta = document.createElement("div");
    meta.className = "meta-line";
    meta.textContent = [domain, docType, risk].filter(Boolean).join(" / ") || "metadata отсутствует";

    const tags = document.createElement("div");
    tags.className = "tags-line";
    tags.textContent = normalizedTags.length ? `tags: ${normalizedTags.join(", ")}` : "tags: —";

    const snippet = document.createElement("p");
    snippet.className = "snippet";
    snippet.textContent = source.snippet || "Snippet отсутствует.";

    item.append(title, path, meta, tags);
    if (source.score !== undefined) {
        const score = document.createElement("span");
        score.className = "score";
        score.textContent = `score ${source.score}`;
        item.appendChild(score);
    }
    item.appendChild(snippet);

    if (clickable) {
        item.classList.add("clickable");
        item.tabIndex = 0;
        item.addEventListener("click", () => openKbDocument(source.path));
        item.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openKbDocument(source.path);
            }
        });
    }
    return item;
}

function renderSources(sources) {
    sourcesList.replaceChildren();
    sourcesList.classList.remove("empty");
    if (!sources.length) {
        sourcesList.classList.add("empty");
        sourcesList.textContent = "Совпадений в базе знаний не найдено.";
        return;
    }
    for (const source of sources) {
        sourcesList.appendChild(sourceArticle(source, false));
    }
}

function activatePanel(panelId) {
    for (const tab of tabs) {
        tab.classList.toggle("active", tab.dataset.panel === panelId);
    }
    for (const panel of panels) {
        panel.classList.toggle("active", panel.id === panelId);
    }
}

async function searchKbDocuments() {
    if (!kbResults) return;
    const params = new URLSearchParams();
    const q = kbSearchInput?.value.trim();
    if (q) params.set("q", q);
    if (kbDomainFilter?.value) params.set("domain", kbDomainFilter.value);
    if (kbTypeFilter?.value) params.set("doc_type", kbTypeFilter.value);
    if (kbRiskFilter?.value) params.set("risk", kbRiskFilter.value);
    if (kbTagFilter?.value.trim()) params.set("tag", kbTagFilter.value.trim());
    params.set("limit", "50");

    if (kbSearchButton) kbSearchButton.disabled = true;
    kbBrowserStatus.textContent = "Searching KB…";
    try {
        const response = await fetch(`/api/kb/documents?${params.toString()}`);
        if (!response.ok) throw new Error(`KB search failed: ${response.status}`);
        const data = await response.json();
        kbResults.replaceChildren();
        kbResults.classList.remove("empty");
        if (!data.items.length) {
            kbResults.classList.add("empty");
            kbResults.textContent = "Документы не найдены.";
        } else {
            for (const item of data.items) {
                kbResults.appendChild(sourceArticle(item, true));
            }
        }
        kbBrowserStatus.textContent = `Found ${data.total} documents.`;
        activatePanel("browser-panel");
    } catch (error) {
        kbBrowserStatus.textContent = `Не удалось выполнить поиск KB: ${error.message}`;
    } finally {
        if (kbSearchButton) kbSearchButton.disabled = false;
    }
}

async function openKbDocument(path) {
    if (!kbDocumentDetail) return;
    kbBrowserStatus.textContent = "Loading document…";
    try {
        const params = new URLSearchParams({path});
        const response = await fetch(`/api/kb/document?${params.toString()}`);
        if (!response.ok) throw new Error(`Document failed: ${response.status}`);
        const documentData = await response.json();
        kbDocumentTitle.textContent = documentData.title;
        kbDocumentPath.textContent = documentData.path;
        kbDocumentContent.textContent = documentData.content;
        kbDocumentDetail.hidden = false;
        kbBrowserStatus.textContent = "Document opened.";
        activatePanel("browser-panel");
    } catch (error) {
        kbBrowserStatus.textContent = `Не удалось открыть документ: ${error.message}`;
    }
}

for (const tab of tabs) {
    tab.addEventListener("click", () => activatePanel(tab.dataset.panel));
}

newSessionButton?.addEventListener("click", createNewSession);
renameSessionButton?.addEventListener("click", renameCurrentSession);
deleteSessionButton?.addEventListener("click", deleteCurrentSession);
newHostButton?.addEventListener("click", createHostFromPrompt);

kbSearchButton?.addEventListener("click", searchKbDocuments);
for (const searchField of [kbSearchInput, kbTagFilter]) {
    searchField?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            searchKbDocuments();
        }
    });
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
        appendMessage("assistant", data.answer, data.actions || []);
        renderSources(data.sources || []);
        activatePanel("sources-panel");
        const sessionsData = await loadSessions();
        const current = sessionsData.items?.find((item) => item.id === sessionId);
        if (current) setCurrentSession(current.id, current.title);
    } catch (error) {
        appendMessage("error", `Не удалось получить ответ: ${error.message}`);
    } finally {
        button.disabled = false;
        input.focus();
    }
});

loadSessions({openNewest: true}).catch((error) => {
    sessionsList.textContent = `Не удалось загрузить историю: ${error.message}`;
});

loadHosts().catch((error) => {
    if (hostsList) hostsList.textContent = `Не удалось загрузить hosts: ${error.message}`;
});
