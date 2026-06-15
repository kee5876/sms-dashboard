const state = {
  messages: [],
  filtered: [],
  cards: [],
  filteredCards: [],
  phones: [],
  goods: [],
  filteredGoods: [],
  stockItems: [],
  filteredStockItems: [],
  orders: [],
  filteredOrders: [],
  agents: [],
  auditLogs: [],
  dashboard: null,
  query: "",
  memberQuery: "",
  cardQuery: "",
  cardStatus: "all",
  goodsQuery: "",
  stockGoodsFilter: "",
  orderQuery: "",
  activeView: "overview",
  settingsLoaded: false,
  settings: {
    defaultCardExpireMinutes: 1440,
    defaultCardReceiveLimit: 1,
  },
};

const CARD_EXPIRE_OPTIONS = [1440, 2880, 4320];

const els = {
  menuItems: Array.from(document.querySelectorAll("[data-view]")),
  pages: Array.from(document.querySelectorAll("[data-view-page]")),
  pageTitle: document.querySelector(".page-title h1"),
  pageCrumb: document.querySelector(".page-title .eyebrow"),
  list: document.querySelector("#messageList"),
  template: document.querySelector("#messageTemplate"),
  count: document.querySelector("#messageCount"),
  lastSync: document.querySelector("#lastSync"),
  status: document.querySelector("#gatewayStatus"),
  syncState: document.querySelector("#syncState"),
  hint: document.querySelector("#panelHint"),
  search: document.querySelector("#searchInput"),
  refresh: document.querySelector("#refreshBtn"),
  test: document.querySelector("#testBtn"),
  refreshDashboard: document.querySelector("#refreshDashboardBtn"),
  overviewHint: document.querySelector("#overviewHint"),
  statMessagesToday: document.querySelector("#statMessagesToday"),
  statCardsToday: document.querySelector("#statCardsToday"),
  statStock: document.querySelector("#statStock"),
  statOrdersToday: document.querySelector("#statOrdersToday"),
  statActiveCards: document.querySelector("#statActiveCards"),
  statPhonesEnabled: document.querySelector("#statPhonesEnabled"),
  recentOrders: document.querySelector("#recentOrders"),
  recentAuditLogs: document.querySelector("#recentAuditLogs"),
  refreshSystemStatus: document.querySelector("#refreshSystemStatusBtn"),
  systemStatusHint: document.querySelector("#systemStatusHint"),
  statusHealth: document.querySelector("#statusHealth"),
  statusHealthDetail: document.querySelector("#statusHealthDetail"),
  statusStorage: document.querySelector("#statusStorage"),
  statusStorageDetail: document.querySelector("#statusStorageDetail"),
  statusDatabase: document.querySelector("#statusDatabase"),
  statusDatabaseDetail: document.querySelector("#statusDatabaseDetail"),
  statusGateway: document.querySelector("#statusGateway"),
  statusGatewayDetail: document.querySelector("#statusGatewayDetail"),
  statusWebhook: document.querySelector("#statusWebhook"),
  statusWebhookDetail: document.querySelector("#statusWebhookDetail"),
  statusXgjGateway: document.querySelector("#statusXgjGateway"),
  memberSearch: document.querySelector("#memberSearchInput"),
  memberList: document.querySelector("#memberList"),
  memberHint: document.querySelector("#memberPanelHint"),
  memberNewCard: document.querySelector("#memberNewCardBtn"),
  agentForm: document.querySelector("#agentForm"),
  agentList: document.querySelector("#agentList"),
  agentTemplate: document.querySelector("#agentTemplate"),
  agentHint: document.querySelector("#agentPanelHint"),
  newAgent: document.querySelector("#newAgentBtn"),
  clearAgent: document.querySelector("#clearAgentBtn"),
  agentId: document.querySelector("#agentId"),
  agentName: document.querySelector("#agentName"),
  agentContact: document.querySelector("#agentContact"),
  agentRate: document.querySelector("#agentRate"),
  agentNote: document.querySelector("#agentNote"),
  agentEnabled: document.querySelector("#agentEnabled"),
  auditLogList: document.querySelector("#auditLogList"),
  logHint: document.querySelector("#logPanelHint"),
  refreshLogs: document.querySelector("#refreshLogsBtn"),
  logout: document.querySelector("#logoutBtn"),
  webhookPath: document.querySelector("#webhookPath"),
  gatewayWebhookPath: document.querySelector("#gatewayWebhookPath"),
  xgjGatewayPath: document.querySelector("#xgjGatewayPath"),
  copyGateway: document.querySelector("#copyGatewayBtn"),
  settingsForm: document.querySelector("#settingsForm"),
  settingsHint: document.querySelector("#settingsHint"),
  defaultCardExpireMinutes: document.querySelector("#defaultCardExpireMinutes"),
  defaultCardReceiveLimit: document.querySelector("#defaultCardReceiveLimit"),
  cardForm: document.querySelector("#cardForm"),
  cardList: document.querySelector("#cardList"),
  cardTemplate: document.querySelector("#cardTemplate"),
  cardHint: document.querySelector("#cardPanelHint"),
  cardSearch: document.querySelector("#cardSearchInput"),
  cardStatusFilter: document.querySelector("#cardStatusFilter"),
  phoneForm: document.querySelector("#phoneForm"),
  phoneList: document.querySelector("#phoneList"),
  phoneTemplate: document.querySelector("#phoneTemplate"),
  phoneHint: document.querySelector("#phonePanelHint"),
  newPhone: document.querySelector("#newPhoneBtn"),
  clearPhone: document.querySelector("#clearPhoneBtn"),
  phoneId: document.querySelector("#phoneId"),
  phoneLabel: document.querySelector("#phoneLabel"),
  poolCountry: document.querySelector("#poolCountry"),
  poolPhone: document.querySelector("#poolPhone"),
  phoneDeviceId: document.querySelector("#phoneDeviceId"),
  phoneSimNumber: document.querySelector("#phoneSimNumber"),
  phoneProvider: document.querySelector("#phoneProvider"),
  phoneNote: document.querySelector("#phoneNote"),
  phoneEnabled: document.querySelector("#phoneEnabled"),
  newCard: document.querySelector("#newCardBtn"),
  exportTxt: document.querySelector("#exportTxtBtn"),
  exportCsv: document.querySelector("#exportCsvBtn"),
  clearCard: document.querySelector("#clearCardBtn"),
  batchGenerate: document.querySelector("#batchGenerateBtn"),
  cardToken: document.querySelector("#cardToken"),
  cardAssignment: document.querySelector("#cardAssignment"),
  cardPhoneSelect: document.querySelector("#cardPhoneSelect"),
  cardCountry: document.querySelector("#cardCountry"),
  cardPhone: document.querySelector("#cardPhone"),
  cardExpireMinutes: document.querySelector("#cardExpireMinutes"),
  cardExpires: document.querySelector("#cardExpires"),
  cardLimit: document.querySelector("#cardLimit"),
  cardWait: document.querySelector("#cardWait"),
  cardService: document.querySelector("#cardService"),
  cardKeywords: document.querySelector("#cardKeywords"),
  batchCount: document.querySelector("#batchCount"),
  cardEnabled: document.querySelector("#cardEnabled"),
  goodsForm: document.querySelector("#goodsForm"),
  goodsList: document.querySelector("#goodsList"),
  goodsTemplate: document.querySelector("#goodsTemplate"),
  goodsHint: document.querySelector("#goodsHint"),
  newGoods: document.querySelector("#newGoodsBtn"),
  clearGoods: document.querySelector("#clearGoodsBtn"),
  goodsNo: document.querySelector("#goodsNo"),
  goodsName: document.querySelector("#goodsName"),
  goodsPrice: document.querySelector("#goodsPrice"),
  goodsNote: document.querySelector("#goodsNote"),
  goodsEnabled: document.querySelector("#goodsEnabled"),
  goodsSearch: document.querySelector("#goodsSearchInput"),
  stockImportForm: document.querySelector("#stockImportForm"),
  stockGoodsSelect: document.querySelector("#stockGoodsSelect"),
  stockGoodsFilter: document.querySelector("#stockGoodsFilter"),
  stockImportText: document.querySelector("#stockImportText"),
  stockImportNote: document.querySelector("#stockImportNote"),
  stockList: document.querySelector("#stockList"),
  stockTemplate: document.querySelector("#stockTemplate"),
  refreshOrders: document.querySelector("#refreshOrdersBtn"),
  orderSearch: document.querySelector("#orderSearchInput"),
  orderList: document.querySelector("#orderList"),
  ordersHint: document.querySelector("#ordersHint"),
};

