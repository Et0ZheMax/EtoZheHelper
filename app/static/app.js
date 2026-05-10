let sessionId = null;
let currentSessionTitle = "";
let selectedHostId = null;
let selectedHostName = "";
let hostsById = new Map();
let sshProfilesById = new Map();

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
const preparedRunsStatus = document.querySelector("#prepared-runs-status");
const newHostButton = document.querySelector("#new-host-button");
const hostsList = document.querySelector("#hosts-list");
const hostsStatus = document.querySelector("#hosts-status");
const newSshProfileButton = document.querySelector("#new-ssh-profile-button");
const sshProfilesList = document.querySelector("#ssh-profiles-list");
const sshProfilesStatus = document.querySelector("#ssh-profiles-status");
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


function getOperatorLabel() {
    return localStorage.getItem("actionRunOperator") || "local-operator";
}

function formatApiErrorDetail(payload, fallback) {
    if (!payload || payload.detail === undefined || payload.detail === null) return fallback;
    if (Array.isArray(payload.detail)) return JSON.stringify(payload.detail);
    if (typeof payload.detail === "object") {
        if (payload.detail.message && payload.detail.execution_id) {
            return `${payload.detail.message} Execution #${payload.detail.execution_id}.`;
        }
        return JSON.stringify(payload.detail);
    }
    return payload.detail;
}

