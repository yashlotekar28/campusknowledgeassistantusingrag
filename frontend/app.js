let currentScope = "all";
let isSending = false;

// Check API key status on page load
window.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    const banner = document.getElementById("key-warning-banner");
    if (banner) {
      if (data.has_api_key) {
        banner.classList.add("hidden");
      } else {
        banner.classList.remove("hidden");
      }
    }
  } catch (e) {}
});

function openSettingsModal() {
  const modal = document.getElementById("settings-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeSettingsModal() {
  const modal = document.getElementById("settings-modal");
  if (modal) modal.classList.add("hidden");
}

async function saveApiKey() {
  const input = document.getElementById("api-key-input");
  const key = input.value.trim();
  const status = document.getElementById("modal-status");

  if (!key) {
    status.className = "text-xs text-red-500 font-medium block";
    status.textContent = "Please enter a valid API key.";
    return;
  }

  status.className = "text-xs text-blue-600 font-medium block";
  status.textContent = "Saving and validating API key...";

  try {
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gemini_api_key: key }),
    });

    const data = await res.json();
    if (res.ok) {
      status.className = "text-xs text-emerald-600 font-medium block";
      status.textContent = "✓ Key saved successfully! Gemini answers are now active.";
      const banner = document.getElementById("key-warning-banner");
      if (banner) banner.classList.add("hidden");
      setTimeout(() => closeSettingsModal(), 1500);
    } else {
      status.className = "text-xs text-red-500 font-medium block";
      status.textContent = `✗ Error: ${data.detail || "Failed to save key."}`;
    }
  } catch (err) {
    status.className = "text-xs text-red-500 font-medium block";
    status.textContent = "✗ Network error connecting to server.";
  }
}

function setScope(scope) {
  currentScope = scope;
  document.querySelectorAll(".scope-btn").forEach((btn) => {
    btn.classList.remove("bg-white", "text-blue-900", "shadow-sm");
    btn.classList.add("text-slate-600");
  });

  const activeBtn = document.getElementById(`scope-${scope}`);
  if (activeBtn) {
    activeBtn.classList.add("bg-white", "text-blue-900", "shadow-sm");
    activeBtn.classList.remove("text-slate-600");
  }

  const indicator = document.getElementById("scope-indicator");
  if (indicator) {
    indicator.textContent = scope === "all" ? "ALL SOURCES" : `${scope} DOCS`;
  }
}

function askExample(question) {
  const input = document.getElementById("query-input");
  input.value = question;
  document.getElementById("chat-form").dispatchEvent(new Event("submit"));
}

async function handleSend(e) {
  e.preventDefault();
  const input = document.getElementById("query-input");
  const query = input.value.trim();
  if (!query || isSending) return;

  isSending = true;
  input.value = "";
  document.getElementById("send-btn").disabled = true;

  // Add User Message to UI
  appendUserMessage(query);

  // Add Assistant Loading Placeholder
  const loadingId = appendLoadingMessage();

  try {
    const res = await fetch("/api/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: query, scope: currentScope, top_k: 3 }),
    });

    const data = await res.json();
    removeMessage(loadingId);

    if (res.ok) {
      appendAssistantMessage(data.answer, data.sources, data.response_time);
    } else {
      appendAssistantMessage(`⚠️ Error: ${data.detail || "Failed to retrieve response."}`);
    }
  } catch (err) {
    removeMessage(loadingId);
    appendAssistantMessage(`⚠️ Network Error: Could not reach the assistant server.`);
  } finally {
    isSending = false;
    document.getElementById("send-btn").disabled = false;
    scrollToBottom();
  }
}

function appendUserMessage(text) {
  const list = document.getElementById("messages-list");
  const div = document.createElement("div");
  div.className = "flex justify-end";
  div.innerHTML = `
    <div class="max-w-2xl bg-blue-600 text-white rounded-2xl rounded-tr-sm px-5 py-3 shadow-sm text-sm">
      <p class="leading-relaxed whitespace-pre-wrap">${escapeHtml(text)}</p>
      <span class="block text-[10px] text-blue-200 mt-1 text-right">${getCurrentTime()}</span>
    </div>
  `;
  list.appendChild(div);
  scrollToBottom();
}

function appendLoadingMessage() {
  const list = document.getElementById("messages-list");
  const id = `loading-${Date.now()}`;
  const div = document.createElement("div");
  div.id = id;
  div.className = "flex items-start space-x-3";
  div.innerHTML = `
    <div class="w-8 h-8 rounded-full bg-blue-900 text-white flex items-center justify-center font-bold text-xs shrink-0">
      <i class="ph-bold ph-robot text-sm"></i>
    </div>
    <div class="bg-slate-100 rounded-2xl rounded-tl-sm px-5 py-3.5 shadow-sm text-sm text-slate-600 flex items-center space-x-2">
      <span class="inline-block w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
      <span class="inline-block w-2 h-2 rounded-full bg-indigo-600 animate-pulse" style="animation-delay: 0.2s"></span>
      <span class="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" style="animation-delay: 0.4s"></span>
      <span class="text-xs text-slate-500 font-medium ml-1">Searching campus documents & reasoning...</span>
    </div>
  `;
  list.appendChild(div);
  scrollToBottom();
  return id;
}