const viewMeta = {
  overview: { title: "数据面板", crumb: "管理后台 / 总览" },
  "system-status": { title: "系统状态", crumb: "管理后台 / 运行状态" },
  members: { title: "会员管理", crumb: "管理后台 / 客户会员" },
  messages: { title: "短信记录", crumb: "运营工作台 / 验证码短信" },
  phones: { title: "手机号池", crumb: "资源管理 / 号码资源" },
  cards: { title: "卡密管理", crumb: "商品交付 / 卡密链接" },
  agents: { title: "代理管理", crumb: "管理后台 / 渠道代理" },
  goods: { title: "商品库存", crumb: "商品交付 / 库存卡密" },
  orders: { title: "订单记录", crumb: "商品交付 / 闲管家订单" },
  logs: { title: "系统日志", crumb: "管理后台 / 操作审计" },
  settings: { title: "系统设置", crumb: "管理后台 / 接入与默认值" },
};

const viewAliases = {
  gateway: "settings",
};

function basePath() {
  const path = window.location.pathname;
  if (path === "/" || path === "") return "";
  return path.endsWith("/") ? path.slice(0, -1) : path;
}

function apiUrl(path) {
  return `${window.location.protocol}//${window.location.host}${basePath()}${path}`;
}

function viewFromHash() {
  const value = window.location.hash.replace(/^#/, "");
  const normalized = viewAliases[value] || value;
  return viewMeta[normalized] ? normalized : "overview";
}

function showView(view, updateHash = true) {
  const next = viewMeta[view] ? view : "overview";
  state.activeView = next;
  for (const item of els.menuItems) {
    item.classList.toggle("active", item.dataset.view === next);
  }
  for (const page of els.pages) {
    page.classList.toggle("active", page.dataset.viewPage === next);
  }
  els.pageTitle.textContent = viewMeta[next].title;
  els.pageCrumb.textContent = viewMeta[next].crumb;
  if (updateHash && window.location.hash !== `#${next}`) {
    history.replaceState(null, "", `#${next}`);
  }
}

function extractCode(message) {
  const text = String(message || "");
  const matches = text.match(/(?<!\d)\d{4,8}(?!\d)/g);
  return matches ? matches[0] : "";
}

function formatTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(date);
}

function formatUnixTime(value) {
  const seconds = Number(value) || 0;
  return seconds ? formatTime(new Date(seconds * 1000).toISOString()) : "-";
}

function formatMoney(cents) {
  return `¥${((Number(cents) || 0) / 100).toFixed(2)}`;
}

function actionLabel(action) {
  return (
    {
      settings_updated: "修改全局设置",
      card_saved: "保存卡密",
      cards_batch_created: "批量生成卡密",
      card_toggled: "切换卡密状态",
      card_deleted: "删除卡密",
      phone_saved: "保存手机号",
      phone_toggled: "切换手机号状态",
      phone_deleted: "删除手机号",
      cards_exported: "导出卡密",
      test_message_created: "创建测试短信",
      xgj_order_created: "闲管家发货",
      xgj_stock_order_created: "库存卡密发货",
      xgj_order_duplicate: "重复订单请求",
      xgj_order_reissued: "订单补发",
      goods_saved: "保存商品",
      goods_toggled: "切换商品状态",
      goods_deleted: "删除商品",
      stock_imported: "导入库存",
      stock_toggled: "切换库存状态",
      stock_deleted: "删除库存",
      agent_saved: "保存代理",
      agent_toggled: "切换代理状态",
      agent_deleted: "删除代理",
    }[action] || action || "操作"
  );
}

function toDateTimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16);
  const offsetMs = date.getTimezoneOffset() * 60 * 1000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function fromDateTimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
}

function minutesFromNowLocal(minutes) {
  const safeMinutes = Math.max(Number(minutes) || CARD_EXPIRE_OPTIONS[0], 1);
  return toDateTimeLocal(new Date(Date.now() + safeMinutes * 60 * 1000).toISOString());
}

function normalizeCardExpireMinutes(value) {
  const minutes = Number(value) || CARD_EXPIRE_OPTIONS[0];
  return CARD_EXPIRE_OPTIONS.includes(minutes) ? minutes : CARD_EXPIRE_OPTIONS[0];
}

function closestCardExpireMinutes(value) {
  const minutes = Math.max(Number(value) || CARD_EXPIRE_OPTIONS[0], 1);
  return CARD_EXPIRE_OPTIONS.reduce((best, option) =>
    Math.abs(option - minutes) < Math.abs(best - minutes) ? option : best
  );
}

function remainingExpireMinutes(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return CARD_EXPIRE_OPTIONS[0];
  return Math.max(Math.ceil((date.getTime() - Date.now()) / 60000), 1);
}

function setCardExpireMinutes(value) {
  const minutes = normalizeCardExpireMinutes(value);
  if (els.cardExpireMinutes) {
    els.cardExpireMinutes.value = String(minutes);
  }
  els.cardExpires.value = minutesFromNowLocal(minutes);
}

function applyCardDefaults() {
  setCardExpireMinutes(state.settings.defaultCardExpireMinutes);
  els.cardLimit.value = String(state.settings.defaultCardReceiveLimit || 1);
}

function applySettings(settings, forceCardDefaults = false) {
  if (!settings) return;
  const next = {
    defaultCardExpireMinutes: normalizeCardExpireMinutes(settings.defaultCardExpireMinutes),
    defaultCardReceiveLimit: Math.min(Math.max(Number(settings.defaultCardReceiveLimit) || 1, 1), 100),
  };
  const firstLoad = !state.settingsLoaded;
  state.settingsLoaded = true;
  state.settings = next;
  if (els.defaultCardExpireMinutes) {
    els.defaultCardExpireMinutes.value = String(next.defaultCardExpireMinutes);
  }
  if (els.defaultCardReceiveLimit) {
    els.defaultCardReceiveLimit.value = String(next.defaultCardReceiveLimit);
  }
  if (forceCardDefaults || (firstLoad && !els.cardToken.value && !els.cardExpires.value)) {
    applyCardDefaults();
  }
}

function setSyncState(text, kind = "") {
  els.syncState.classList.remove("ok", "bad");
  if (kind) els.syncState.classList.add(kind);
  els.syncState.textContent = text;
}