async function postActionRunDecision(runId, decision, body) {
    const response = await fetch(`/api/action-runs/${runId}/${decision}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body),
    });
    if (!response.ok) {
        let details = `${decision} failed: ${response.status}`;
        try {
            const payload = await response.json();
            details = formatApiErrorDetail(payload, details);
        } catch (_) {
            // Keep generic HTTP status when the response is not JSON.
        }
        throw new Error(details);
    }
    return response.json();
}

async function postActionRunExecution(runId, operator) {
    const response = await fetch(`/api/action-runs/${runId}/execute`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({operator}),
    });
    if (!response.ok) {
        let details = `Read-only SSH check failed: ${response.status}`;
        try {
            const payload = await response.json();
            details = formatApiErrorDetail(payload, details);
        } catch (_) {
            // Keep generic HTTP status when the response is not JSON.
        }
        throw new Error(details);
    }
    return response.json();
}

async function fetchActionRunReadiness(runId) {
    const response = await fetch(`/api/action-runs/${runId}/readiness`);
    if (!response.ok) {
        let details = `Readiness check failed: ${response.status}`;
        try {
            const payload = await response.json();
            details = formatApiErrorDetail(payload, details);
        } catch (_) {
            // Keep generic HTTP status when the response is not JSON.
        }
        throw new Error(details);
    }
    return response.json();
}

async function fetchActionRunExecutions(runId) {
    const response = await fetch(`/api/action-runs/${runId}/executions?limit=5&offset=0`);
    if (!response.ok) {
        let details = `Execution list failed: ${response.status}`;
        try {
            const payload = await response.json();
            details = formatApiErrorDetail(payload, details);
        } catch (_) {
            // Keep generic HTTP status when the response is not JSON.
        }
        throw new Error(details);
    }
    return response.json();
}

async function fetchActionExecution(executionId) {
    const response = await fetch(`/api/action-executions/${executionId}`);
    if (!response.ok) {
        let details = `Execution detail failed: ${response.status}`;
        try {
            const payload = await response.json();
            details = formatApiErrorDetail(payload, details);
        } catch (_) {
            // Keep generic HTTP status when the response is not JSON.
        }
        throw new Error(details);
    }
    return response.json();
}

function copyTextToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text);
    }
    return new Promise((resolve, reject) => {
        const area = document.createElement("textarea");
        area.value = text;
        area.setAttribute("readonly", "readonly");
        area.style.position = "fixed";
        area.style.left = "-9999px";
        document.body.append(area);
        area.select();
        try {
            const copied = document.execCommand("copy");
            area.remove();
            copied ? resolve() : reject(new Error("copy failed"));
        } catch (error) {
            area.remove();
            reject(error);
        }
    });
}

function appendExecutionPre(parent, label, text, copyLabel) {
    const title = document.createElement("div");
    title.className = "readiness-label";
    title.textContent = label;

    const copyButton = document.createElement("button");
    copyButton.type = "button";
    copyButton.className = "compact secondary";
    copyButton.textContent = copyLabel;
    copyButton.disabled = !text;
    copyButton.addEventListener("click", async () => {
        try {
            await copyTextToClipboard(text || "");
            copyButton.textContent = "Copied";
            window.setTimeout(() => {
                copyButton.textContent = copyLabel;
            }, 1200);
        } catch (_) {
            copyButton.textContent = "Copy failed";
        }
    });

    const pre = document.createElement("pre");
    pre.textContent = text || "";
    parent.append(title, copyButton, pre);
}


function renderExecutionAnalysis(parent, execution) {
    const status = execution.analysis_status;
    if (!status) {
        return;
    }

    const block = document.createElement("div");
    block.className = "analysis-block";

    const title = document.createElement("div");
    title.className = "readiness-label";
    title.textContent = "Analysis";
    block.append(title);

    const statusLine = document.createElement("div");
    statusLine.className = status === "analyzed" ? "readiness-ready" : "readiness-meta";
    if (status === "skipped_empty_output") {
        statusLine.textContent = "Analysis skipped: empty output.";
        block.append(statusLine);
        parent.append(block);
        return;
    }
    if (status === "skipped_too_large") {
        statusLine.textContent = "Analysis skipped: output too large.";
        block.append(statusLine);
        parent.append(block);
        return;
    }
    if (status === "not_applicable") {
        statusLine.textContent = "No actionable findings detected.";
        block.append(statusLine);
        parent.append(block);
        return;
    }
    if (status === "failed") {
        statusLine.textContent = "Analysis failed safely.";
        block.append(statusLine);
        parent.append(block);
        return;
    }

    statusLine.textContent = `Status: ${status}`;
    block.append(statusLine);
    if (execution.analysis_summary) {
        const summary = document.createElement("div");
        summary.className = "readiness-meta";
        summary.textContent = `Summary: ${execution.analysis_summary}`;
        block.append(summary);
    }

    const analysis = execution.analysis || {};
    const findings = Array.isArray(analysis.findings) ? analysis.findings : [];
    if (findings.length) {
        const findingsTitle = document.createElement("div");
        findingsTitle.className = "readiness-label";
        findingsTitle.textContent = "Findings";
        block.append(findingsTitle);
        for (const finding of findings) {
            const item = document.createElement("div");
            item.className = "analysis-finding";
            const heading = document.createElement("div");
            heading.className = "analysis-finding-title";
            heading.textContent = `[${finding.severity || "info"}] ${finding.title || "Finding"}`;
            item.append(heading);
            if (finding.evidence) {
                const evidence = document.createElement("div");
                evidence.className = "readiness-meta";
                evidence.textContent = `Evidence: ${finding.evidence}`;
                item.append(evidence);
            }
            if (finding.interpretation) {
                const interpretation = document.createElement("div");
                interpretation.className = "readiness-meta";
                interpretation.textContent = `Interpretation: ${finding.interpretation}`;
                item.append(interpretation);
            }
            appendReadinessList(item, "Next steps:", Array.isArray(finding.next_steps) ? finding.next_steps : []);
            block.append(item);
        }
    }

    appendReadinessList(block, "Hypotheses", Array.isArray(analysis.hypotheses) ? analysis.hypotheses : []);
    appendReadinessList(block, "Next checks", Array.isArray(analysis.next_checks) ? analysis.next_checks : []);
    parent.append(block);
}

function renderExecutionResult(parent, execution) {
    parent.replaceChildren();
    const notice = document.createElement("div");
    notice.className = "readiness-ready";
    notice.textContent = "Executed over SSH as read-only approved action.";

    const status = document.createElement("div");
    status.className = execution.status === "completed" ? "readiness-ready" : "readiness-blocked";
    status.textContent = `Status: ${execution.status}`;

    const exitCode = document.createElement("div");
    exitCode.className = "readiness-meta";
    exitCode.textContent = `Exit code: ${execution.exit_code === null || execution.exit_code === undefined ? "none" : execution.exit_code}`;

    const duration = document.createElement("div");
    duration.className = "readiness-meta";
    duration.textContent = `Duration: ${execution.duration_ms === null || execution.duration_ms === undefined ? "unknown" : `${execution.duration_ms} ms`}`;

    parent.append(notice, status, exitCode, duration);
    if (execution.error_category) {
        const category = document.createElement("div");
        category.className = "readiness-meta";
        category.textContent = `Error category: ${execution.error_category}`;
        parent.append(category);
    }
    if (execution.error) {
        const error = document.createElement("div");
        error.className = "readiness-blocked";
        error.textContent = `Error: ${execution.error}`;
        parent.append(error);
    }
    appendExecutionPre(parent, "stdout:", execution.stdout || "", "Copy stdout");
    appendExecutionPre(parent, "stderr:", execution.stderr || "", "Copy stderr");
    appendReadinessList(parent, "warnings:", execution.warnings || []);
    renderExecutionAnalysis(parent, execution);
}

function renderLatestExecutions(parent, runId) {
    parent.replaceChildren();
    const title = document.createElement("div");
    title.className = "readiness-label";
    title.textContent = "Latest executions";
    parent.append(title);

    const list = document.createElement("ul");
    list.className = "readiness-list";
    parent.append(list);

    const detail = document.createElement("div");
    detail.className = "readiness-result";
    parent.append(detail);

    fetchActionRunExecutions(runId)
        .then((payload) => {
            list.replaceChildren();
            const items = payload.items || [];
            if (!items.length) {
                const empty = document.createElement("li");
                empty.textContent = "none";
                list.append(empty);
                return;
            }
            for (const execution of items) {
                const item = document.createElement("li");
                const summary = document.createElement("span");
                const exitText = execution.exit_code === null || execution.exit_code === undefined ? "" : ` exit=${execution.exit_code}`;
                const durationText = execution.duration_ms === null || execution.duration_ms === undefined ? "" : ` ${execution.duration_ms}ms`;
                const analysisText = execution.analysis_summary ? ` analysis=${execution.analysis_status}: ${execution.analysis_summary}` : (execution.analysis_status ? ` analysis=${execution.analysis_status}` : "");
                summary.textContent = `#${execution.id} ${execution.status}${exitText}${durationText}${analysisText}`;

                const viewButton = document.createElement("button");
                viewButton.type = "button";
                viewButton.className = "compact secondary";
                viewButton.textContent = "View";
                viewButton.addEventListener("click", async () => {
                    detail.textContent = "Loading execution detail…";
                    try {
                        const executionDetail = await fetchActionExecution(execution.id);
                        renderExecutionResult(detail, executionDetail);
                    } catch (error) {
                        detail.textContent = `Could not load execution detail: ${error.message}`;
                    }
                });

                item.append(summary, viewButton);
                list.append(item);
            }
        })
        .catch((error) => {
            list.replaceChildren();
            const item = document.createElement("li");
            item.textContent = `Could not load latest executions: ${error.message}`;
            list.append(item);
        });
}

