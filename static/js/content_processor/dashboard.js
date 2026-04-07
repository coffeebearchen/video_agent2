const form = document.getElementById("content-processor-form");
const generateButton = document.getElementById("generate-button");
const generateABButton = document.getElementById("generate-ab-button");
const formStatus = document.getElementById("form-status");
const confirmStatusText = document.getElementById("confirm-status-text");
const autoContinueInput = document.getElementById("auto_continue");
const referenceImagesInput = document.getElementById("reference_images");
const referenceVideosInput = document.getElementById("reference_videos");
const confirmButton = document.querySelector('[data-placeholder-action="confirm"]');
const regenerateButton = document.querySelector('[data-placeholder-action="regenerate"]');
const manualEditButton = document.querySelector('[data-placeholder-action="manual-edit"]');
const manualEditDetails = document.getElementById("manual-edit-details");

const resultNodes = {
    styleBadge: document.getElementById("result-style-badge"),
    confirmBadge: document.getElementById("result-confirm-status"),
    title: document.getElementById("result-title"),
    script: document.getElementById("result-script"),
    highlights: document.getElementById("result-highlights"),
    keywords: document.getElementById("result-keywords"),
    metaContentMode: document.getElementById("meta-content-mode"),
    metaStyleMode: document.getElementById("meta-style-mode"),
    metaScriptLength: document.getElementById("meta-script-length"),
    metaConfirmStatus: document.getElementById("meta-confirm-status"),
    metaAutoFlow: document.getElementById("meta-auto-flow"),
    sourceSummary: document.getElementById("result-source-summary"),
};

const abNodes = {
    status: document.getElementById("ab-status-text"),
    grid: document.getElementById("ab-compare-grid"),
};

const mediaNodes = {
    imageList: document.getElementById("image-upload-list"),
    videoList: document.getElementById("video-upload-list"),
};

const editorNodes = {
    title: document.getElementById("editor-title-input"),
    scriptList: document.getElementById("script-editor-list"),
    highlightList: document.getElementById("highlight-editor-list"),
    keywordList: document.getElementById("keyword-editor-list"),
    keywordInput: document.getElementById("keyword-add-input"),
    keywordAddButton: document.getElementById("keyword-add-button"),
    applyButton: document.getElementById("apply-edit-button"),
    status: document.getElementById("editor-status"),
    versionIndicator: document.getElementById("editor-version-indicator"),
};

const pageState = {
    currentContentPackage: null,
    lastSubmittedFormSnapshot: null,
    isGenerating: false,
    hasGenerated: false,
    isConfirmed: false,
};

const abState = {
    versionA: null,
    versionB: null,
    isGeneratingAB: false,
    selectedVersion: null,
};

const editorState = {
    title: "",
    scriptItems: [],
    highlightItems: [],
    keywordItems: [],
};

const mediaState = {
    images: [],
    videos: [],
};

let editorItemCounter = 0;
let imageAssetCounter = 0;
let videoAssetCounter = 0;

function createEditorItem(prefix, text = "") {
    editorItemCounter += 1;
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return {
            id: `${prefix}-${crypto.randomUUID()}`,
            text,
            locked: false,
        };
    }

    return {
        id: `${prefix}-${Date.now()}-${editorItemCounter}`,
        text,
        locked: false,
    };
}

function applySelectedVersionTheme() {
    const body = document.body;
    body.classList.remove("theme-version-a", "theme-version-b");

    if (abState.selectedVersion === "A") {
        body.classList.add("theme-version-a");
    } else if (abState.selectedVersion === "B") {
        body.classList.add("theme-version-b");
    }
}

function updateEditorVersionIndicator() {
    if (!editorNodes.versionIndicator) {
        return;
    }

    if (abState.selectedVersion === "A") {
        editorNodes.versionIndicator.textContent = "Editing Version A";
        return;
    }

    if (abState.selectedVersion === "B") {
        editorNodes.versionIndicator.textContent = "Editing Version B";
        return;
    }

    if (pageState.hasGenerated) {
        editorNodes.versionIndicator.textContent = "Editing Current Draft";
        return;
    }

    editorNodes.versionIndicator.textContent = "No version selected";
}

function clearSelectedVersionContext() {
    abState.selectedVersion = null;
    applySelectedVersionTheme();
    updateEditorVersionIndicator();
}

