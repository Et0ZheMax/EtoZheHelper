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
        item.tabIndex = 0;
        item.classList.add("clickable");
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
        appendMessage("assistant", data.answer);
        renderSources(data.sources || []);
        activatePanel("sources-panel");
    } catch (error) {
        appendMessage("error", `Не удалось получить ответ: ${error.message}`);
    } finally {
        button.disabled = false;
        input.focus();
    }
});