function readinessHelperMessages(blockers) {
    const values = Array.isArray(blockers) ? blockers : [];
    const helpers = [];
    if (values.some((item) => String(item).includes("Host has no SSH profile assigned"))) {
        helpers.push("Assign an SSH profile to this host in the Hosts panel, then prepare/approve/check readiness again.");
    }
    const incompatibleProfileFragments = [
        "Manual auth is not executable",
        "Key auth execution is not implemented",
        "Password auth execution is not implemented",
        "Interactive sudo prompt is not supported",
        "NOPASSWD limited sudo execution is not implemented",
    ];
    if (values.some((item) => incompatibleProfileFragments.some((fragment) => String(item).includes(fragment)))) {
        helpers.push("Stage 14/15 can execute only agent auth with sudo_mode=none. Edit or assign a compatible SSH profile.");
    }
    return helpers;
}

function appendReadinessList(parent, label, items) {
    const title = document.createElement("div");
    title.className = "readiness-label";
    title.textContent = label;
    parent.append(title);

    const list = document.createElement("ul");
    list.className = "readiness-list";
    const values = items && items.length ? items : ["none"];
    for (const item of values) {
        const entry = document.createElement("li");
        entry.textContent = item;
        list.append(entry);
    }
    parent.append(list);
}

function renderReadinessPreview(parent, readiness, runId = null) {
    parent.replaceChildren();

    const ready = document.createElement("div");
    ready.className = readiness.ready ? "readiness-ready" : "readiness-blocked";
    ready.textContent = `Ready for read-only SSH check: ${readiness.ready ? "yes" : "no"}`;

    const execution = document.createElement("div");
    execution.className = readiness.ready ? "readiness-ready" : "execution-disabled";
    execution.textContent = readiness.ready ? "Stage 14 SSH agent execution is available for this approved read-only run." : "Read-only SSH check unavailable until readiness blockers are resolved.";

    const commandLabel = document.createElement("div");
    commandLabel.className = "readiness-label";
    commandLabel.textContent = "command preview:";
    const command = document.createElement("code");
    command.textContent = readiness.command_preview || "";

    const host = document.createElement("div");
    host.className = "readiness-meta";
    host.textContent = `Host: ${readiness.host?.name || "none"}`;

    const sshProfile = document.createElement("div");
    sshProfile.className = "readiness-meta";
    sshProfile.textContent = `SSH profile: ${readiness.ssh_profile?.name || "none"}`;

    parent.append(ready, execution, commandLabel, command, host, sshProfile);
    appendReadinessList(parent, "blockers:", readiness.blockers || []);
    const helpers = readinessHelperMessages(readiness.blockers || []);
    if (helpers.length) {
        appendReadinessList(parent, "how to fix:", helpers);
    }
    appendReadinessList(parent, "warnings:", readiness.warnings || []);

    let latestExecutions = null;
    if (runId) {
        latestExecutions = document.createElement("div");
        latestExecutions.className = "readiness-result";
        renderLatestExecutions(latestExecutions, runId);
    }

    if (readiness.ready && runId) {
        const executionResult = document.createElement("div");
        executionResult.className = "readiness-result";
        executionResult.hidden = true;

        const runButton = document.createElement("button");
        runButton.type = "button";
        runButton.className = "compact";
        runButton.textContent = "Run read-only SSH check";
        runButton.addEventListener("click", async () => {
            const operator = promptActionRunOperator();
            if (!operator) return;
            runButton.disabled = true;
            executionResult.hidden = false;
            executionResult.textContent = "Running read-only SSH check…";
            try {
                const executionPayload = await postActionRunExecution(runId, operator);
                renderExecutionResult(executionResult, executionPayload);
                if (latestExecutions) renderLatestExecutions(latestExecutions, runId);
                if (preparedRunsStatus) {
                    preparedRunsStatus.textContent = `Prepared runs: latest #${runId} read-only SSH check finished with status ${executionPayload.status}.`;
                }
            } catch (error) {
                executionResult.textContent = `Could not run read-only SSH check: ${error.message}`;
            } finally {
                runButton.disabled = false;
            }
        });
        parent.append(runButton, executionResult);
    }
    if (latestExecutions) parent.append(latestExecutions);
}