function createAssetId(assetType) {
    if (assetType === "image") {
        imageAssetCounter += 1;
        return `img_${String(imageAssetCounter).padStart(3, "0")}`;
    }

    videoAssetCounter += 1;
    return `vid_${String(videoAssetCounter).padStart(3, "0")}`;
}

function createMediaItem(file, assetType) {
    return {
        assetId: createAssetId(assetType),
        file,
        fileName: file?.name || "unnamed",
        assetType,
        uploadProgress: 0,
        uploadStatus: "pending",
    };
}

function renderUploadList(container, items, theme) {
    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (!items.length) {
        const empty = document.createElement("div");
        empty.className = `upload-empty upload-empty-${theme}`;
        empty.textContent = theme === "image" ? "暂无图片素材" : "暂无视频素材";
        container.appendChild(empty);
        return;
    }

    items.forEach((item) => {
        const wrapper = document.createElement("div");
        wrapper.className = `upload-item upload-item-${theme}`;

        const header = document.createElement("div");
        header.className = "upload-item-header";

        const fileName = document.createElement("span");
        fileName.className = "upload-file-name";
        fileName.textContent = item.fileName;

        const assetId = document.createElement("span");
        assetId.className = "upload-asset-id";
        assetId.textContent = item.assetId;

        header.appendChild(fileName);
        header.appendChild(assetId);

        const track = document.createElement("div");
        track.className = "upload-progress-track";

        const fill = document.createElement("div");
        fill.className = `upload-progress-fill upload-progress-fill-${theme}`;
        fill.style.width = `${item.uploadProgress}%`;
        track.appendChild(fill);

        const status = document.createElement("div");
        status.className = "upload-status-text";
        status.textContent = `${item.uploadStatus} · ${item.uploadProgress}%`;

        wrapper.appendChild(header);
        wrapper.appendChild(track);
        wrapper.appendChild(status);
        container.appendChild(wrapper);
    });
}

function renderImageUploadList() {
    renderUploadList(mediaNodes.imageList, mediaState.images, "image");
}

function renderVideoUploadList() {
    renderUploadList(mediaNodes.videoList, mediaState.videos, "video");
}

function simulateUploadProgress(item, onUpdate) {
    item.uploadStatus = "preparing";
    item.uploadProgress = 0;
    onUpdate();

    const checkpoints = [20, 45, 72, 100];
    checkpoints.forEach((value, index) => {
        window.setTimeout(() => {
            item.uploadProgress = value;
            item.uploadStatus = value >= 100 ? "ready" : "preparing";
            onUpdate();
        }, 120 * (index + 1));
    });
}

function buildMediaMetadata(items) {
    return items.map((item) => ({
        asset_id: item.assetId,
        file_name: item.fileName,
        asset_type: item.assetType,
        upload_status: item.uploadStatus,
    }));
}

function handleReferenceFilesChange(assetType) {
    const input = assetType === "image" ? referenceImagesInput : referenceVideosInput;
    const files = Array.from(input?.files || []);
    const items = files.map((file) => createMediaItem(file, assetType));

    if (assetType === "image") {
        mediaState.images = items;
        renderImageUploadList();
        mediaState.images.forEach((item) => simulateUploadProgress(item, renderImageUploadList));
        return;
    }

    mediaState.videos = items;
    renderVideoUploadList();
    mediaState.videos.forEach((item) => simulateUploadProgress(item, renderVideoUploadList));
}

function normalizeFixedEditorItems(textList, prefix, targetCount = 3) {
    const sourceList = Array.isArray(textList) ? textList.slice(0, targetCount) : [];
    const items = sourceList.map((text) => createEditorItem(prefix, text || ""));

    while (items.length < targetCount) {
        items.push(createEditorItem(prefix, ""));
    }

    return items;
}

function renderList(container, items, ordered = false) {
    container.innerHTML = "";
    const normalized = Array.isArray(items) && items.length > 0 ? items : ["暂无内容"];

    normalized.forEach((item) => {
        const li = document.createElement("li");
        li.textContent = item;
        container.appendChild(li);
    });

    if (!ordered) {
        container.classList.remove("content-list");
        container.classList.add("token-list");
    }
}

