const REFRESH_MS = 2000;

const FILES = {
  progress: "../output/highlight_ab/progress_status.json",
  reportJson: "../output/highlight_ab/ab_results_three_topics.json",
  reportMd: "../output/highlight_ab/ab_results_three_topics.md",
  topic1: "../output/highlight_ab/topic1_result.json",
  topic2: "../output/highlight_ab/topic2_result.json",
  topic3: "../output/highlight_ab/topic3_result.json",
};

const TOPICS = ["topic1", "topic2", "topic3"];

function bust(url) {
  return `${url}?t=${Date.now()}`;
}

async function fetchJson(url) {
  const response = await fetch(bust(url), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function checkFile(url) {
  try {
    const response = await fetch(bust(url), { cache: "no-store" });
    return response.ok;
  } catch (_error) {
    return false;
  }
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value;
  }
}

function setBadge(id, value) {
  const element = document.getElementById(id);
  if (!element) {
    return;
  }
  element.textContent = value;
  element.className = "badge";
  if (value === "running") {
    element.classList.add("badge-running");
  } else if (value === "done") {
    element.classList.add("badge-done");
  } else if (value === "failed") {
    element.classList.add("badge-failed");
  } else if (value === "pending") {
    element.classList.add("badge-pending");
  } else {
    element.classList.add("badge-neutral");
  }
}

function setLinkState(id, exists) {
  const element = document.getElementById(id);
  if (!element) {
    return;
  }
  element.classList.toggle("disabled-link", !exists);
}

function topicStatus(topicKey, progress, topicResultExists) {
  const completedTopics = progress?.completed_topics || [];
  if (completedTopics.includes(topicKey) || topicResultExists) {
    return "done";
  }
  if (progress?.status === "running" && progress?.current_topic === topicKey) {
    return "running";
  }
  if (progress?.status === "failed" && progress?.current_topic === topicKey) {
    return "failed";
  }
  return "pending";
}

function findTopicConclusion(reportJson, topicKey, topicJson) {
  if (topicJson?.conclusion) {
    return topicJson.conclusion;
  }
  const topicResults = reportJson?.topic_results || [];
  const match = topicResults.find((item) => item.topic_key === topicKey);
  return match?.conclusion || "pending";
}

async function refreshPreview() {
  const now = new Date();
  setText("last-refresh", `最近刷新: ${now.toLocaleString()}`);

  const progressPromise = fetchJson(FILES.progress).catch(() => null);
  const reportPromise = fetchJson(FILES.reportJson).catch(() => null);
  const topicPromises = TOPICS.map((topicKey) => fetchJson(FILES[topicKey]).catch(() => null));
  const fileChecksPromise = Promise.all([
    checkFile(FILES.progress),
    checkFile(FILES.reportJson),
    checkFile(FILES.reportMd),
    checkFile(FILES.topic1),
    checkFile(FILES.topic2),
    checkFile(FILES.topic3),
  ]);

  const [progress, reportJson, topicJsonList, fileChecks] = await Promise.all([
    progressPromise,
    reportPromise,
    Promise.all(topicPromises),
    fileChecksPromise,
  ]);

  const [progressExists, reportJsonExists, reportMdExists, topic1Exists, topic2Exists, topic3Exists] = fileChecks;
  const topicMap = {
    topic1: topicJsonList[0],
    topic2: topicJsonList[1],
    topic3: topicJsonList[2],
  };
  const topicExistsMap = {
    topic1: topic1Exists,
    topic2: topic2Exists,
    topic3: topic3Exists,
  };

  setBadge("status-badge", progress?.status || "pending");
  setText("current-topic", progress?.current_topic || "-");
  setText("current-variant", progress?.current_variant || "-");
  setText(
    "completed-cases",
    `${progress?.completed_cases ?? 0} / ${progress?.total_cases ?? 6}`
  );
  setText("last-update-time", progress?.last_update_time || "-");
  setText(
    "status-note",
    progressExists
      ? "preview 正在只读 progress_status.json"
      : "未找到 progress_status.json"
  );

  setText(
    "overall-conclusion",
    reportJson?.summary?.overall_conclusion || "pending"
  );
  setText(
    "completed-topic-count",
    `${reportJson?.summary?.completed_topic_count ?? 0} / ${reportJson?.summary?.total_topic_count ?? 3}`
  );

  for (const topicKey of TOPICS) {
    const exists = topicExistsMap[topicKey];
    const status = topicStatus(topicKey, progress, exists);
    const conclusion = findTopicConclusion(reportJson, topicKey, topicMap[topicKey]);

    setBadge(`${topicKey}-status`, status);
    setText(`${topicKey}-file-state`, exists ? "已生成，可查看" : "未生成");
    setText(`${topicKey}-conclusion`, conclusion);
    setText(`${topicKey}-card-conclusion`, conclusion);
    setText(`${topicKey}-result-state`, exists ? "可查看" : "未生成");
    setLinkState(`${topicKey}-link`, exists);
    setLinkState(`${topicKey}-result-link`, exists);
  }

  setText("progress-file-state", progressExists ? "可查看" : "未生成");
  setText("report-json-state", reportJsonExists ? "可查看" : "未生成");
  setText("report-md-state", reportMdExists ? "可查看" : "未生成");

  setLinkState("progress-file-link", progressExists);
  setLinkState("report-json-link", reportJsonExists);
  setLinkState("report-md-link", reportMdExists);
}

refreshPreview();
setInterval(refreshPreview, REFRESH_MS);