function promptActionRunOperator() {
    const operator = window.prompt("Operator name", getOperatorLabel());
    if (operator === null) return null;
    const trimmed = operator.trim();
    if (!trimmed) {
        window.alert("Operator name is required.");
        return null;
    }
    localStorage.setItem("actionRunOperator", trimmed);
    return trimmed;
}

function promptActionRunNote(message) {
    const note = window.prompt(message, "");
    if (note === null) return null;
    const trimmed = note.trim();
    return trimmed || null;
}

function appendDecisionNote(parent, note) {
    if (!note) return;
    const noteLine = document.createElement("div");
    noteLine.className = "decision-note";
    noteLine.textContent = `Note: ${note}`;
    parent.append(noteLine);
}

function renderPreparedRunResult(result, run) {
    result.replaceChildren();
    const title = document.createElement("strong");
    title.textContent = `Prepared run #${run.id}`;
    const command = document.createElement("code");
    command.textContent = run.command_preview || "";
    const execution = document.createElement("div");
    execution.className = "execution-disabled";
    execution.textContent = "Approval required before read-only SSH readiness";

    const controls = document.createElement("div");
    controls.className = "approval-controls";

    const approveButton = document.createElement("button");
    approveButton.type = "button";
    approveButton.className = "compact";
    approveButton.textContent = "Approve";

    const rejectButton = document.createElement("button");
    rejectButton.type = "button";
    rejectButton.className = "compact secondary";
    rejectButton.textContent = "Reject";

    approveButton.addEventListener("click", async () => {
        const operator = promptActionRunOperator();
        if (!operator) return;
        const note = promptActionRunNote("Approval note (optional)");
        if (note === null) return;
        approveButton.disabled = true;
        rejectButton.disabled = true;
        try {
            const approved = await postActionRunDecision(run.id, "approve", {operator, note});
            result.replaceChildren();
            const approvedTitle = document.createElement("strong");
            approvedTitle.textContent = `Approved run #${approved.id}`;
            const warning = document.createElement("div");
            warning.className = "execution-disabled";
            warning.textContent = "Approved run can be checked for Stage 14 read-only SSH readiness.";
            const readinessResult = document.createElement("div");
            readinessResult.className = "readiness-result";
            readinessResult.hidden = true;

            const readinessButton = document.createElement("button");
            readinessButton.type = "button";
            readinessButton.className = "compact";
            readinessButton.textContent = "Check readiness";
            readinessButton.addEventListener("click", async () => {
                readinessButton.disabled = true;
                readinessResult.hidden = false;
                readinessResult.textContent = "Checking readiness…";
                try {
                    const readiness = await fetchActionRunReadiness(approved.id);
                    renderReadinessPreview(readinessResult, readiness, approved.id);
                    if (preparedRunsStatus) {
                        preparedRunsStatus.textContent = `Prepared runs: latest #${approved.id} readiness checked.`;
                    }
                } catch (error) {
                    readinessResult.textContent = `Could not check readiness: ${error.message}`;
                } finally {
                    readinessButton.disabled = false;
                }
            });

            result.append(approvedTitle);
            appendDecisionNote(result, approved.approval_note);
            result.append(warning, readinessButton, readinessResult);
            if (preparedRunsStatus) {
                preparedRunsStatus.textContent = `Prepared runs: latest #${approved.id} approved. No command was executed.`;
            }
        } catch (error) {
            result.append(document.createTextNode(` Could not approve run: ${error.message}`));
            approveButton.disabled = false;
            rejectButton.disabled = false;
        }
    });

    rejectButton.addEventListener("click", async () => {
        const operator = promptActionRunOperator();
        if (!operator) return;
        const note = promptActionRunNote("Rejection note (optional)");
        if (note === null) return;
        approveButton.disabled = true;
        rejectButton.disabled = true;
        try {
            const rejected = await postActionRunDecision(run.id, "reject", {operator, note});
            result.replaceChildren();
            const rejectedTitle = document.createElement("strong");
            rejectedTitle.textContent = `Rejected run #${rejected.id}`;
            const warning = document.createElement("div");
            warning.className = "execution-disabled";
            warning.textContent = "No command was executed.";
            result.append(rejectedTitle);
            appendDecisionNote(result, rejected.rejection_note);
            result.append(warning);
            if (preparedRunsStatus) {
                preparedRunsStatus.textContent = `Prepared runs: latest #${rejected.id} rejected. No command was executed.`;
            }
        } catch (error) {
            result.append(document.createTextNode(` Could not reject run: ${error.message}`));
            approveButton.disabled = false;
            rejectButton.disabled = false;
        }
    });

    controls.append(approveButton, rejectButton);
    result.append(title, command, execution, controls);
}

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
        disabled.textContent = "Approval required before read-only SSH readiness";

        const prepareButton = document.createElement("button");
        prepareButton.type = "button";
        prepareButton.className = "compact prepare-run-button";
        prepareButton.textContent = "Prepare run";
        prepareButton.disabled = !selectedHostId;

        const prepareHelper = document.createElement("div");
        prepareHelper.className = "muted small prepare-helper";
        prepareHelper.textContent = selectedHostName
            ? `Prepare an approved read-only ActionRun for ${selectedHostName}. No SSH connection is made during preparation.`
            : "Select a host to prepare an approved read-only ActionRun. No SSH connection is made during preparation.";

        const result = document.createElement("div");
        result.className = "prepared-run-result";
        result.hidden = true;

        prepareButton.addEventListener("click", async () => {
            if (!selectedHostId) return;
            prepareButton.disabled = true;
            prepareButton.textContent = "Preparing…";
            result.hidden = false;
            result.textContent = "Preparing read-only ActionRun preview…";
            try {
                const response = await fetch("/api/action-runs/prepare", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        session_id: sessionId,
                        host_id: selectedHostId,
                        action: action.action,
                        params: action.params || {},
                    }),
                });
                if (!response.ok) {
                    let details = `Prepare failed: ${response.status}`;
                    try {
                        const payload = await response.json();
                        details = formatApiErrorDetail(payload, details);
                    } catch (_) {
                        // Keep generic HTTP status when the response is not JSON.
                    }
                    throw new Error(details);
                }
                const run = await response.json();
                renderPreparedRunResult(result, run);
                if (preparedRunsStatus) {
                    preparedRunsStatus.textContent = `Prepared runs: latest #${run.id} prepared. No command was executed.`;
                }
            } catch (error) {
                result.textContent = `Could not prepare run: ${error.message}`;
                if (preparedRunsStatus) preparedRunsStatus.textContent = `Prepared run failed: ${error.message}`;
            } finally {
                prepareButton.disabled = !selectedHostId;
                prepareButton.textContent = "Prepare run";
            }
        });

        const hostContext = document.createElement("div");
        hostContext.className = "target-host-context";
        hostContext.textContent = selectedHostName ? `Target host context: ${selectedHostName}` : "Target host context: none";

        card.append(heading, label, previewLabel, preview, hostContext);
        card.append(disabled, prepareButton, prepareHelper, result);
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