function renderKeywords(items) {
    resultNodes.keywords.innerHTML = "";
    const normalized = Array.isArray(items) && items.length > 0 ? items : ["暂无关键词"];

    normalized.forEach((item) => {
        const pill = document.createElement("span");
        pill.className = "keyword-pill";
        pill.textContent = item;
        resultNodes.keywords.appendChild(pill);
    });
}

function createKeywordPill(item, className = "keyword-pill") {
    const pill = document.createElement("span");
    pill.className = className;
    pill.textContent = item;
    return pill;
}

function normalizeCompareText(value) {
    return String(value || "").trim();
}

function isDifferentText(valueA, valueB) {
    return normalizeCompareText(valueA) !== normalizeCompareText(valueB);
}

function buildFixedCompareList(items, targetCount = 3) {
    const normalizedItems = Array.isArray(items) ? items.slice(0, targetCount) : [];
    const results = normalizedItems.map((item) => normalizeCompareText(item));

    while (results.length < targetCount) {
        results.push("");
    }

    return results;
}

function buildABDiffState(versionA, versionB) {
    if (!versionA || !versionB) {
        return null;
    }

    const scriptA = buildFixedCompareList(versionA.script, 3);
    const scriptB = buildFixedCompareList(versionB.script, 3);
    const highlightsA = buildFixedCompareList(versionA.highlights, 3);
    const highlightsB = buildFixedCompareList(versionB.highlights, 3);

    return {
        titleDifferent: isDifferentText(versionA.title, versionB.title),
        scriptDiffs: scriptA.map((item, index) => isDifferentText(item, scriptB[index])),
        highlightDiffs: highlightsA.map((item, index) => isDifferentText(item, highlightsB[index])),
        keywordsDifferent: isDifferentText(
            (versionA.keywords || []).map((item) => normalizeCompareText(item)).join("||"),
            (versionB.keywords || []).map((item) => normalizeCompareText(item)).join("||"),
        ),
    };
}

function appendDifferenceBadge(container, label = "Changed") {
    container.appendChild(createKeywordPill(label, "keyword-pill muted-pill"));
}

function renderInputSources(inputSources) {
    resultNodes.sourceSummary.innerHTML = "";

    const groups = [];
    if (inputSources?.has_reference_images && inputSources.image_group) {
        groups.push(`images · ${inputSources.image_group.role_hint} · ${inputSources.image_group.assets.length}`);
    }
    if (inputSources?.has_reference_videos && inputSources.video_group) {
        groups.push(`videos · ${inputSources.video_group.role_hint} · ${inputSources.video_group.assets.length}`);
    }

    const policy = document.createElement("span");
    policy.className = "keyword-pill";
    policy.textContent = inputSources?.priority_policy || "user_uploaded_media_first";
    resultNodes.sourceSummary.appendChild(policy);

    if (groups.length === 0) {
        const empty = document.createElement("span");
        empty.className = "keyword-pill muted-pill";
        empty.textContent = "no reference media";
        resultNodes.sourceSummary.appendChild(empty);
        return;
    }

    groups.forEach((item) => {
        const pill = document.createElement("span");
        pill.className = "keyword-pill";
        pill.textContent = item;
        resultNodes.sourceSummary.appendChild(pill);
    });
}

function collectFormSnapshot() {
    return {
        raw_text: document.getElementById("raw_text").value || "",
        content_mode: document.getElementById("content_mode").value || "finance",
        style_mode: document.getElementById("style_mode").value || "knowledge",
        script_length_target: document.getElementById("script_length_target").value || "100",
        feedback_text: document.getElementById("feedback_text").value || "",
        auto_flow: autoContinueInput.checked,
        reference_images_note: document.getElementById("reference_images_note").value || "",
        reference_images_role_hint: document.getElementById("reference_images_role_hint").value || "hook",
        reference_videos_note: document.getElementById("reference_videos_note").value || "",
        reference_videos_role_hint: document.getElementById("reference_videos_role_hint").value || "primary",
        reference_images_count: mediaState.images.length,
        reference_videos_count: mediaState.videos.length,
    };
}