function setStatus(config) {
  applySettings(config?.cardDefaults);
  const configured = Boolean(config?.gatewayConfigured);
  const poll = config?.poll || {};
  els.status.classList.remove("ok", "bad");

  if (!configured && config?.webhookTokenSet) {
    els.status.classList.add("ok");
    els.status.lastElementChild.textContent = "Webhook 模式";
    setSyncState("等待短信推送", "ok");
  } else if (!configured) {
    els.status.classList.add("bad");
    els.status.lastElementChild.textContent = "未配置手机";
    setSyncState(poll.lastPollError || "手机网关未配置", "bad");
  } else if (poll.lastPollOk === false) {
    els.status.classList.add("bad");
    els.status.lastElementChild.textContent = "同步失败";
    setSyncState(poll.lastPollError || "同步失败", "bad");
  } else {
    els.status.classList.add("ok");
    els.status.lastElementChild.textContent = "已连接";
    setSyncState(poll.lastPollAt ? "已同步" : "待同步", poll.lastPollAt ? "ok" : "");
  }

  els.lastSync.textContent = poll.lastPollAt ? formatTime(poll.lastPollAt) : "-";
  els.webhookPath.textContent = config?.webhookPath || "/api/sms-webhook";
  els.gatewayWebhookPath.textContent = `${window.location.origin}${basePath()}${
    config?.webhookPath || "/api/sms-webhook"
  }`;
  els.xgjGatewayPath.textContent = `${window.location.origin}${basePath()}/api/xianguanjia`;
}

function filterMessages() {
  const query = state.query.trim().toLowerCase();
  if (!query) {
    state.filtered = state.messages;
    return;
  }

  state.filtered = state.messages.filter((item) => {
    const haystack = [
      item.sender,
      item.recipient,
      item.message,
      item.source,
      item.receivedAt,
      extractCode(item.message),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text || "");
    const old = button.textContent;
    button.textContent = "已复制";
    setTimeout(() => {
      button.textContent = old;
    }, 900);
  } catch {
    window.prompt("复制", text || "");
  }
}

function renderMessages() {
  filterMessages();
  els.count.textContent = String(state.messages.length);
  els.list.innerHTML = "";
  els.hint.textContent = state.query
    ? `匹配 ${state.filtered.length} 条`
    : "按接收时间倒序显示";

  if (!state.filtered.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.query ? "没有匹配短信" : "暂无短信";
    els.list.append(empty);
    return;
  }

  for (const item of state.filtered) {
    const fragment = els.template.content.cloneNode(true);
    const row = fragment.querySelector(".message-row");
    const code = extractCode(item.message);
    const codeEl = fragment.querySelector(".code");
    const sourceEl = fragment.querySelector(".source");
    const metaEl = fragment.querySelector(".meta");
    const bodyEl = fragment.querySelector(".body");
    const copyCode = fragment.querySelector(".copy-code");
    const copyMessage = fragment.querySelector(".copy-message");

    codeEl.textContent = code || "无验证码";
    sourceEl.textContent = item.source || "sms";
    metaEl.textContent = `${item.sender || "未知号码"} · ${formatTime(item.receivedAt)}`;
    bodyEl.textContent = item.message || "";
    copyCode.disabled = !code;
    copyCode.addEventListener("click", () => copyText(code, copyCode));
    copyMessage.addEventListener("click", () => copyText(item.message || "", copyMessage));
    row.dataset.id = item.id || "";
    els.list.append(fragment);
  }
}

function renderActivityList(container, items, type) {
  container.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = type === "order" ? "暂无订单" : "暂无操作日志";
    container.append(empty);
    return;
  }

  for (const item of items) {
    const row = document.createElement("article");
    row.className = "activity-row";
    const title = document.createElement("div");
    title.className = "activity-title";
    const strong = document.createElement("strong");
    const time = document.createElement("span");
    const meta = document.createElement("p");
    meta.className = "activity-meta";

    if (type === "order") {
      strong.textContent = item.orderNo || "-";
      time.textContent = item.orderTime ? formatUnixTime(item.orderTime) : formatTime(item.createdAt);
      meta.textContent = [
        item.goodsName || "卡密商品",
        `数量 ${item.buyQuantity || 0}`,
        `金额 ${formatMoney(item.orderAmount)}`,
        item.statusText || "",
      ]
        .filter(Boolean)
        .join(" · ");
    } else {
      strong.textContent = actionLabel(item.action);
      time.textContent = formatTime(item.createdAt);
      meta.textContent = [item.target, item.clientIp ? `IP ${item.clientIp}` : ""].filter(Boolean).join(" · ");
    }

    title.append(strong, time);
    row.append(title, meta);
    container.append(row);
  }
}

function renderDashboard() {
  const summary = state.dashboard?.summary || {};
  els.statMessagesToday.textContent = String(summary.messagesToday || 0);
  els.statCardsToday.textContent = String(summary.cardsToday || 0);
  els.statStock.textContent = String(summary.stock || 0);
  els.statOrdersToday.textContent = String(summary.ordersToday || 0);
  els.statActiveCards.textContent = String(summary.cardsActive || 0);
  els.statPhonesEnabled.textContent = `${summary.phonesEnabled || 0}/${summary.phonesTotal || 0}`;
  els.overviewHint.textContent = `总短信 ${summary.messagesTotal || 0} · 总卡密 ${
    summary.cardsTotal || 0
  } · 总订单 ${summary.ordersTotal || 0} · 失败订单 ${summary.ordersFailed || 0}`;
  renderActivityList(els.recentOrders, state.dashboard?.recentOrders || [], "order");
  renderActivityList(els.recentAuditLogs, state.dashboard?.recentAuditLogs || [], "audit");
}

function renderSystemStatus(health = {}, config = {}) {
  if (!els.statusHealth) return;
  const poll = config.poll || {};
  const storage = config.storageBackend || health.storageBackend || "-";
  els.statusHealth.textContent = health.ok === false ? "异常" : "正常";
  els.statusHealthDetail.textContent = health.ok === false ? "健康检查未通过" : "服务可以响应请求";
  els.statusStorage.textContent = storage;
  els.statusStorageDetail.textContent = config.mysqlReady
    ? `MySQL 数据库：${config.mysqlDatabase || "-"}`
    : "当前使用本地 JSON 文件存储";
  els.statusDatabase.textContent = health.databaseOk === false ? "不可用" : "可用";
  els.statusDatabaseDetail.textContent = health.databaseError || (config.mysqlRequested ? "MySQL 连接正常" : "未请求 MySQL");
  els.statusGateway.textContent = config.gatewayConfigured ? "已配置" : "未配置";
  els.statusGatewayDetail.textContent = poll.lastPollAt
    ? `最近同步：${formatTime(poll.lastPollAt)}`
    : poll.lastPollError || "等待短信推送或配置手机网关";
  els.statusWebhook.textContent = config.webhookSignatureEnabled ? "签名模式" : "Token 模式";
  els.statusWebhookDetail.textContent = config.webhookTokenSet
    ? "Webhook token 已配置"
    : "Webhook token 仍是默认值或未配置";
  els.statusXgjGateway.textContent = `${window.location.origin}${basePath()}/api/xianguanjia`;
  els.systemStatusHint.textContent = `存储 ${storage} · 网关${config.gatewayConfigured ? "已配置" : "未配置"} · Webhook ${
    config.webhookSignatureEnabled ? "签名校验" : "Token 校验"
  }`;
}

function memberBadge(card) {
  if (!card.enabled) return { text: "已停用", kind: "bad" };
  if (card.expired) return { text: "已过期", kind: "bad" };
  if (!card.available) return { text: card.unavailableReason || "不可用", kind: "bad" };
  return { text: "正常", kind: "ok" };
}