function updateActionPrepareControls() {
    for (const button of document.querySelectorAll(".prepare-run-button")) {
        button.disabled = !selectedHostId;
    }
    for (const helper of document.querySelectorAll(".prepare-helper")) {
        helper.textContent = selectedHostName
            ? `Prepare an approved read-only ActionRun for ${selectedHostName}. No SSH connection is made during preparation.`
            : "Select a host to prepare an approved read-only ActionRun. No SSH connection is made during preparation.";
    }
    for (const item of document.querySelectorAll(".target-host-context")) {
        item.textContent = selectedHostName ? `Target host context: ${selectedHostName}` : "Target host context: none";
    }
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
    updateActionPrepareControls();
}

async function persistSessionHost(hostId) {
    if (!sessionId) return;
    const response = await fetch(`/api/chat/session/${sessionId}/host`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({host_id: hostId}),
    });
    if (!response.ok) throw new Error(`Persist host failed: ${response.status}`);
}

async function selectHost(host, persist = true) {
    setSelectedHost(host);
    if (!persist || !sessionId) return;
    try {
        await persistSessionHost(host?.id || null);
        if (hostsStatus) hostsStatus.textContent = host
            ? `Selected host context saved: ${host.name}. No SSH connection was performed.`
            : "Selected host context cleared. No SSH connection was performed.";
    } catch (error) {
        if (hostsStatus) hostsStatus.textContent = `Не удалось сохранить host context: ${error.message}`;
    }
}