function syncActionState() {
    generateButton.disabled = pageState.isGenerating;
    generateButton.textContent = pageState.isGenerating ? "Generating..." : "Generate Content Package";

    if (generateABButton) {
        generateABButton.disabled = pageState.isGenerating || abState.isGeneratingAB;
        generateABButton.textContent = abState.isGeneratingAB ? "Generating A/B..." : "Generate A/B Versions";
    }

    const canConfirm = pageState.hasGenerated && !pageState.isGenerating && !pageState.isConfirmed;
    const canRegenerate = pageState.hasGenerated && !pageState.isGenerating;
    const canEdit = pageState.hasGenerated && !pageState.isGenerating;

    if (confirmButton) {
        confirmButton.disabled = !canConfirm;
        confirmButton.textContent = pageState.isConfirmed ? "Confirmed" : "Confirm";
    }

    if (regenerateButton) {
        regenerateButton.disabled = !canRegenerate;
        regenerateButton.textContent = pageState.isGenerating && pageState.hasGenerated ? "Regenerating..." : "Regenerate";
    }

    if (manualEditButton) {
        manualEditButton.disabled = !canEdit;
    }

    if (editorNodes.applyButton) {
        editorNodes.applyButton.disabled = !canEdit;
    }

    if (editorNodes.keywordAddButton) {
        editorNodes.keywordAddButton.disabled = !canEdit;
    }

    if (editorNodes.keywordInput) {
        editorNodes.keywordInput.disabled = !canEdit;
    }

    if (editorNodes.title) {
        editorNodes.title.disabled = !canEdit;
    }
}

function setCurrentContentPackage(contentPackage, formSnapshot) {
    pageState.currentContentPackage = contentPackage;
    pageState.lastSubmittedFormSnapshot = formSnapshot;
    pageState.hasGenerated = true;
    pageState.isConfirmed = contentPackage?.meta?.confirm_status === "confirmed";
    renderContentPackage(contentPackage);
    populateEditorFromPackage(contentPackage);
    syncActionState();
    updateEditorVersionIndicator();
}

function normalizeGeneratedPayload(payload) {
    const contentPackage = {
        ...payload,
        meta: {
            ...(payload.meta || {}),
            confirm_status: "draft",
        },
        input_sources: {
            ...(payload.input_sources || {}),
        },
    };
    contentPackage.meta.auto_flow = Boolean(contentPackage.meta.auto_flow);
    return contentPackage;
}

function renderContentPackage(contentPackage) {
    resultNodes.styleBadge.textContent = `${contentPackage.content_mode} · ${contentPackage.style_mode}`;
    resultNodes.confirmBadge.textContent = `confirm_status: ${contentPackage.meta.confirm_status}`;
    resultNodes.title.textContent = contentPackage.title;

    renderList(resultNodes.script, contentPackage.script, true);
    renderList(resultNodes.highlights, contentPackage.highlights, false);
    renderKeywords(contentPackage.keywords);

    resultNodes.metaContentMode.textContent = contentPackage.content_mode;
    resultNodes.metaStyleMode.textContent = contentPackage.style_mode;
    resultNodes.metaScriptLength.textContent = String(contentPackage.meta.script_length_target);
    resultNodes.metaConfirmStatus.textContent = contentPackage.meta.confirm_status;
    resultNodes.metaAutoFlow.textContent = String(contentPackage.meta.auto_flow);
    renderInputSources(contentPackage.input_sources || {});
}

function setGeneratingState(isGenerating) {
    pageState.isGenerating = isGenerating;
    syncActionState();
}

function setABGeneratingState(isGeneratingAB) {
    abState.isGeneratingAB = isGeneratingAB;
    syncActionState();
}

function buildGenerateFormData() {
    const formData = new FormData(form);
    formData.set("auto_flow", autoContinueInput.checked ? "true" : "false");
    formData.set("image_assets_meta", JSON.stringify({
        group_note: document.getElementById("reference_images_note").value || "",
        role_hint: document.getElementById("reference_images_role_hint").value || "hook",
        assets: buildMediaMetadata(mediaState.images),
    }));
    formData.set("video_assets_meta", JSON.stringify({
        group_note: document.getElementById("reference_videos_note").value || "",
        role_hint: document.getElementById("reference_videos_role_hint").value || "primary",
        assets: buildMediaMetadata(mediaState.videos),
    }));
    return formData;
}

async function fetchGeneratedPackage() {
    const response = await fetch("/content-processor/generate", {
        method: "POST",
        body: buildGenerateFormData(),
    });

    const payload = await response.json();
    if (!response.ok) {
        throw new Error(payload.message || "内容生成失败，请稍后重试。");
    }

    return normalizeGeneratedPayload(payload);
}