function renderMembers() {
  if (!els.memberList) return;
  const query = state.memberQuery.trim().toLowerCase();
  const members = state.cards.filter((card) => {
    if (!query) return true;
    return [card.card, card.phoneNumber, card.serviceName, card.keywordsText, card.userUrl]
      .join(" ")
      .toLowerCase()
      .includes(query);
  });
  els.memberList.innerHTML = "";
  els.memberHint.textContent =
    members.length === state.cards.length ? `共 ${state.cards.length} 个会员凭证` : `匹配 ${members.length} / 共 ${state.cards.length} 个会员凭证`;

  if (!members.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.cards.length ? "没有匹配会员" : "暂无会员卡密";
    els.memberList.append(empty);
    return;
  }

  for (const card of members) {
    const row = document.createElement("article");
    row.className = "order-row member-row";

    const main = document.createElement("div");
    const title = document.createElement("div");
    title.className = "order-title";
    const token = document.createElement("strong");
    token.textContent = card.card || "-";
    const created = document.createElement("span");
    created.textContent = formatTime(card.createdAt);
    title.append(token, created);
    const meta = document.createElement("p");
    meta.className = "order-meta";
    meta.textContent = [card.serviceName || "接码会员", `${card.countryCode || "+86"} ${card.phoneNumber || "未填手机号"}`]
      .filter(Boolean)
      .join(" · ");
    main.append(title, meta);

    const permission = document.createElement("div");
    permission.className = "order-links";
    const usage = document.createElement("code");
    usage.textContent = `次数 ${card.usedCount || 0}/${card.receiveLimit || 0} · 剩余 ${card.remainingCount ?? 0}`;
    const expires = document.createElement("code");
    expires.textContent = `到期 ${formatTime(card.expiresAt)}`;
    permission.append(usage, expires);

    const statusBox = document.createElement("div");
    statusBox.className = "card-actions";
    const badgeInfo = memberBadge(card);
    const status = document.createElement("span");
    status.className = `card-badge ${badgeInfo.kind}`;
    status.textContent = badgeInfo.text;
    const copy = document.createElement("button");
    copy.type = "button";
    copy.textContent = "复制链接";
    copy.addEventListener("click", () => copyText(card.userUrl || "", copy));
    statusBox.append(status, copy);

    row.append(main, permission, statusBox);
    els.memberList.append(row);
  }
}

function clearAgentForm() {
  if (!els.agentForm) return;
  els.agentForm.reset();
  els.agentId.value = "";
  els.agentRate.value = "0";
  els.agentEnabled.checked = true;
  els.agentHint.textContent = "维护代理资料，便于后续批量发卡和渠道结算。";
}

function fillAgentForm(agent) {
  els.agentId.value = agent.id || "";
  els.agentName.value = agent.name || "";
  els.agentContact.value = agent.contact || "";
  els.agentRate.value = String(agent.ratePercent || 0);
  els.agentNote.value = agent.note || "";
  els.agentEnabled.checked = agent.enabled !== false;
  els.agentHint.textContent = `正在编辑：${agent.name || agent.id}`;
}

function readAgentForm() {
  return {
    id: els.agentId.value.trim(),
    name: els.agentName.value.trim(),
    contact: els.agentContact.value.trim(),
    ratePercent: Number(els.agentRate.value) || 0,
    note: els.agentNote.value.trim(),
    enabled: els.agentEnabled.checked,
  };
}

function renderAgents() {
  if (!els.agentList) return;
  els.agentList.innerHTML = "";
  els.agentHint.textContent = `共 ${state.agents.length} 个代理`;
  if (!state.agents.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "暂无代理";
    els.agentList.append(empty);
    return;
  }
  for (const agent of state.agents) {
    const fragment = els.agentTemplate.content.cloneNode(true);
    const name = fragment.querySelector(".agent-name");
    const badge = fragment.querySelector(".agent-badge");
    const meta = fragment.querySelector(".agent-meta");
    const edit = fragment.querySelector(".edit-agent");
    const toggle = fragment.querySelector(".toggle-agent");
    const remove = fragment.querySelector(".delete-agent");
    name.textContent = agent.name || "-";
    badge.textContent = agent.enabled === false ? "已禁用" : "启用中";
    badge.classList.add(agent.enabled === false ? "bad" : "ok", "card-badge");
    meta.textContent = [
      agent.contact || "未填写联系方式",
      `分成 ${agent.ratePercent || 0}%`,
      agent.note || "",
      `更新 ${formatTime(agent.updatedAt)}`,
    ]
      .filter(Boolean)
      .join(" · ");
    edit.addEventListener("click", () => fillAgentForm(agent));
    toggle.textContent = agent.enabled === false ? "启用" : "禁用";
    toggle.addEventListener("click", () => toggleAgent(agent.id, agent.enabled === false));
    remove.addEventListener("click", () => deleteAgent(agent.id));
    els.agentList.append(fragment);
  }
}

function clearPhoneForm() {
  els.phoneForm.reset();
  els.phoneId.value = "";
  els.poolCountry.value = "+86";
  els.phoneEnabled.checked = true;
  els.phoneHint.textContent = "维护可分配手机号，批量生成卡密时可自动选择空闲号码";
}

function fillPhoneForm(phone) {
  els.phoneId.value = phone.id || "";
  els.phoneLabel.value = phone.label || "";
  els.poolCountry.value = phone.countryCode || "+86";
  els.poolPhone.value = phone.phoneNumber || "";
  els.phoneDeviceId.value = phone.deviceId || "";
  els.phoneSimNumber.value = phone.simNumber || "";
  els.phoneProvider.value = phone.provider || "";
  els.phoneNote.value = phone.note || "";
  els.phoneEnabled.checked = phone.enabled !== false;
  els.phoneHint.textContent = `正在编辑：${phone.phoneNumber}`;
}

function readPhoneForm() {
  return {
    id: els.phoneId.value.trim(),
    label: els.phoneLabel.value.trim(),
    countryCode: els.poolCountry.value.trim() || "+86",
    phoneNumber: els.poolPhone.value.trim(),
    deviceId: els.phoneDeviceId.value.trim(),
    simNumber: els.phoneSimNumber.value.trim(),
    provider: els.phoneProvider.value.trim(),
    note: els.phoneNote.value.trim(),
    enabled: els.phoneEnabled.checked,
  };
}

function renderPhoneOptions() {
  const previous = els.cardPhoneSelect.value;
  els.cardPhoneSelect.innerHTML = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = state.phones.length ? "选择号池号码" : "暂无号池号码";
  els.cardPhoneSelect.append(empty);

  for (const phone of state.phones.filter((item) => item.enabled !== false)) {
    const option = document.createElement("option");
    option.value = phone.id;
    option.textContent = `${phone.label ? `${phone.label} · ` : ""}${phone.countryCode || "+86"} ${
      phone.phoneNumber
    }`;
    els.cardPhoneSelect.append(option);
  }

  els.cardPhoneSelect.value = previous;
}

function renderPhones() {
  els.phoneList.innerHTML = "";
  els.phoneHint.textContent = `共 ${state.phones.length} 个手机号`;
  renderPhoneOptions();

  if (!state.phones.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "暂无手机号";
    els.phoneList.append(empty);
    return;
  }

  for (const phone of state.phones) {
    const fragment = els.phoneTemplate.content.cloneNode(true);
    const number = fragment.querySelector(".phone-number");
    const badge = fragment.querySelector(".phone-badge");
    const meta = fragment.querySelector(".phone-meta");
    const edit = fragment.querySelector(".edit-phone");
    const toggle = fragment.querySelector(".toggle-phone");
    const remove = fragment.querySelector(".delete-phone");

    number.textContent = `${phone.countryCode || "+86"} ${phone.phoneNumber}`;
    badge.textContent = phone.enabled === false ? "已禁用" : "可用";
    badge.classList.add(phone.enabled === false ? "bad" : "ok");
    meta.textContent = [
      phone.label || "未命名",
      phone.provider || "未填写来源",
      phone.deviceId ? `设备 ${phone.deviceId}` : "",
      phone.simNumber ? `SIM ${phone.simNumber}` : "",
      `可用卡 ${phone.activeCards || 0}`,
      `总卡 ${phone.cards || 0}`,
      phone.note || "",
    ]
      .filter(Boolean)
      .join(" · ");
    edit.addEventListener("click", () => fillPhoneForm(phone));
    toggle.textContent = phone.enabled === false ? "启用" : "禁用";
    toggle.addEventListener("click", () => togglePhone(phone.id, phone.enabled === false));
    remove.addEventListener("click", () => deletePhone(phone.id));
    els.phoneList.append(fragment);
  }
}