async function restoreSessionHost(hostId) {
    if (!hostId) {
        setSelectedHost(null);
        return;
    }
    if (!hostsById.has(hostId)) {
        await loadHosts();
    }
    setSelectedHost(hostsById.get(hostId) || null);
}

function profileDisplayName(profileId) {
    if (!profileId) return "none";
    const profile = sshProfilesById.get(profileId);
    return profile ? profile.name : `#${profileId}`;
}

function renderSshProfiles(items) {
    if (!sshProfilesList) return;
    sshProfilesById = new Map((items || []).map((profile) => [profile.id, profile]));
    sshProfilesList.replaceChildren();
    sshProfilesList.classList.remove("empty");
    if (!items.length) {
        sshProfilesList.classList.add("empty");
        sshProfilesList.textContent = "No SSH profiles yet.";
        return;
    }
    for (const profile of items) {
        const card = document.createElement("article");
        card.className = "ssh-profile-item";

        const title = document.createElement("span");
        title.className = "ssh-profile-title";
        title.textContent = profile.name;

        const user = document.createElement("span");
        user.className = "ssh-profile-meta";
        user.textContent = `user: ${profile.username}`;

        const auth = document.createElement("span");
        auth.className = "ssh-profile-meta";
        auth.textContent = `auth: ${profile.auth_type}`;

        const sudo = document.createElement("span");
        sudo.className = "ssh-profile-meta";
        sudo.textContent = `sudo: ${profile.sudo_mode}`;

        const id = document.createElement("span");
        id.className = "ssh-profile-meta";
        id.textContent = `id: ${profile.id}`;

        card.append(title, user, auth, sudo, id);
        sshProfilesList.append(card);
    }
}

