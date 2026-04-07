const form = document.getElementById("generate-form");
const textInput = document.getElementById("text");
const contentModeInput = document.getElementById("content_mode");
const button = document.getElementById("generate-button");
const errorMessage = document.getElementById("error-message");
const resultsContainer = document.getElementById("results");
const cardTemplate = document.getElementById("result-card-template");

const STYLE_LABELS = {
    knowledge: "知识型",
    authority: "老板型",
    story: "故事型",
};

const STYLE_BADGES = {
    knowledge: "🎯 知识型",
    authority: "🧠 老板型",
    story: "🎬 故事型",
};

function buildCopyText(item) {
    const title = item.title || "内容待生成";
    const scenes = Array.isArray(item.scenes) ? item.scenes : [];
    const lines = scenes.length === 0 ? ["1. 内容待生成"] : scenes.map((scene, index) => `${index + 1}. ${scene}`);

    return [
        "标题：",
        title,
        "",
        "视频脚本：",
        ...lines,
    ].join("\n");
}

async function copyCardText(button, item) {
    const originalText = button.textContent;
    try {
        await navigator.clipboard.writeText(buildCopyText(item));
        button.textContent = "已复制";
        button.classList.add("is-copied");
        window.setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove("is-copied");
        }, 1200);
    } catch (error) {
        button.textContent = "复制失败";
        window.setTimeout(() => {
            button.textContent = originalText;
        }, 1200);
    }
}

function setLoading(isLoading) {
    button.disabled = isLoading;
    button.textContent = isLoading ? "生成中..." : "生成多风格视频文案";
}

function setError(visible, text = "生成失败，请稍后重试") {
    errorMessage.hidden = !visible;
    errorMessage.textContent = text;
}

function renderEmptyState() {
    resultsContainer.innerHTML = "";
    const block = document.createElement("div");
    block.className = "empty-state";
    block.textContent = "输入一段内容后，这里会展示三种风格的视频表达结果。";
    resultsContainer.appendChild(block);
}

function renderResults(results) {
    resultsContainer.innerHTML = "";

    results.forEach((item) => {
        const fragment = cardTemplate.content.cloneNode(true);
        const styleMode = item.style_mode || "unknown";
        const styleLabel = STYLE_LABELS[styleMode] || styleMode;
        const styleBadge = STYLE_BADGES[styleMode] || styleLabel;
        const card = fragment.querySelector(".result-card");
        card.classList.add(styleMode);

        fragment.querySelector(".style-tag").textContent = styleBadge;
        fragment.querySelector(".card-title").textContent = styleLabel;
        fragment.querySelector(".headline-text").textContent = item.title || "内容待生成";

        const copyButton = fragment.querySelector(".copy-btn");
        copyButton.addEventListener("click", () => {
            copyCardText(copyButton, item);
        });

        const sceneList = fragment.querySelector(".scene-list");
        const scenes = Array.isArray(item.scenes) ? item.scenes : [];
        if (scenes.length === 0) {
            const li = document.createElement("li");
            li.textContent = "内容待生成";
            sceneList.appendChild(li);
        } else {
            scenes.forEach((scene) => {
                const li = document.createElement("li");
                li.textContent = scene;
                sceneList.appendChild(li);
            });
        }

        resultsContainer.appendChild(fragment);
    });
}

async function handleSubmit(event) {
    event.preventDefault();
    const text = textInput.value.trim();
    const contentMode = contentModeInput.value;

    if (text.length < 4) {
        setError(true, "请输入更完整的内容。");
        return;
    }

    setLoading(true);
    setError(false);

    try {
        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                text,
                content_mode: contentMode,
            }),
        });

        const payload = await response.json();
        if (!response.ok || !payload.ok) {
            throw new Error(payload.message || "生成失败，请稍后重试");
        }

        renderResults(payload.results || []);
    } catch (error) {
        setError(true, "生成失败，请稍后重试");
    } finally {
        setLoading(false);
    }
}

form.addEventListener("submit", handleSubmit);
renderEmptyState();