function renderScriptEditor() {
    editorNodes.scriptList.innerHTML = "";

    editorState.scriptItems.forEach((item, index) => {
        const wrapper = document.createElement("div");
        wrapper.className = "field-block full-width";

        const label = document.createElement("label");
        label.setAttribute("for", `script-item-${item.id}`);
        label.textContent = `${index + 1}. Script Item`;

        const textarea = document.createElement("textarea");
        textarea.id = `script-item-${item.id}`;
        textarea.rows = 3;
        textarea.value = item.text || "";
        textarea.disabled = item.locked || !pageState.hasGenerated || pageState.isGenerating;
        textarea.addEventListener("input", (event) => {
            item.text = event.target.value;
        });

        wrapper.appendChild(label);
        wrapper.appendChild(textarea);
        editorNodes.scriptList.appendChild(wrapper);
    });
}

function renderHighlightEditor() {
    editorNodes.highlightList.innerHTML = "";

    editorState.highlightItems.forEach((item, index) => {
        const wrapper = document.createElement("div");
        wrapper.className = "field-block full-width";

        const label = document.createElement("label");
        label.setAttribute("for", `highlight-item-${item.id}`);
        label.textContent = `${index + 1}. Highlight Item`;

        const input = document.createElement("input");
        input.id = `highlight-item-${item.id}`;
        input.type = "text";
        input.value = item.text || "";
        input.disabled = item.locked || !pageState.hasGenerated || pageState.isGenerating;
        input.addEventListener("input", (event) => {
            item.text = event.target.value;
        });

        wrapper.appendChild(label);
        wrapper.appendChild(input);
        editorNodes.highlightList.appendChild(wrapper);
    });
}

function removeKeyword(id) {
    editorState.keywordItems = editorState.keywordItems.filter((item) => item.id !== id);
    renderEditor();
}

function renderKeywordEditor() {
    editorNodes.keywordList.innerHTML = "";

    if (editorState.keywordItems.length === 0) {
        const empty = document.createElement("span");
        empty.className = "keyword-pill muted-pill";
        empty.textContent = "暂无 keyword";
        editorNodes.keywordList.appendChild(empty);
        return;
    }

    editorState.keywordItems.forEach((item) => {
        const wrapper = document.createElement("span");
        wrapper.className = "keyword-pill";

        const textInput = document.createElement("input");
        textInput.type = "text";
        textInput.value = item.text || "";
        textInput.disabled = item.locked || !pageState.hasGenerated || pageState.isGenerating;
        textInput.addEventListener("input", (event) => {
            item.text = event.target.value;
        });

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.textContent = "x";
        removeButton.disabled = item.locked || !pageState.hasGenerated || pageState.isGenerating;
        removeButton.addEventListener("click", () => removeKeyword(item.id));

        wrapper.appendChild(textInput);
        wrapper.appendChild(removeButton);
        editorNodes.keywordList.appendChild(wrapper);
    });
}

function renderEditor() {
    editorNodes.title.value = editorState.title || "";
    renderScriptEditor();
    renderHighlightEditor();
    renderKeywordEditor();
}

function populateEditorFromPackage(pkg) {
    editorState.title = pkg.title || "";
    editorState.scriptItems = normalizeFixedEditorItems(pkg.script, "s", 3);
    editorState.highlightItems = normalizeFixedEditorItems(pkg.highlights, "h", 3);
    editorState.keywordItems = (pkg.keywords || []).map((text) => createEditorItem("k", text));
    renderEditor();
    editorNodes.status.textContent = "已从当前 content package 载入 Structured Editor。";
}

