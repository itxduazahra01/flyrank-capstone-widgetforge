(() => {
  const script = document.currentScript;
  const widgetId = new URL(script.src).searchParams.get("id");
  if (!widgetId) return;

  const apiBase = new URL(script.src).origin;
  const root = document.createElement("section");
  root.className = "wf-root";
  root.dataset.widgetforgeRoot = widgetId;
  root.setAttribute("aria-live", "polite");
  script.insertAdjacentElement("afterend", root);

  if (!document.getElementById("wf-styles")) {
    const style = document.createElement("style");
    style.id = "wf-styles";
    style.textContent = `.wf-root{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;max-width:430px}.wf-card{box-sizing:border-box;background:#fff;border:1px solid #d8dee8;border-radius:12px;padding:24px;box-shadow:0 4px 14px rgba(23,32,51,.07)}.wf-title{font-size:20px;line-height:1.25;letter-spacing:-.02em;margin:0 0 7px}.wf-description{color:#667085;line-height:1.5;margin:0 0 20px;font-size:14px}.wf-form{display:grid;gap:15px}.wf-label{display:grid;gap:6px;color:#344054;font-size:14px;font-weight:650}.wf-input{box-sizing:border-box;width:100%;border:1px solid #c9d2df;border-radius:7px;padding:10px 11px;font:inherit;color:#172033;background:#fff}.wf-input:focus{outline:3px solid #dce4ff;border-color:#4055a8}.wf-input[aria-invalid="true"]{border-color:#b42318}.wf-field-error{color:#b42318;font-size:12px;font-weight:500}.wf-button{border:0;border-radius:7px;background:#4055a8;color:#fff;padding:11px 14px;font:inherit;font-weight:650;cursor:pointer}.wf-button:hover{background:#32458f}.wf-button:disabled{opacity:.65;cursor:wait}.wf-message{margin:0;color:#667085;font-size:14px;line-height:1.45}.wf-message--error{color:#b42318}.wf-success{padding:8px 0}.wf-success h3{margin:0 0 7px;font-size:20px}.wf-honeypot{position:absolute!important;left:-10000px!important;opacity:0!important;pointer-events:none!important}`;
    document.head.append(style);
  }

  function message(text, type = "") {
    const node = document.createElement("p");
    node.className = `wf-message ${type ? `wf-message--${type}` : ""}`;
    node.textContent = text;
    return node;
  }

  function createKey() {
    return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
  }

  function analyticsSession() {
    const key = `widgetforge-session-${widgetId}`;
    try {
      const existing = sessionStorage.getItem(key);
      if (existing) return existing;
      const created = createKey(); sessionStorage.setItem(key, created); return created;
    } catch (_) { return createKey(); }
  }

  const sessionId = analyticsSession();
  function track(eventType) {
    fetch(`${apiBase}/public/v1/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ widget_id: widgetId, event_type: eventType, session_id: sessionId }),
      keepalive: true,
    }).catch(() => {});
  }

  fetch(`${apiBase}/public/v1/widgets/${widgetId}/config`)
    .then(response => response.ok ? response.json() : Promise.reject())
    .then(config => {
      track("widget_viewed");
      const card = document.createElement("div"); card.className = "wf-card";
      const appearance = config.display_options || {};
      card.style.borderRadius = `${appearance.border_radius ?? 8}px`;
      const title = document.createElement("h2"); title.className = "wf-title"; title.textContent = config.title; card.append(title);
      if (config.description) { const description = document.createElement("p"); description.className = "wf-description"; description.textContent = config.description; card.append(description); }
      const form = document.createElement("form"); form.className = "wf-form"; form.noValidate = true;
      const fields = new Map();
      config.form_fields.forEach(definition => {
        const label = document.createElement("label"); label.className = "wf-label"; label.textContent = definition.label;
        const input = document.createElement("input"); input.className = "wf-input"; input.name = definition.name; input.type = definition.type; input.required = definition.required; input.maxLength = definition.max_length; input.autocomplete = definition.type === "email" ? "email" : "name";
        const error = document.createElement("span"); error.className = "wf-field-error"; error.hidden = true; error.id = `wf-error-${definition.name}`; input.setAttribute("aria-describedby", error.id);
        label.append(input, error); form.append(label); fields.set(definition.name, { definition, input, error });
      });
      const honeypot = document.createElement("input"); honeypot.className = "wf-honeypot"; honeypot.name = "website"; honeypot.tabIndex = -1; honeypot.autocomplete = "off"; honeypot.setAttribute("aria-hidden", "true"); form.append(honeypot);
      const button = document.createElement("button"); button.className = "wf-button"; button.type = "submit"; button.textContent = config.button_text; button.style.background = appearance.primary_color || "#2457E6"; form.append(button);
      const feedback = message(""); feedback.hidden = true; form.append(feedback); card.append(form); root.replaceChildren(card);
      let idempotencyKey = createKey();
      form.addEventListener("input", () => track("form_started"), { once: true });
      function validate() {
        let firstInvalid = null; let valid = true;
        fields.forEach(({ definition, input, error }) => { let text = ""; if (definition.required && !input.value.trim()) text = "This field is required."; else if (definition.type === "email" && input.value && !input.validity.valid) text = "Enter a valid email address."; error.textContent = text; error.hidden = !text; input.setAttribute("aria-invalid", String(Boolean(text))); if (text && !firstInvalid) firstInvalid = input; valid = valid && !text; });
        if (firstInvalid) firstInvalid.focus(); return valid;
      }
      form.addEventListener("submit", async event => {
        event.preventDefault(); if (!validate()) return; button.disabled = true; button.textContent = "Sending…"; feedback.hidden = true;
        const payload = {}; fields.forEach(({ input }, name) => { payload[name] = input.value.trim(); });
        try {
          const response = await fetch(`${apiBase}/public/v1/submissions`, { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey }, body: JSON.stringify({ widget_id: widgetId, fields: payload, website: honeypot.value }) });
          if (response.ok) { const success = document.createElement("div"); success.className = "wf-success"; const heading = document.createElement("h3"); heading.textContent = "Thank you"; success.append(heading, message(appearance.success_message || "Your submission was received.")); card.replaceChildren(success); return; }
          feedback.textContent = response.status === 429 ? "Too many attempts. Please wait a moment and try again." : "Please check your details and try again."; feedback.className = "wf-message wf-message--error"; feedback.hidden = false;
        } catch (_) { feedback.textContent = "We could not send your submission. Please try again shortly."; feedback.className = "wf-message wf-message--error"; feedback.hidden = false; }
        button.disabled = false; button.textContent = config.button_text; idempotencyKey = createKey();
      });
    })
    .catch(() => root.replaceChildren(message("This form is unavailable right now.", "error")));
})();
