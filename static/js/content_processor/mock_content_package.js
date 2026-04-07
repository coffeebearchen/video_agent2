function pickSnippet(rawText, fallback) {
    const normalized = String(rawText || "").trim();
    if (!normalized) {
        return fallback;
    }

    const cleaned = normalized.replace(/\s+/g, " ").trim();
    return cleaned.slice(0, 28) || fallback;
}

function buildMockTitle(rawText, styleMode) {
    const snippet = pickSnippet(rawText, "内容重点");

    if (styleMode === "authority") {
        return `不要只看${snippet.slice(0, 10)}`;
    }
    if (styleMode === "story") {
        return `很多人先看${snippet.slice(0, 10)}，但关键不止这一层`;
    }
    if (styleMode === "product") {
        return `先把${snippet.slice(0, 10)}整理成可确认内容包`;
    }
    if (styleMode === "ads") {
        return `${snippet.slice(0, 12)}，先抓主信息再往下走`;
    }

    return `本质上，先把${snippet.slice(0, 10)}整理清楚`;
}

export function getMockContentPackage(input) {
    const rawText = String(input.raw_text || "").trim();
    const contentMode = String(input.content_mode || "finance");
    const styleMode = String(input.style_mode || "knowledge");
    const scriptLengthTarget = Number(input.script_length_target || 100);
    const baseSnippet = pickSnippet(rawText, "用户原始内容");

    return {
        content_mode: contentMode,
        style_mode: styleMode,
        title: buildMockTitle(rawText, styleMode),
        script: [
            `先抽取原始内容中的主信息：${baseSnippet}`,
            `按 ${contentMode} / ${styleMode} 组合整理成单一正式 content package。`,
            `保留 script_length_target=${scriptLengthTarget}，为后续表达模块输入做准备。`,
        ],
        highlights: [
            `${contentMode} 模式`,
            `${styleMode} 单风格生成`,
            `长度目标 ${scriptLengthTarget}`,
        ],
        keywords: [
            "content package",
            contentMode,
            styleMode,
            "draft",
        ],
        meta: {
            script_length_target: scriptLengthTarget,
            confirm_status: "draft",
            auto_flow: false,
        },
    };
}