function buildABVersionCard(versionKey, contentPackage, diffState) {
    const card = document.createElement("section");
    card.className = `result-block ab-version-card version-${versionKey.toLowerCase()}-card`;
    if (abState.selectedVersion === versionKey) {
        card.classList.add("is-selected");
    }

    const sectionLabel = document.createElement("p");
    sectionLabel.className = "section-label";
    sectionLabel.textContent = `Version ${versionKey}`;

    const badgeRow = document.createElement("div");
    badgeRow.className = "result-summary";

    const styleBadge = document.createElement("span");
    styleBadge.className = "result-badge";
    styleBadge.textContent = `${contentPackage.content_mode} · ${contentPackage.style_mode}`;

    const selectedBadge = document.createElement("span");
    selectedBadge.className = "result-meta-inline";
    selectedBadge.textContent = abState.selectedVersion === versionKey ? `selected: ${versionKey}` : "candidate";

    badgeRow.appendChild(styleBadge);
    badgeRow.appendChild(selectedBadge);

    const title = document.createElement("h3");
    title.className = "result-title";
    title.textContent = contentPackage.title || "-";

    if (diffState?.titleDifferent) {
        appendDifferenceBadge(badgeRow, "Different");
    }

    const scriptLabel = document.createElement("p");
    scriptLabel.className = "section-label";
    scriptLabel.textContent = "Script";

    const scriptList = document.createElement("ol");
    scriptList.className = "content-list";
    buildFixedCompareList(contentPackage.script, 3).forEach((item, index) => {
        const li = document.createElement("li");
        li.textContent = item || "-";
        if (diffState?.scriptDiffs?.[index]) {
            li.appendChild(document.createTextNode(" "));
            li.appendChild(createKeywordPill("Changed", "keyword-pill muted-pill"));
        }
        scriptList.appendChild(li);
    });

    const highlightLabel = document.createElement("p");
    highlightLabel.className = "section-label";
    highlightLabel.textContent = "Highlights";

    const highlightList = document.createElement("ul");
    highlightList.className = "token-list";
    buildFixedCompareList(contentPackage.highlights, 3).forEach((item, index) => {
        const li = document.createElement("li");
        li.textContent = item || "-";
        if (diffState?.highlightDiffs?.[index]) {
            li.appendChild(document.createTextNode(" "));
            li.appendChild(createKeywordPill("Changed", "keyword-pill muted-pill"));
        }
        highlightList.appendChild(li);
    });

    const keywordLabel = document.createElement("p");
    keywordLabel.className = "section-label";
    keywordLabel.textContent = diffState?.keywordsDifferent ? "Keywords · Different" : "Keywords";

    const keywordWrap = document.createElement("div");
    keywordWrap.className = "keyword-wrap";
    (contentPackage.keywords || []).forEach((item) => {
        keywordWrap.appendChild(createKeywordPill(item));
    });

    const useButton = document.createElement("button");
    useButton.type = "button";
    useButton.className = `primary-button version-${versionKey.toLowerCase()}-button`;
    if (abState.selectedVersion === versionKey) {
        useButton.classList.add("is-selected");
    }
    useButton.textContent = `Use Version ${versionKey}`;
    useButton.disabled = pageState.isGenerating || abState.isGeneratingAB;
    useButton.addEventListener("click", () => useABVersion(versionKey));

    card.appendChild(sectionLabel);
    card.appendChild(badgeRow);
    card.appendChild(title);
    card.appendChild(scriptLabel);
    card.appendChild(scriptList);
    card.appendChild(highlightLabel);
    card.appendChild(highlightList);
    card.appendChild(keywordLabel);
    card.appendChild(keywordWrap);
    card.appendChild(useButton);

    return card;
}

function renderABComparePanel() {
    if (!abNodes.grid || !abNodes.status) {
        return;
    }

    abNodes.grid.innerHTML = "";

    if (!abState.versionA && !abState.versionB) {
        const emptyA = document.createElement("section");
        emptyA.className = "result-block";
        emptyA.innerHTML = '<p class="section-label">Version A</p><p class="inline-note">点击 Generate A/B Versions 后显示候选版本 A。</p>';

        const emptyB = document.createElement("section");
        emptyB.className = "result-block";
        emptyB.innerHTML = '<p class="section-label">Version B</p><p class="inline-note">点击 Generate A/B Versions 后显示候选版本 B。</p>';

        abNodes.grid.appendChild(emptyA);
        abNodes.grid.appendChild(emptyB);
        abNodes.status.textContent = abState.isGeneratingAB ? "正在生成 A/B versions..." : "A/B compare 尚未生成。";
        return;
    }

    const diffState = abState.versionA && abState.versionB
        ? buildABDiffState(abState.versionA, abState.versionB)
        : null;

    if (abState.versionA) {
        abNodes.grid.appendChild(buildABVersionCard("A", abState.versionA, diffState));
    }

    if (abState.versionB) {
        abNodes.grid.appendChild(buildABVersionCard("B", abState.versionB, diffState));
    }

    if (abState.isGeneratingAB) {
        abNodes.status.textContent = "正在生成 A/B versions...";
        return;
    }

    abNodes.status.textContent = abState.selectedVersion
        ? `A/B versions ready. Current selection: Version ${abState.selectedVersion}.`
        : "A/B versions ready. Choose one to continue.";
}