function clearCardForm() {
  els.cardForm.reset();
  els.cardToken.value = "";
  els.cardAssignment.value = "manual";
  els.cardPhoneSelect.value = "";
  els.cardCountry.value = "+86";
  els.cardLimit.value = String(state.settings.defaultCardReceiveLimit || 1);
  els.cardWait.value = "60";
  els.cardService.value = "腾讯视频APP";
  els.cardKeywords.value = "腾讯视频";
  els.batchCount.value = "10";
  els.cardEnabled.checked = true;
  setCardExpireMinutes(state.settings.defaultCardExpireMinutes);
  els.cardHint.textContent = "创建客户访问链接，设置手机号、过期时间和可接码次数";
}

function fillCardForm(card) {
  els.cardToken.value = card.card || "";
  els.cardAssignment.value = card.phoneId ? "selected" : "manual";
  els.cardPhoneSelect.value = card.phoneId || "";
  els.cardCountry.value = card.countryCode || "+86";
  els.cardPhone.value = card.phoneNumber || "";
  setCardExpireMinutes(closestCardExpireMinutes(remainingExpireMinutes(card.expiresAt)));
  els.cardLimit.value = card.receiveLimit ?? 1;
  els.cardWait.value = card.waitSeconds ?? 60;
  els.cardService.value = card.serviceName || "腾讯视频APP";
  els.cardKeywords.value = card.keywordsText || (card.keywords || []).join(",");
  els.cardEnabled.checked = card.enabled !== false;
  els.cardHint.textContent = `正在编辑：${card.card}`;
}

function readCardForm() {
  const expiresAtLocal = minutesFromNowLocal(normalizeCardExpireMinutes(els.cardExpireMinutes?.value));
  els.cardExpires.value = expiresAtLocal;
  return {
    card: els.cardToken.value.trim(),
    assignmentMode: els.cardAssignment.value,
    phoneId: els.cardPhoneSelect.value,
    countryCode: els.cardCountry.value.trim() || "+86",
    phoneNumber: els.cardPhone.value.trim(),
    expiresAt: fromDateTimeLocal(expiresAtLocal),
    receiveLimit: Number(els.cardLimit.value) || 0,
    waitSeconds: Number(els.cardWait.value) || 60,
    serviceName: els.cardService.value.trim() || "腾讯视频APP",
    keywordsText: els.cardKeywords.value.trim(),
    enabled: els.cardEnabled.checked,
  };
}

function readBatchForm() {
  const payload = readCardForm();
  payload.card = "";
  payload.count = Number(els.batchCount.value) || 1;
  return payload;
}

function cardBadge(card) {
  if (!card.enabled) return { text: "已禁用", kind: "bad" };
  if (card.expired) return { text: "已过期", kind: "bad" };
  if (!card.available) return { text: card.unavailableReason || "不可用", kind: "bad" };
  return { text: "可用", kind: "ok" };
}

function cardStatus(card) {
  if (!card.enabled) return "disabled";
  if (card.expired) return "expired";
  if (card.available) return "available";
  if ((Number(card.remainingCount) || 0) <= 0) return "exhausted";
  return "unavailable";
}