async function loadSshProfiles() {
    if (!sshProfilesList) return null;
    const response = await fetch("/api/ssh-profiles?limit=50&offset=0");
    if (!response.ok) throw new Error(`SSH profiles failed: ${response.status}`);
    const data = await response.json();
    renderSshProfiles(data.items || []);
    if (sshProfilesStatus) {
        sshProfilesStatus.textContent = "Agent profiles do not store secrets. The key must be available in the OS ssh-agent for this Windows/Linux user.";
    }
    return data;
}

async function createSshProfileFromPrompt() {
    if (!newSshProfileButton) return;
    const name = prompt("Profile name, e.g. support-agent");
    if (name === null) return;
    const username = prompt("SSH username, e.g. support");
    if (username === null) return;
    newSshProfileButton.disabled = true;
    try {
        const response = await fetch("/api/ssh-profiles", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                name: name.trim(),
                username: username.trim(),
                auth_type: "agent",
                sudo_mode: "none",
            }),
        });
        if (!response.ok) {
            let details = `Create SSH profile failed: ${response.status}`;
            try {
                const payload = await response.json();
                details = formatApiErrorDetail(payload, details);
            } catch (_) {
                // Keep generic status if response is not JSON.
            }
            throw new Error(details);
        }
        const profile = await response.json();
        await loadSshProfiles();
        await loadHosts();
        if (sshProfilesStatus) sshProfilesStatus.textContent = `Agent SSH profile added: ${profile.name}. No secrets were stored.`;
    } catch (error) {
        if (sshProfilesStatus) sshProfilesStatus.textContent = `Не удалось добавить SSH profile: ${error.message}`;
    } finally {
        newSshProfileButton.disabled = false;
    }
}

async function assignSshProfileToHost(hostId, profileId) {
    const response = await fetch(`/api/hosts/${hostId}`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ssh_profile_id: Number(profileId)}),
    });
    if (!response.ok) {
        let details = `Assign SSH profile failed: ${response.status}`;
        try {
            const payload = await response.json();
            details = formatApiErrorDetail(payload, details);
        } catch (_) {
            // Keep generic status if response is not JSON.
        }
        throw new Error(details);
    }
    return response.json();
}