function appendAssistantMessage(answerText, sources = [], responseTime = null) {
  const list = document.getElementById("messages-list");
  const div = document.createElement("div");
  div.className = "flex items-start space-x-3";

  // Parse markdown tables or basic formatting
  const formattedAnswer = formatMarkdown(answerText);

  // Build Source Cards
  let sourcesHtml = "";
  if (sources && sources.length > 0) {
    sourcesHtml = `
      <div class="mt-4 pt-3 border-t border-slate-200/80">
        <h5 class="text-xs font-bold text-slate-700 flex items-center space-x-1 mb-2">
          <i class="ph-bold ph-bookmark-simple text-blue-600"></i>
          <span>Sources & Page Citations</span>
        </h5>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
          ${sources
            .map(
              (s) => `
            <div class="bg-white border border-slate-200 rounded-xl p-2.5 flex items-start justify-between shadow-xs hover:border-blue-400 transition">
              <div class="overflow-hidden pr-2">
                <div class="flex items-center space-x-1.5 text-xs font-semibold text-slate-800 truncate">
                  <i class="ph-bold ph-file-pdf text-red-500"></i>
                  <span class="truncate" title="${escapeHtml(s.source)}">${escapeHtml(s.source)}</span>
                </div>
                <p class="text-[11px] text-slate-500 mt-0.5">Page ${s.page_number} &bull; <span class="capitalize text-blue-600">${s.doc_scope}</span></p>
              </div>
              <button onclick="previewSnippet('${escapeHtml(s.source)}', ${s.page_number}, '${escapeHtml(s.snippet || "")}')" class="text-[11px] text-blue-600 hover:text-blue-800 font-medium whitespace-nowrap flex items-center space-x-0.5">
                <span>View</span>
                <i class="ph-bold ph-arrow-up-right"></i>
              </button>
            </div>
          `
            )
            .join("")}
        </div>
      </div>
    `;
  }

  const timeNotice = responseTime
    ? `<span class="text-[10px] text-slate-400 ml-2">&bull; ${responseTime}s</span>`
    : "";

  div.innerHTML = `
    <div class="w-8 h-8 rounded-full bg-blue-900 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
      <i class="ph-bold ph-robot text-sm"></i>
    </div>
    <div class="max-w-3xl bg-slate-50 border border-slate-200/80 rounded-2xl rounded-tl-sm p-4 shadow-sm text-sm text-slate-800">
      <div class="prose prose-sm max-w-none text-slate-800 leading-relaxed">${formattedAnswer}</div>
      ${sourcesHtml}
      <div class="flex items-center justify-between text-[10px] text-slate-400 mt-2">
        <span>MIT AOE AI Verified${timeNotice}</span>
        <span>${getCurrentTime()}</span>
      </div>
    </div>
  `;
  list.appendChild(div);
  scrollToBottom();
}

function removeMessage(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollToBottom() {
  const container = document.getElementById("chat-container");
  container.scrollTop = container.scrollHeight;
}

function getCurrentTime() {
  const d = new Date();
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  // Markdown Tables
  const lines = html.split("\n");
  let inTable = false;
  let tableHtml = "";
  let resLines = [];

  for (let line of lines) {
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      if (!inTable) {
        inTable = true;
        tableHtml = "<div class='overflow-x-auto my-3'><table class='min-w-full text-xs text-left border border-slate-200 rounded-lg overflow-hidden'><thead class='bg-slate-100 font-semibold text-slate-700'>";
        const cols = line.split("|").filter((c, i, a) => i !== 0 && i !== a.length - 1);
        tableHtml += "<tr>" + cols.map((c) => `<th class='p-2 border-b'>${c.trim()}</th>`).join("") + "</tr></thead><tbody class='divide-y divide-slate-100'>";
      } else if (line.includes("---")) {
        // Divider row, skip
      } else {
        const cols = line.split("|").filter((c, i, a) => i !== 0 && i !== a.length - 1);
        tableHtml += "<tr>" + cols.map((c) => `<td class='p-2'>${c.trim()}</td>`).join("") + "</tr>";
      }
    } else {
      if (inTable) {
        inTable = false;
        tableHtml += "</tbody></table></div>";
        resLines.push(tableHtml);
      }
      resLines.push(line);
    }
  }
  if (inTable) {
    tableHtml += "</tbody></table></div>";
    resLines.push(tableHtml);
  }

  html = resLines.join("<br/>");
  return html;
}

async function uploadFile(file) {
  if (!file) return;
  const statusEl = document.getElementById("upload-status");
  statusEl.classList.remove("hidden");
  statusEl.innerHTML = `<span class="text-blue-600 font-medium">Uploading & indexing ${escapeHtml(file.name)}...</span>`;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("scope", "personal");

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (res.ok) {
      statusEl.innerHTML = `<span class="text-emerald-600 font-medium">✓ Indexed ${data.details.chunks_created} chunks from ${escapeHtml(file.name)}!</span>`;
      setTimeout(() => statusEl.classList.add("hidden"), 5000);
    } else {
      statusEl.innerHTML = `<span class="text-red-500 font-medium">✗ Upload failed: ${data.detail}</span>`;
    }
  } catch (err) {
    statusEl.innerHTML = `<span class="text-red-500 font-medium">✗ Error uploading document.</span>`;
  }
}

function previewSnippet(source, page, snippet) {
  alert(`Source: ${source}\nPage: ${page}\n\nRetrieved Content:\n${snippet}`);
}

function switchTab(tab) {
  alert(`Switched to: ${tab}`);
}
