const SUMMARY_URL = "/output/batch_generation/batch_summary.json";
const VALID_ITEM_STATUSES = new Set(["success", "failed", "partial"]);
const VALID_STYLE_STATUSES = new Set(["success", "failed"]);

document.addEventListener("DOMContentLoaded", () => {
    loadSummary();
});

async function loadSummary() {
    try {
        const response = await fetch(SUMMARY_URL, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} while loading batch_summary.json`);
        }

        const summary = await response.json();
        validateSummary(summary);
        renderViewer(summary);
    } catch (error) {
        renderError(buildLoadErrorMessage(error));
    }
}

function validateSummary(summary) {
    if (!summary || typeof summary !== "object" || Array.isArray(summary)) {
        throw new Error("batch_summary.json must be a JSON object");
    }

    const requiredTopLevel = [
        "mode",
        "total_inputs",
        "total_styles",
        "total_jobs",
        "success_count",
        "failed_count",
        "generated_at",
        "items",
    ];

    for (const fieldName of requiredTopLevel) {
        if (!(fieldName in summary)) {
            throw new Error(`Missing top-level field: ${fieldName}`);
        }
    }

    if (!Array.isArray(summary.items)) {
        throw new Error("Field 'items' must be an array");
    }

    for (const item of summary.items) {
        const requiredItemFields = ["item_id", "input_index", "input_text", "status", "styles"];
        for (const fieldName of requiredItemFields) {
            if (!(fieldName in item)) {
                throw new Error(`Item missing field: ${fieldName}`);
            }
        }

        if (!VALID_ITEM_STATUSES.has(item.status)) {
            throw new Error(`Invalid item status: ${item.status}`);
        }

        if (!Array.isArray(item.styles)) {
            throw new Error(`Item ${item.item_id} has non-array styles`);
        }

        for (const styleResult of item.styles) {
            const requiredStyleFields = ["style", "status", "preview_path", "meta_path", "error"];
            for (const fieldName of requiredStyleFields) {
                if (!(fieldName in styleResult)) {
                    throw new Error(`Style result missing field: ${fieldName}`);
                }
            }

            if (!VALID_STYLE_STATUSES.has(styleResult.status)) {
                throw new Error(`Invalid style status: ${styleResult.status}`);
            }
        }
    }
}

function renderViewer(summary) {
    const app = document.getElementById("app");
    app.replaceChildren(renderOverview(summary), renderItems(summary.items));
}

function renderOverview(summary) {
    const section = document.createElement("section");
    section.className = "panel";

    const title = document.createElement("h2");
    title.textContent = "Overview";

    const subtitle = document.createElement("p");
    subtitle.className = "item-subtitle";
    subtitle.textContent = "Summary-level status from the frozen output contract.";

    const grid = document.createElement("dl");
    grid.className = "overview-grid";

    const metrics = [
        ["Mode", summary.mode],
        ["Inputs", summary.total_inputs],
        ["Styles", summary.total_styles],
        ["Jobs", summary.total_jobs],
        ["Success", summary.success_count],
        ["Failed", summary.failed_count],
        ["Generated At", summary.generated_at],
    ];

    for (const [label, value] of metrics) {
        const card = document.createElement("div");
        card.className = "metric-card";

        const dt = document.createElement("dt");
        dt.textContent = label;

        const dd = document.createElement("dd");
        dd.textContent = String(value);

        card.append(dt, dd);
        grid.append(card);
    }

    section.append(title, subtitle, grid);
    return section;
}

function renderItems(items) {
    const wrapper = document.createElement("section");
    wrapper.className = "app-shell";

    for (const item of items) {
        const article = document.createElement("article");
        article.className = "item-panel";

        const header = document.createElement("div");
        header.className = "item-header";

        const headingGroup = document.createElement("div");
        const itemId = document.createElement("p");
        itemId.className = "item-id";
        itemId.textContent = `${item.item_id} · Input ${item.input_index}`;

        const itemSubtitle = document.createElement("p");
        itemSubtitle.className = "item-subtitle";
        itemSubtitle.textContent = `Item status: ${item.status}`;

        const inputText = document.createElement("p");
        inputText.className = "input-text";
        inputText.textContent = item.input_text;

        headingGroup.append(itemId, itemSubtitle, inputText);

        const itemStatus = document.createElement("span");
        itemStatus.className = `status-pill status-${item.status}`;
        itemStatus.textContent = item.status;

        header.append(headingGroup, itemStatus);

        const stylesGrid = document.createElement("div");
        stylesGrid.className = "styles-grid";
        for (const styleResult of item.styles) {
            stylesGrid.append(renderStyleCard(styleResult));
        }

        article.append(header, stylesGrid);
        wrapper.append(article);
    }

    return wrapper;
}

function renderStyleCard(styleResult) {
    const template = document.getElementById("style-card-template");
    const fragment = template.content.cloneNode(true);
    const card = fragment.querySelector(".style-card");
    const statusClassName = `status-${styleResult.status}`;

    fragment.querySelector(".style-name").textContent = styleResult.style;
    fragment.querySelector(".style-meta").textContent = `Status: ${styleResult.status}`;

    const statusPill = fragment.querySelector(".status-pill");
    statusPill.textContent = styleResult.status;
    statusPill.classList.add(statusClassName);

    if (styleResult.status === "failed") {
        card.classList.add("failed");
    }

    const previewPath = toViewerPath(styleResult.preview_path);
    const metaPath = toViewerPath(styleResult.meta_path);

    fragment.querySelector(".preview-path").textContent = styleResult.preview_path;
    fragment.querySelector(".meta-path").textContent = styleResult.meta_path;

    setupPreview(fragment, previewPath);
    populateError(fragment, styleResult.error);
    loadMetaSummary(fragment, metaPath);

    return fragment;
}

function setupPreview(fragment, previewPath) {
    const image = fragment.querySelector(".preview-image");
    const fallback = fragment.querySelector(".preview-fallback");

    image.src = previewPath;
    image.addEventListener("error", () => {
        image.hidden = true;
        fallback.hidden = false;
    });

    image.addEventListener("load", () => {
        image.hidden = false;
        fallback.hidden = true;
    });
}

function populateError(fragment, errorValue) {
    if (!errorValue) {
        return;
    }

    const errorBlock = fragment.querySelector(".error-block");
    errorBlock.hidden = false;
    fragment.querySelector(".error-text").textContent = String(errorValue);
}

async function loadMetaSummary(fragment, metaPath) {
    const metaSummary = fragment.querySelector(".meta-summary");

    try {
        const response = await fetch(metaPath, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const meta = await response.json();
        const lines = [];
        if (meta.title) {
            lines.push(`Title: ${meta.title}`);
        }
        if (meta.highlight) {
            lines.push(`Highlight: ${meta.highlight}`);
        }
        if (typeof meta.used_ai_generation === "boolean") {
            lines.push(`AI: ${meta.used_ai_generation ? "enabled" : "disabled"}`);
        }

        metaSummary.textContent = lines.length > 0 ? lines.join(" | ") : "Meta loaded";
    } catch (error) {
        metaSummary.textContent = `Meta unavailable: ${error.message}`;
    }
}

function renderError(message) {
    const app = document.getElementById("app");
    const panel = document.createElement("section");
    panel.className = "panel error-panel";

    const title = document.createElement("h2");
    title.textContent = "Failed to load batch_summary.json";

    const body = document.createElement("p");
    body.textContent = message;

    const hint = document.createElement("p");
    hint.className = "item-subtitle";
    hint.textContent = "Run a simple static server from the project root, for example: python -m http.server 8000";

    panel.append(title, body, hint);
    app.replaceChildren(panel);
}

function buildLoadErrorMessage(error) {
    if (window.location.protocol === "file:") {
        return "This viewer should be opened through a simple static server, not directly from the file protocol.";
    }

    if (error instanceof Error) {
        return error.message;
    }

    return "Unknown error while loading summary.";
}

function toViewerPath(rawPath) {
    const normalized = String(rawPath).replace(/\\/g, "/");
    return normalized.startsWith("/") ? normalized : `/${normalized}`;
}