function useABVersion(versionKey) {
    const selectedPackage = versionKey === "A" ? abState.versionA : abState.versionB;
    if (!selectedPackage) {
        abNodes.status.textContent = `Version ${versionKey} 不存在，无法选用。`;
        return;
    }

    abState.selectedVersion = versionKey;
    applySelectedVersionTheme();
    updateEditorVersionIndicator();
    const formSnapshot = collectFormSnapshot();
    setCurrentContentPackage(selectedPackage, formSnapshot);
    renderABComparePanel();
    formStatus.textContent = `已选用 Version ${versionKey}，当前正式结果为 draft。`;
    confirmStatusText.textContent = `Version ${versionKey} 已进入正式工作流，可继续 Confirm、Regenerate 或 Structured Editor。`;
}

function buildPackageFromEditor() {
    const currentPackage = pageState.currentContentPackage || {};

    return {
        ...currentPackage,
        title: editorState.title,
        script: editorState.scriptItems.map((item) => item.text.trim()).filter(Boolean).slice(0, 3),
        highlights: editorState.highlightItems.map((item) => item.text.trim()).filter(Boolean).slice(0, 3),
        keywords: editorState.keywordItems.map((item) => item.text.trim()).filter(Boolean).slice(0, 6),
        meta: {
            ...(currentPackage.meta || {}),
            confirm_status: "draft",
        },
    };
}

function applyManualEdit() {
    if (!pageState.currentContentPackage) {
        confirmStatusText.textContent = "请先 Generate。";
        return;
    }

    const newPackage = buildPackageFromEditor();

    pageState.currentContentPackage = newPackage;
    pageState.isConfirmed = false;

    renderContentPackage(newPackage);
    syncActionState();

    formStatus.textContent = "编辑已应用（draft）";
    editorNodes.status.textContent = "Structured Editor 修改已覆盖当前 content package。";
    confirmStatusText.textContent = "当前结果已被手动修改并回到 draft，可继续 Confirm 或 Regenerate。";
}

function addKeyword() {
    if (!pageState.currentContentPackage) {
        confirmStatusText.textContent = "请先 Generate，再添加 keyword。";
        return;
    }

    const text = String(editorNodes.keywordInput.value || "").trim();
    if (!text) {
        editorNodes.status.textContent = "请输入 keyword 后再添加。";
        return;
    }

    editorState.keywordItems = [...editorState.keywordItems, createEditorItem("k", text)];
    editorNodes.keywordInput.value = "";
    renderEditor();
    editorNodes.status.textContent = "keyword 已加入编辑器，点击 Apply Edit 后会覆盖当前 package。";
}

async function requestContentPackage(requestReason) {
    const contentPackage = await fetchGeneratedPackage();

    clearSelectedVersionContext();
    const formSnapshot = collectFormSnapshot();
    setCurrentContentPackage(contentPackage, formSnapshot);
    renderABComparePanel();

    if (requestReason === "regenerate_with_feedback") {
        formStatus.textContent = "Regenerate 完成：已根据反馈重新生成新版本，当前状态为 draft。";
        confirmStatusText.textContent = "当前结果已按反馈方向重生成为新的 draft content package。";
        return;
    }

    if (requestReason === "regenerate") {
        formStatus.textContent = "Regenerate 完成：已重新生成新版本，当前状态为 draft。";
        confirmStatusText.textContent = "当前结果为新的 draft content package，如需确认请点击 Confirm。";
        return;
    }

    formStatus.textContent = "Generate 完成：已生成 draft content package。";
    confirmStatusText.textContent = "当前结果为 draft content package，可 Confirm、Regenerate 或进入 Structured Editor。";
}

