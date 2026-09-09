const PATIENCE_MESSAGE =
  "Thanks for your patience — I'm still working on that for you.";
const PATIENCE_DELAY_MS = 5000;

const transcript = document.getElementById("transcript");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message");
const sendButton = document.getElementById("send");
const newChatButton = document.getElementById("new-chat");

let sessionId = null;
let busy = false;
let patienceTimer = null;
let typingEl = null;
let waitToken = 0;

function renderMarkdown(text) {
  if (typeof marked !== "undefined" && typeof marked.parse === "function") {
    return marked.parse(text, { breaks: true, gfm: true });
  }
  const escaped = text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
  return escaped.replaceAll("\n", "<br>");
}

function appendBubble(role, text, { extraClass = "", markdown = false } = {}) {
  const el = document.createElement("div");
  el.className = `bubble ${role}${extraClass ? ` ${extraClass}` : ""}`;
  if (markdown && role === "assistant") {
    el.classList.add("markdown");
    el.innerHTML = renderMarkdown(text);
  } else {
    el.textContent = text;
  }
  transcript.appendChild(el);
  transcript.scrollTop = transcript.scrollHeight;
  return el;
}

function showTyping() {
  clearTyping();
  typingEl = document.createElement("div");
  typingEl.className = "bubble assistant";
  typingEl.setAttribute("aria-label", "Sunny is typing");
  typingEl.innerHTML =
    '<div class="typing" aria-hidden="true"><span></span><span></span><span></span></div>';
  transcript.appendChild(typingEl);
  transcript.scrollTop = transcript.scrollHeight;
}

function clearTyping() {
  if (typingEl) {
    typingEl.remove();
    typingEl = null;
  }
}

function clearPatienceTimer() {
  if (patienceTimer !== null) {
    window.clearTimeout(patienceTimer);
    patienceTimer = null;
  }
}

function setBusy(next) {
  busy = next;
  messageInput.disabled = next;
  sendButton.disabled = next;
}

async function createSession() {
  const res = await fetch("/api/session", { method: "POST" });
  if (!res.ok) {
    throw new Error("Could not start a chat session.");
  }
  const data = await res.json();
  sessionId = data.session_id;
  transcript.replaceChildren();
  appendBubble("assistant", data.welcome);
}

async function startNewChat() {
  waitToken += 1;
  clearPatienceTimer();
  clearTyping();
  setBusy(true);
  try {
    await createSession();
  } catch (err) {
    appendBubble(
      "assistant",
      err instanceof Error ? err.message : "Something went wrong when starting the chat.",
    );
  } finally {
    setBusy(false);
    messageInput.focus();
  }
}

function schedulePatience(token) {
  clearPatienceTimer();
  const startedAt = Date.now();
  patienceTimer = window.setTimeout(() => {
    patienceTimer = null;
    // Only show after a configured wait, and only if this turn is still pending.
    if (token !== waitToken || !busy) return;
    if (Date.now() - startedAt < PATIENCE_DELAY_MS) return;

    clearTyping();
    appendBubble("assistant", PATIENCE_MESSAGE, { extraClass: "patience" });
    showTyping();
  }, PATIENCE_DELAY_MS);
}

async function sendMessage(text) {
  if (!sessionId || busy) return;

  const token = ++waitToken;
  appendBubble("user", text);
  messageInput.value = "";
  messageInput.style.height = "auto";
  setBusy(true);
  showTyping();
  schedulePatience(token);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });

    if (token !== waitToken) return;

    clearPatienceTimer();
    clearTyping();

    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      throw new Error(detail?.detail || "Sorry — I couldn't complete that request.");
    }

    const data = await res.json();

    if (data.outcome === "reset" || data.outcome === "exit") {
      if (data.reply) {
        appendBubble("assistant", data.reply, { markdown: true });
      }
      const sessionRes = await fetch("/api/session", { method: "POST" });
      if (!sessionRes.ok) {
        throw new Error("Could not start a new conversation.");
      }
      const session = await sessionRes.json();
      sessionId = session.session_id;
      appendBubble("assistant", session.welcome);
      return;
    }

    if (data.reply) {
      appendBubble("assistant", data.reply, { markdown: true });
    }
  } catch (err) {
    if (token !== waitToken) return;
    clearPatienceTimer();
    clearTyping();
    appendBubble(
      "assistant",
      err instanceof Error ? err.message : "Sorry — something went wrong.",
    );
  } finally {
    if (token === waitToken) {
      setBusy(false);
      messageInput.focus();
    }
  }
}

composer.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  void sendMessage(text);
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    composer.requestSubmit();
  }
});

messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 128)}px`;
});

newChatButton.addEventListener("click", () => {
  void startNewChat();
});

void startNewChat();