function filterCards() {
  const query = state.cardQuery.trim().toLowerCase();
  state.filteredCards = state.cards.filter((card) => {
    if (state.cardStatus !== "all" && cardStatus(card) !== state.cardStatus) {
      return false;
    }
    if (!query) return true;
    const haystack = [
      card.card,
      card.phoneNumber,
      card.countryCode,
      card.serviceName,
      card.keywordsText,
      card.userUrl,
      card.unavailableReason,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function renderCards() {
  filterCards();
  els.cardList.innerHTML = "";
  els.cardHint.textContent =
    state.filteredCards.length === state.cards.length
      ? `共 ${state.cards.length} 张卡密`
      : `匹配 ${state.filteredCards.length} / 共 ${state.cards.length} 张卡密`;

  if (!state.filteredCards.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.cards.length ? "没有匹配卡密" : "暂无卡密";
    els.cardList.append(empty);
    return;
  }

  for (const card of state.filteredCards) {
    const fragment = els.cardTemplate.content.cloneNode(true);
    const token = fragment.querySelector(".card-token");
    const badge = fragment.querySelector(".card-badge");
    const meta = fragment.querySelector(".card-meta");
    const link = fragment.querySelector(".card-link");
    const copyLink = fragment.querySelector(".copy-link");
    const edit = fragment.querySelector(".edit-card");
    const toggle = fragment.querySelector(".toggle-card");
    const remove = fragment.querySelector(".delete-card");
    const badgeInfo = cardBadge(card);

    token.textContent = card.card || "-";
    badge.textContent = badgeInfo.text;
    badge.classList.add(badgeInfo.kind);
    meta.textContent = [
      `${card.countryCode || "+86"} ${card.phoneNumber || "未填手机号"}`,
      `次数 ${card.usedCount || 0}/${card.receiveLimit || "未配置"}`,
      `剩余 ${card.remainingCount ?? "-"}`,
      `到期 ${formatTime(card.expiresAt)}`,
    ].join(" · ");
    link.textContent = card.userUrl || "";
    copyLink.addEventListener("click", () => copyText(card.userUrl || "", copyLink));
    edit.addEventListener("click", () => fillCardForm(card));
    toggle.textContent = card.enabled ? "禁用" : "启用";
    toggle.addEventListener("click", () => toggleCard(card.card, !card.enabled));
    remove.addEventListener("click", () => deleteCard(card.card));
    els.cardList.append(fragment);
  }
}

function stockGoods() {
  return state.goods.filter((item) => item.deliveryMode === "stock_code" && !item.builtin);
}

function clearGoodsForm() {
  if (!els.goodsForm) return;
  els.goodsForm.reset();
  els.goodsNo.value = "";
  els.goodsPrice.value = "100";
  els.goodsEnabled.checked = true;
  els.goodsNo.disabled = false;
  els.goodsHint.textContent = "维护真实卡密/兑换码库存，闲管家下单后自动扣减并发货";
}

function fillGoodsForm(goods) {
  els.goodsNo.value = goods.goodsNo || "";
  els.goodsName.value = goods.goodsName || "";
  els.goodsPrice.value = goods.priceCents ?? 0;
  els.goodsNote.value = goods.note || "";
  els.goodsEnabled.checked = goods.enabled !== false;
  els.goodsNo.disabled = true;
  els.goodsHint.textContent = `正在编辑：${goods.goodsNo}`;
}

function readGoodsForm() {
  return {
    goodsNo: els.goodsNo.value.trim(),
    goodsName: els.goodsName.value.trim(),
    priceCents: Number(els.goodsPrice.value) || 0,
    note: els.goodsNote.value.trim(),
    enabled: els.goodsEnabled.checked,
  };
}

function renderGoodsOptions() {
  const options = stockGoods();
  const previousImport = els.stockGoodsSelect?.value || "";
  const previousFilter = state.stockGoodsFilter || els.stockGoodsFilter?.value || "";

  if (els.stockGoodsSelect) {
    els.stockGoodsSelect.innerHTML = "";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = options.length ? "选择库存商品" : "暂无库存商品";
    els.stockGoodsSelect.append(empty);
    for (const goods of options) {
      const option = document.createElement("option");
      option.value = goods.goodsNo;
      option.textContent = `${goods.goodsNo} · ${goods.goodsName}`;
      els.stockGoodsSelect.append(option);
    }
    els.stockGoodsSelect.value = previousImport;
  }

  if (els.stockGoodsFilter) {
    els.stockGoodsFilter.innerHTML = "";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "全部库存";
    els.stockGoodsFilter.append(all);
    for (const goods of options) {
      const option = document.createElement("option");
      option.value = goods.goodsNo;
      option.textContent = `${goods.goodsNo} · ${goods.stockAvailable || 0}/${goods.stockTotal || 0}`;
      els.stockGoodsFilter.append(option);
    }
    els.stockGoodsFilter.value = previousFilter;
  }
}

function goodsBadge(goods) {
  if (goods.builtin) return { text: "接码链接", kind: "ok" };
  if (!goods.enabled) return { text: "已禁用", kind: "bad" };
  if ((Number(goods.stockAvailable) || 0) <= 0) return { text: "缺货", kind: "bad" };
  return { text: "可售", kind: "ok" };
}

function filterGoods() {
  const query = state.goodsQuery.trim().toLowerCase();
  state.filteredGoods = state.goods.filter((goods) => {
    if (!query) return true;
    const haystack = [goods.goodsNo, goods.goodsName, goods.note, goods.deliveryMode].join(" ").toLowerCase();
    return haystack.includes(query);
  });
}

function renderGoods() {
  if (!els.goodsList) return;
  filterGoods();
  renderGoodsOptions();
  els.goodsList.innerHTML = "";
  els.goodsHint.textContent =
    state.filteredGoods.length === state.goods.length
      ? `共 ${state.goods.length} 个商品`
      : `匹配 ${state.filteredGoods.length} / 共 ${state.goods.length} 个商品`;

  if (!state.filteredGoods.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.goods.length ? "没有匹配商品" : "暂无商品";
    els.goodsList.append(empty);
    return;
  }

  for (const goods of state.filteredGoods) {
    const fragment = els.goodsTemplate.content.cloneNode(true);
    const name = fragment.querySelector(".goods-name");
    const badge = fragment.querySelector(".goods-badge");
    const meta = fragment.querySelector(".goods-meta");
    const code = fragment.querySelector(".goods-code");
    const edit = fragment.querySelector(".edit-goods");
    const toggle = fragment.querySelector(".toggle-goods");
    const remove = fragment.querySelector(".delete-goods");
    const badgeInfo = goodsBadge(goods);

    name.textContent = goods.goodsName || goods.goodsNo;
    badge.textContent = badgeInfo.text;
    badge.classList.add(badgeInfo.kind);
    meta.textContent = [
      goods.deliveryMode === "sms_link" ? "接码链接" : "库存卡密",
      `售价 ${formatMoney(goods.priceCents)}`,
      `可用 ${goods.stockAvailable || 0}`,
      `总数 ${goods.stockTotal || 0}`,
      `已售 ${goods.stockSold || 0}`,
      goods.note || "",
    ]
      .filter(Boolean)
      .join(" · ");
    code.textContent = goods.goodsNo || "";
    edit.disabled = Boolean(goods.builtin);
    toggle.disabled = Boolean(goods.builtin);
    remove.disabled = Boolean(goods.builtin);
    edit.addEventListener("click", () => fillGoodsForm(goods));
    toggle.textContent = goods.enabled === false ? "启用" : "禁用";
    toggle.addEventListener("click", () => toggleGoods(goods.goodsNo, goods.enabled === false));
    remove.addEventListener("click", () => deleteGoods(goods.goodsNo));
    els.goodsList.append(fragment);
  }
}

function stockBadge(item) {
  if (item.status === "sold") return { text: "已售", kind: "bad" };
  if (item.status === "disabled") return { text: "已禁用", kind: "bad" };
  return { text: "可用", kind: "ok" };
}

function renderStock() {
  if (!els.stockList) return;
  els.stockList.innerHTML = "";
  if (!state.stockItems.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.stockGoodsFilter ? "该商品暂无库存记录" : "暂无库存记录";
    els.stockList.append(empty);
    return;
  }

  for (const item of state.stockItems) {
    const fragment = els.stockTemplate.content.cloneNode(true);
    const code = fragment.querySelector(".stock-code");
    const badge = fragment.querySelector(".stock-badge");
    const meta = fragment.querySelector(".stock-meta");
    const secret = fragment.querySelector(".stock-secret");
    const toggle = fragment.querySelector(".toggle-stock");
    const remove = fragment.querySelector(".delete-stock");
    const badgeInfo = stockBadge(item);

    code.textContent = item.cardNo || item.id || "库存码";
    badge.textContent = badgeInfo.text;
    badge.classList.add(badgeInfo.kind);
    meta.textContent = [
      item.goodsNo || "",
      item.orderNo ? `订单 ${item.orderNo}` : "",
      item.soldAt ? `售出 ${formatTime(item.soldAt)}` : "",
      item.note || "",
    ]
      .filter(Boolean)
      .join(" · ");
    secret.textContent = item.cardPwd || "";
    toggle.textContent = item.status === "disabled" ? "启用" : "禁用";
    toggle.disabled = item.status === "sold";
    remove.disabled = item.status === "sold";
    toggle.addEventListener("click", () => toggleStock(item.id, item.status === "disabled"));
    remove.addEventListener("click", () => deleteStock(item.id));
    els.stockList.append(fragment);
  }
}

function filterOrders() {
  const query = state.orderQuery.trim().toLowerCase();
  if (!query) {
    state.filteredOrders = state.orders;
    return;
  }
  state.filteredOrders = state.orders.filter((order) => {
    const cards = (order.cardItems || [])
      .map((item) => [item.card_no, item.card_pwd].join(" "))
      .join(" ");
    const haystack = [
      order.orderNo,
      order.outOrderNo,
      order.goodsName,
      order.statusText,
      cards,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

function orderCanReissue(order) {
  const goods = state.goods.find((item) => item.goodsNo === order.goodsNo);
  return goods && goods.deliveryMode === "stock_code";
}

function renderOrders() {
  filterOrders();
  els.orderList.innerHTML = "";
  els.ordersHint.textContent =
    state.filteredOrders.length === state.orders.length
      ? `共 ${state.orders.length} 个订单`
      : `匹配 ${state.filteredOrders.length} / 共 ${state.orders.length} 个订单`;

  if (!state.filteredOrders.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = state.orders.length ? "没有匹配订单" : "暂无订单";
    els.orderList.append(empty);
    return;
  }

  for (const order of state.filteredOrders) {
    const row = document.createElement("article");
    row.className = "order-row";

    const main = document.createElement("div");
    const title = document.createElement("div");
    title.className = "order-title";
    const orderNo = document.createElement("strong");
    orderNo.textContent = order.orderNo || "-";
    const time = document.createElement("span");
    time.textContent = order.orderTime ? formatUnixTime(order.orderTime) : formatTime(order.createdAt);
    title.append(orderNo, time);
    const meta = document.createElement("p");
    meta.className = "order-meta";
    meta.textContent = [
      order.outOrderNo ? `平台单 ${order.outOrderNo}` : "",
      order.goodsName || "",
      `数量 ${order.buyQuantity || 0}`,
      formatMoney(order.orderAmount),
    ]
      .filter(Boolean)
      .join(" · ");
    main.append(title, meta);

    const links = document.createElement("div");
    links.className = "order-links";
    const items = Array.isArray(order.cardItems) ? order.cardItems : [];
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "order-meta";
      empty.textContent = "暂无发货链接";
      links.append(empty);
    } else {
      for (const item of items) {
        const code = document.createElement("code");
        code.textContent = item.card_no
          ? `${item.card_no} · ${item.card_pwd || ""}`
          : item.card_pwd || "";
        links.append(code);
      }
    }

    const statusBox = document.createElement("div");
    statusBox.className = "card-actions";
    const status = document.createElement("span");
    status.className = `card-badge ${Number(order.orderStatus) >= 40 ? "bad" : "ok"}`;
    status.textContent = order.statusText || "已发货";
    statusBox.append(status);
    if (orderCanReissue(order)) {
      const reissue = document.createElement("button");
      reissue.type = "button";
      reissue.textContent = "补发";
      reissue.addEventListener("click", () => reissueOrder(order.orderNo));
      statusBox.append(reissue);
    }

    row.append(main, links, statusBox);
    els.orderList.append(row);
  }
}

async function loadDashboard() {
  if (!els.overviewHint) return;
  els.overviewHint.textContent = "看板读取中";
  const response = await fetch(apiUrl("/api/dashboard"), { cache: "no-store" });
  if (!response.ok) {
    els.overviewHint.textContent = `看板读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  state.dashboard = data;
  renderDashboard();
}

async function loadSystemStatus() {
  if (!els.statusHealth) return;
  els.systemStatusHint.textContent = "状态读取中";
  const [healthResponse, configResponse] = await Promise.all([
    fetch(apiUrl("/health"), { cache: "no-store" }),
    fetch(apiUrl("/api/config"), { cache: "no-store" }),
  ]);
  const health = await healthResponse.json().catch(() => ({}));
  const config = await configResponse.json().catch(() => ({}));
  if (!healthResponse.ok || !configResponse.ok) {
    els.systemStatusHint.textContent = `状态读取失败：${healthResponse.status}/${configResponse.status}`;
    return;
  }
  renderSystemStatus(health, config);
}

async function loadAuditLogs() {
  if (!els.auditLogList) return;
  els.logHint.textContent = "日志读取中";
  const response = await fetch(apiUrl("/api/audit-logs"), { cache: "no-store" });
  if (!response.ok) {
    els.logHint.textContent = `日志读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  state.auditLogs = Array.isArray(data.logs) ? data.logs : [];
  els.logHint.textContent = `最近 ${state.auditLogs.length} 条后台操作`;
  renderActivityList(els.auditLogList, state.auditLogs, "audit");
}

async function loadOrders() {
  if (!els.orderList) return;
  els.ordersHint.textContent = "订单读取中";
  const response = await fetch(apiUrl("/api/orders"), { cache: "no-store" });
  if (!response.ok) {
    els.ordersHint.textContent = `订单读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  applySettings(data.config?.cardDefaults);
  state.orders = Array.isArray(data.orders) ? data.orders : [];
  renderOrders();
}

async function loadMessages(refresh = false) {
  setSyncState(refresh ? "同步中" : "读取中");
  const url = refresh ? "/api/messages?refresh=1" : "/api/messages";
  const endpoint = apiUrl(url);
  const response = await fetch(endpoint, { cache: "no-store" });
  if (!response.ok) {
    setSyncState(`读取失败：${response.status}`, "bad");
    return;
  }
  const data = await response.json();
  state.messages = Array.isArray(data.messages) ? data.messages : [];
  setStatus(data.config || {});
  renderMessages();
}

async function addTestMessage() {
  const response = await fetch(apiUrl("/api/test-message"), { method: "POST" });
  if (response.ok) {
    await loadMessages(false);
  }
}

async function loadPhones() {
  const response = await fetch(apiUrl("/api/phones"), { cache: "no-store" });
  if (!response.ok) {
    els.phoneHint.textContent = `号池读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  applySettings(data.config?.cardDefaults);
  state.phones = Array.isArray(data.phones) ? data.phones : [];
  renderPhones();
}

async function savePhone(event) {
  event.preventDefault();
  const response = await fetch(apiUrl("/api/phones"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(readPhoneForm()),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.phoneHint.textContent = data.error || `保存失败：${response.status}`;
    return;
  }
  els.phoneHint.textContent = "手机号已保存";
  clearPhoneForm();
  await loadPhones();
}

async function togglePhone(id, enabled) {
  const response = await fetch(apiUrl("/api/phones/toggle"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, enabled }),
  });
  if (response.ok) {
    await loadPhones();
  }
}

async function deletePhone(id) {
  if (!window.confirm("删除这个手机号？已生成卡密会保留原手机号。")) return;
  const response = await fetch(apiUrl("/api/phones/delete"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  if (response.ok) {
    await loadPhones();
  }
}

async function loadCards() {
  const response = await fetch(apiUrl("/api/cards"), { cache: "no-store" });
  if (!response.ok) {
    els.cardHint.textContent = `卡密读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  applySettings(data.config?.cardDefaults);
  state.cards = Array.isArray(data.cards) ? data.cards : [];
  renderCards();
  renderMembers();
}

async function loadGoods() {
  if (!els.goodsList) return;
  els.goodsHint.textContent = "商品读取中";
  const response = await fetch(apiUrl("/api/goods"), { cache: "no-store" });
  if (!response.ok) {
    els.goodsHint.textContent = `商品读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  state.goods = Array.isArray(data.goods) ? data.goods : [];
  renderGoods();
}

async function loadStock() {
  if (!els.stockList) return;
  const query = state.stockGoodsFilter ? `?goodsNo=${encodeURIComponent(state.stockGoodsFilter)}` : "";
  const response = await fetch(apiUrl(`/api/stock${query}`), { cache: "no-store" });
  if (!response.ok) {
    els.goodsHint.textContent = `库存读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  state.stockItems = Array.isArray(data.items) ? data.items : [];
  renderStock();
}

async function loadAgents() {
  if (!els.agentList) return;
  els.agentHint.textContent = "代理读取中";
  const response = await fetch(apiUrl("/api/agents"), { cache: "no-store" });
  if (!response.ok) {
    els.agentHint.textContent = `代理读取失败：${response.status}`;
    return;
  }
  const data = await response.json();
  state.agents = Array.isArray(data.agents) ? data.agents : [];
  renderAgents();
}

async function saveAgent(event) {
  event.preventDefault();
  const response = await fetch(apiUrl("/api/agents"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(readAgentForm()),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.agentHint.textContent = data.error || `保存失败：${response.status}`;
    return;
  }
  els.agentHint.textContent = "代理已保存";
  clearAgentForm();
  await loadAgents();
  await loadAuditLogs();
}

async function toggleAgent(id, enabled) {
  const response = await fetch(apiUrl("/api/agents/toggle"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, enabled }),
  });
  if (response.ok) {
    await loadAgents();
    await loadAuditLogs();
  }
}

async function deleteAgent(id) {
  if (!window.confirm("删除这个代理？")) return;
  const response = await fetch(apiUrl("/api/agents/delete"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  if (response.ok) {
    await loadAgents();
    await loadAuditLogs();
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const payload = {
    defaultCardExpireMinutes: normalizeCardExpireMinutes(els.defaultCardExpireMinutes.value),
    defaultCardReceiveLimit: Number(els.defaultCardReceiveLimit.value) || 1,
  };
  const response = await fetch(apiUrl("/api/settings"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.settingsHint.textContent = data.error || `保存失败：${response.status}`;
    return;
  }
  applySettings(data.settings, true);
  els.settingsHint.textContent = "全局卡密设置已保存，后续新卡密和闲管家新订单将使用该默认值。";
}

async function saveGoods(event) {
  event.preventDefault();
  const response = await fetch(apiUrl("/api/goods"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(readGoodsForm()),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.goodsHint.textContent = data.error || `保存失败：${response.status}`;
    return;
  }
  els.goodsHint.textContent = "商品已保存";
  clearGoodsForm();
  await loadGoods();
  await loadStock();
}

async function toggleGoods(goodsNo, enabled) {
  const response = await fetch(apiUrl("/api/goods/toggle"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goodsNo, enabled }),
  });
  if (response.ok) {
    await loadGoods();
  }
}

async function deleteGoods(goodsNo) {
  if (!window.confirm(`删除商品 ${goodsNo}？商品有库存记录时不能删除。`)) return;
  const response = await fetch(apiUrl("/api/goods/delete"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ goodsNo }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.goodsHint.textContent = data.error || `删除失败：${response.status}`;
    return;
  }
  await loadGoods();
}

async function importStock(event) {
  event.preventDefault();
  const payload = {
    goodsNo: els.stockGoodsSelect.value,
    text: els.stockImportText.value,
    note: els.stockImportNote.value.trim(),
  };
  const response = await fetch(apiUrl("/api/stock/import"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.goodsHint.textContent = data.error || `导入失败：${response.status}`;
    return;
  }
  els.goodsHint.textContent = `已导入 ${data.count || 0} 条库存`;
  els.stockImportText.value = "";
  await loadGoods();
  state.stockGoodsFilter = payload.goodsNo;
  if (els.stockGoodsFilter) els.stockGoodsFilter.value = payload.goodsNo;
  await loadStock();
}

async function toggleStock(id, enabled) {
  const response = await fetch(apiUrl("/api/stock/toggle"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id, enabled }),
  });
  if (response.ok) {
    await loadGoods();
    await loadStock();
  }
}

async function deleteStock(id) {
  if (!window.confirm("删除这条未售库存？")) return;
  const response = await fetch(apiUrl("/api/stock/delete"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id }),
  });
  if (response.ok) {
    await loadGoods();
    await loadStock();
  }
}

async function reissueOrder(orderNo) {
  if (!window.confirm(`给订单 ${orderNo} 补发新的库存卡密？`)) return;
  const response = await fetch(apiUrl("/api/orders/reissue"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ orderNo }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.ordersHint.textContent = data.error || `补发失败：${response.status}`;
    return;
  }
  els.ordersHint.textContent = "订单已补发";
  await loadOrders();
  await loadGoods();
  await loadStock();
}

async function saveCard(event) {
  event.preventDefault();
  const response = await fetch(apiUrl("/api/cards"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(readCardForm()),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.cardHint.textContent = data.error || `保存失败：${response.status}`;
    return;
  }
  els.cardHint.textContent = "卡密已保存";
  clearCardForm();
  await loadCards();
}

async function generateBatchCards() {
  const response = await fetch(apiUrl("/api/cards/batch"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(readBatchForm()),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) {
    els.cardHint.textContent = data.error || `批量生成失败：${response.status}`;
    return;
  }
  els.cardHint.textContent = `已批量生成 ${data.count || 0} 张卡密`;
  clearCardForm();
  await loadCards();
}

function exportCards(format) {
  window.location.href = apiUrl(`/api/cards/export?format=${format}&scope=available`);
}

async function logout() {
  const path = `${basePath()}/logout`;
  window.location.replace(`${window.location.protocol}//logout:logout@${window.location.host}${path}`);
}

async function toggleCard(card, enabled) {
  const response = await fetch(apiUrl("/api/cards/toggle"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card, enabled }),
  });
  if (response.ok) {
    await loadCards();
  }
}

async function deleteCard(card) {
  if (!window.confirm(`删除卡密 ${card}？`)) return;
  const response = await fetch(apiUrl("/api/cards/delete"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card }),
  });
  if (response.ok) {
    await loadCards();
  }
}

els.refresh.addEventListener("click", () => loadMessages(true));
els.test.addEventListener("click", addTestMessage);
els.refreshDashboard.addEventListener("click", loadDashboard);
if (els.refreshSystemStatus) {
  els.refreshSystemStatus.addEventListener("click", loadSystemStatus);
}
els.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderMessages();
});
if (els.memberSearch) {
  els.memberSearch.addEventListener("input", (event) => {
    state.memberQuery = event.target.value;
    renderMembers();
  });
}
if (els.memberNewCard) {
  els.memberNewCard.addEventListener("click", () => {
    showView("cards");
    clearCardForm();
  });
}
els.cardSearch.addEventListener("input", (event) => {
  state.cardQuery = event.target.value;
  renderCards();
});
els.cardStatusFilter.addEventListener("change", (event) => {
  state.cardStatus = event.target.value;
  renderCards();
});
if (els.cardExpireMinutes) {
  els.cardExpireMinutes.addEventListener("change", (event) => setCardExpireMinutes(event.target.value));
}
if (els.goodsSearch) {
  els.goodsSearch.addEventListener("input", (event) => {
    state.goodsQuery = event.target.value;
    renderGoods();
  });
}
if (els.stockGoodsFilter) {
  els.stockGoodsFilter.addEventListener("change", async (event) => {
    state.stockGoodsFilter = event.target.value;
    await loadStock();
  });
}
els.refreshOrders.addEventListener("click", loadOrders);
els.orderSearch.addEventListener("input", (event) => {
  state.orderQuery = event.target.value;
  renderOrders();
});
els.phoneForm.addEventListener("submit", savePhone);
els.newPhone.addEventListener("click", clearPhoneForm);
els.clearPhone.addEventListener("click", clearPhoneForm);
els.cardForm.addEventListener("submit", saveCard);
els.newCard.addEventListener("click", clearCardForm);
els.clearCard.addEventListener("click", clearCardForm);
els.batchGenerate.addEventListener("click", generateBatchCards);
els.exportTxt.addEventListener("click", () => exportCards("txt"));
els.exportCsv.addEventListener("click", () => exportCards("csv"));
if (els.goodsForm) {
  els.goodsForm.addEventListener("submit", saveGoods);
  els.newGoods.addEventListener("click", clearGoodsForm);
  els.clearGoods.addEventListener("click", clearGoodsForm);
}
if (els.stockImportForm) {
  els.stockImportForm.addEventListener("submit", importStock);
}
if (els.agentForm) {
  els.agentForm.addEventListener("submit", saveAgent);
  els.newAgent.addEventListener("click", clearAgentForm);
  els.clearAgent.addEventListener("click", clearAgentForm);
}
if (els.refreshLogs) {
  els.refreshLogs.addEventListener("click", loadAuditLogs);
}
if (els.logout) {
  els.logout.addEventListener("click", logout);
}
for (const item of els.menuItems) {
  item.addEventListener("click", () => showView(item.dataset.view));
}
window.addEventListener("hashchange", () => showView(viewFromHash(), false));
if (els.copyGateway) {
  els.copyGateway.addEventListener("click", () => {
    const url = `${window.location.origin}${basePath()}/api/xianguanjia`;
    copyText(url, els.copyGateway);
  });
}
if (els.settingsForm) {
  els.settingsForm.addEventListener("submit", saveSettings);
}

showView(viewFromHash(), false);
loadDashboard();
loadSystemStatus();
loadAuditLogs();
loadMessages(false);
loadPhones().then(loadCards);
loadGoods().then(loadStock).then(loadOrders);
loadAgents();
setInterval(() => loadMessages(false), 5000);
