const state = {
  cardToken: new URLSearchParams(window.location.search).get("card") || "",
  card: null,
  messages: [],
  latestId: "",
  waitStartedAt: Date.now(),
};

const els = {
  countryCode: document.querySelector("#countryCode"),
  phoneNumber: document.querySelector("#phoneNumber"),
  receiveLimit: document.querySelector("#receiveLimit"),
  expiresAt: document.querySelector("#expiresAt"),
  copyNumber: document.querySelector("#copyNumberBtn"),
  waitLabel: document.querySelector("#waitLabel"),
  waitTimer: document.querySelector("#waitTimer"),
  list: document.querySelector("#recordList"),
  template: document.querySelector("#recordTemplate"),
  instructions: document.querySelector("#instructions"),
};

function dashboardBasePath() {
  return window.location.pathname.replace(/\/user\/?$/, "");
}

function apiUrl(path) {
  return `${window.location.origin}${dashboardBasePath()}${path}`;
}

function pad(value) {
  return String(value).padStart(2, "0");
}

function formatDuration(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  return `${pad(Math.floor(safe / 60))}:${pad(safe % 60)}`;
}

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function formatExpiry(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()} ${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
}

function showCopyStatus(button, text) {
  if (!button) return;
  const oldText = button.textContent;
  button.textContent = text;
  setTimeout(() => {
    button.textContent = oldText;
  }, 900);
}

function copyTextFallback(text) {
  const input = document.createElement("textarea");
  input.value = text;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.left = "-9999px";
  input.style.top = "0";
  input.style.opacity = "0";
  input.style.pointerEvents = "none";
  document.body.append(input);

  const selection = document.getSelection();
  const previousRange = selection && selection.rangeCount > 0 ? selection.getRangeAt(0) : null;

  input.focus({ preventScroll: true });
  input.select();
  input.setSelectionRange(0, input.value.length);

  let copied = false;
  try {
    copied = document.execCommand("copy");
  } finally {
    input.remove();
    if (selection) {
      selection.removeAllRanges();
      if (previousRange) selection.addRange(previousRange);
    }
  }

  if (!copied) throw new Error("copy command failed");
}

async function copyText(text, button) {
  const value = String(text || "");
  try {
    if (window.isSecureContext && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
    } else {
      copyTextFallback(value);
    }
    showCopyStatus(button, "已复制");
  } catch {
    try {
      copyTextFallback(value);
      showCopyStatus(button, "已复制");
    } catch {
      window.prompt("请手动复制", value);
      showCopyStatus(button, "已选中");
    }
  }
}

function renderSummary() {
  const card = state.card || {};
  els.countryCode.textContent = card.countryCode || "+86";
  els.phoneNumber.textContent = card.phoneNumber || "未配置";
  const limit = Number(card.receiveLimit) || 0;
  const used = Number(card.usedCount) || 0;
  els.receiveLimit.textContent = limit > 0 ? `${used} / ${limit}` : `${used} / 未配置`;
  els.expiresAt.textContent = formatExpiry(card.expiresAt);
  els.copyNumber.disabled = !card.available;
  const service = card.serviceName || "对应APP";
  els.instructions.children[0].textContent = `复制手机号，打开${service}。`;
  els.instructions.children[1].textContent = `在${service}中粘贴手机号并获取验证码。`;
  document.title = `${card.serviceName || "验证码"}接收`;
}

function renderError(message) {
  els.waitLabel.textContent = "无法接收";
  els.waitTimer.textContent = "00:00";
  els.list.innerHTML = "";
  const error = document.createElement("div");
  error.className = "error";
  error.textContent = message;
  els.list.append(error);
}

function renderRecords() {
  els.list.innerHTML = "";

  if (!state.messages.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent =
      state.card && !state.card.available
        ? state.card.unavailableReason || "当前不可用"
        : "暂无短信，请先在官方页面发送验证码。";
    els.list.append(empty);
    return;
  }

  for (const item of state.messages) {
    const fragment = els.template.content.cloneNode(true);
    const row = fragment.querySelector(".record-row");
    const code = fragment.querySelector(".code");
    const time = fragment.querySelector(".time");
    const copy = fragment.querySelector(".copy-code");
    const codeText = item.code || "无验证码";

    code.textContent = codeText;
    time.textContent = formatTime(item.receivedAt);
    copy.disabled = !item.code;
    copy.addEventListener("click", () => copyText(item.code || "", copy));

    if (item.id && item.id === state.latestId) {
      code.classList.add("pulse");
    }

    els.list.append(fragment);
  }
}

function updateWaitTimer() {
  if (state.card && !state.card.available) {
    els.waitTimer.textContent = "00:00";
    els.waitLabel.textContent = state.card.unavailableReason || "当前不可用";
    return;
  }

  const total = Number(state.card?.waitSeconds) || 60;
  const elapsed = Math.floor((Date.now() - state.waitStartedAt) / 1000);
  const remaining = Math.max(0, total - elapsed);
  els.waitTimer.textContent = formatDuration(remaining);
  els.waitLabel.textContent = remaining > 0 ? "等待短信中..." : "继续等待中...";
}

async function loadCard() {
  if (!state.cardToken) {
    renderError("链接缺少 card 参数，请检查客户链接。");
    return;
  }

  const response = await fetch(apiUrl(`/api/user-card?card=${encodeURIComponent(state.cardToken)}`), {
    cache: "no-store",
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok || !data.ok) {
    renderError(data.error || `读取失败：HTTP ${response.status}`);
    return;
  }

  const oldLatest = state.messages[0]?.id || "";
  state.card = data.card || {};
  state.messages = Array.isArray(data.messages) ? data.messages : [];
  const newLatest = state.messages[0]?.id || "";

  if (newLatest && newLatest !== oldLatest) {
    state.latestId = newLatest;
    state.waitStartedAt = Date.now();
  } else if (!state.latestId) {
    state.latestId = newLatest;
  }

  renderSummary();
  renderRecords();
  updateWaitTimer();
}

els.copyNumber.addEventListener("click", () => {
  copyText(state.card?.phoneNumber || "", els.copyNumber);
});

loadCard().catch((error) => renderError(`读取失败：${error.message}`));
setInterval(() => loadCard().catch(() => {}), 5000);
setInterval(updateWaitTimer, 1000);