function renderHosts(items) {
    if (!hostsList) return;
    hostsById = new Map((items || []).map((host) => [host.id, host]));
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
        const card = document.createElement("article");
        card.className = "host-item";
        card.dataset.hostId = String(host.id);
        card.classList.toggle("active", host.id === selectedHostId);

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

        const profile = document.createElement("span");
        profile.className = "host-meta";
        profile.textContent = `ssh profile: ${profileDisplayName(host.ssh_profile_id)}`;

        const controls = document.createElement("div");
        controls.className = "host-controls";

        const selectButton = document.createElement("button");
        selectButton.type = "button";
        selectButton.className = "compact";
        selectButton.textContent = host.id === selectedHostId ? "Selected" : "Select host";
        selectButton.addEventListener("click", () => selectHost(host));

        const profileSelect = document.createElement("select");
        profileSelect.setAttribute("aria-label", `SSH profile for ${host.name}`);
        profileSelect.disabled = sshProfilesById.size === 0;

        const emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = sshProfilesById.size ? "Choose SSH profile" : "Create profile first";
        profileSelect.append(emptyOption);
        for (const profileItem of sshProfilesById.values()) {
            const option = document.createElement("option");
            option.value = String(profileItem.id);
            option.textContent = `${profileItem.name} (${profileItem.username}, agent/none)`;
            option.selected = profileItem.id === host.ssh_profile_id;
            profileSelect.append(option);
        }

        const assignButton = document.createElement("button");
        assignButton.type = "button";
        assignButton.className = "compact secondary";
        assignButton.textContent = "Assign SSH profile";
        assignButton.disabled = sshProfilesById.size === 0;
        assignButton.addEventListener("click", async () => {
            if (!sshProfilesById.size) {
                if (hostsStatus) hostsStatus.textContent = "Create an agent SSH profile first.";
                return;
            }
            const value = profileSelect.value;
            if (!value) {
                if (hostsStatus) hostsStatus.textContent = "Choose an SSH profile to assign.";
                return;
            }
            assignButton.disabled = true;
            try {
                const updated = await assignSshProfileToHost(host.id, value);
                await loadHosts();
                if (selectedHostId === updated.id) setSelectedHost(updated);
                if (hostsStatus) hostsStatus.textContent = "SSH profile assigned to host. No SSH connection was performed.";
            } catch (error) {
                if (hostsStatus) hostsStatus.textContent = `Не удалось назначить SSH profile: ${error.message}`;
            } finally {
                assignButton.disabled = false;
            }
        });

        controls.append(selectButton, profileSelect, assignButton);
        card.append(title, endpoint, tags, status, profile, controls);
        hostsList.appendChild(card);
    }
}

async function loadHosts() {
    if (!hostsList) return null;
    if (sshProfilesList && sshProfilesById.size === 0) {
        await loadSshProfiles();
    }
    const response = await fetch("/api/hosts?limit=50&offset=0");
    if (!response.ok) throw new Error(`Hosts failed: ${response.status}`);
    const data = await response.json();
    renderHosts(data.items || []);
    if (hostsStatus) hostsStatus.textContent = "Inventory only. SSH runs only from approved read-only ActionRuns.";
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
                details = formatApiErrorDetail(payload, details);
            } catch (_) {
                // Keep generic status if response is not JSON.
            }
            throw new Error(details);
        }
        const host = await response.json();
        await loadHosts();
        await selectHost(host);
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
        if (selectedHostId) await persistSessionHost(selectedHostId);
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
    await restoreSessionHost(data.host_id);
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
newSshProfileButton?.addEventListener("click", createSshProfileFromPrompt);

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

    const hadSession = Boolean(sessionId);
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
        if (!hadSession && selectedHostId) await persistSessionHost(selectedHostId);
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

loadSshProfiles().then(() => loadHosts()).catch((error) => {
    if (sshProfilesList) sshProfilesList.textContent = `Не удалось загрузить SSH profiles: ${error.message}`;
    if (hostsList) hostsList.textContent = `Не удалось загрузить hosts: ${error.message}`;
});