async function requestABPackages() {
    setABGeneratingState(true);
    clearSelectedVersionContext();
    renderABComparePanel();
    abNodes.status.textContent = "正在生成 A/B versions...";
    formStatus.textContent = "正在生成 A/B 候选版本...";

    try {
        const versionA = await fetchGeneratedPackage();
        const versionB = await fetchGeneratedPackage();

        abState.versionA = versionA;
        abState.versionB = versionB;
        renderABComparePanel();

        formStatus.textContent = "A/B 候选版本已生成，请选择一个进入正式结果区。";
        confirmStatusText.textContent = "A/B Compare Panel 已就绪；选择 Version A 或 Version B 后才会进入正式工作流。";
    } catch (error) {
        abState.versionA = null;
        abState.versionB = null;
        renderABComparePanel();
        formStatus.textContent = error instanceof Error ? error.message : "A/B 生成失败，请稍后重试。";
    } finally {
        setABGeneratingState(false);
        renderABComparePanel();
    }
}

function confirmCurrentContentPackage() {
    if (!pageState.currentContentPackage) {
        confirmStatusText.textContent = "请先 Generate，再执行 Confirm。";
        return;
    }

    pageState.currentContentPackage = {
        ...pageState.currentContentPackage,
        meta: {
            ...(pageState.currentContentPackage.meta || {}),
            confirm_status: "confirmed",
        },
    };
    pageState.isConfirmed = true;

    renderContentPackage(pageState.currentContentPackage);
    syncActionState();
    formStatus.textContent = "当前结果已确认，可继续查看或手动编辑。";
    confirmStatusText.textContent = "当前结果已确认（confirmed）。如需新版本，请点击 Regenerate。";
}

async function regenerateCurrentContentPackage() {
    if (!pageState.hasGenerated) {
        confirmStatusText.textContent = "请先 Generate，再执行 Regenerate。";
        return;
    }

    const feedbackText = String(document.getElementById("feedback_text")?.value || "").trim();
    const requestReason = feedbackText ? "regenerate_with_feedback" : "regenerate";

    setGeneratingState(true);
    formStatus.textContent = feedbackText
        ? "正在根据反馈重新生成 content package..."
        : "正在重新生成 content package...";

    try {
        await requestContentPackage(requestReason);
    } catch (error) {
        formStatus.textContent = error instanceof Error ? error.message : "重新生成失败，请稍后重试。";
    } finally {
        setGeneratingState(false);
    }
}

async function handleGenerate(event) {
    event.preventDefault();
    setGeneratingState(true);
    formStatus.textContent = "正在生成正式 content package...";

    try {
        await requestContentPackage("generate");
    } catch (error) {
        formStatus.textContent = error instanceof Error ? error.message : "内容生成失败，请稍后重试。";
    } finally {
        setGeneratingState(false);
    }
}

function handleManualEditOpen() {
    if (manualEditDetails) {
        manualEditDetails.open = true;
        manualEditDetails.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    if (!pageState.currentContentPackage) {
        confirmStatusText.textContent = "请先 Generate，再进入 Structured Editor。";
        return;
    }

    editorNodes.title.focus();
    editorNodes.status.textContent = "Structured Editor 已就绪，可逐项修改后 Apply Edit。";
}

form.addEventListener("submit", handleGenerate);

if (confirmButton) {
    confirmButton.addEventListener("click", confirmCurrentContentPackage);
}

if (regenerateButton) {
    regenerateButton.addEventListener("click", regenerateCurrentContentPackage);
}

if (manualEditButton) {
    manualEditButton.addEventListener("click", handleManualEditOpen);
}

if (generateABButton) {
    generateABButton.addEventListener("click", requestABPackages);
}

if (referenceImagesInput) {
    referenceImagesInput.addEventListener("change", () => handleReferenceFilesChange("image"));
}

if (referenceVideosInput) {
    referenceVideosInput.addEventListener("change", () => handleReferenceFilesChange("video"));
}

if (editorNodes.title) {
    editorNodes.title.addEventListener("input", (event) => {
        editorState.title = event.target.value;
    });
}

if (editorNodes.applyButton) {
    editorNodes.applyButton.addEventListener("click", applyManualEdit);
}

if (editorNodes.keywordAddButton) {
    editorNodes.keywordAddButton.addEventListener("click", addKeyword);
}

if (editorNodes.keywordInput) {
    editorNodes.keywordInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            addKeyword();
        }
    });
}

renderEditor();
renderABComparePanel();
applySelectedVersionTheme();
updateEditorVersionIndicator();
renderImageUploadList();
renderVideoUploadList();
syncActionState();