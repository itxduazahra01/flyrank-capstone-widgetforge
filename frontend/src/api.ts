export type LoginResponse = { access_token: string; token_type: string };

const TOKEN_KEY = "widgetforge_access_token";
const SESSION_EVENT = "widgetforge-session-changed";

function notifySessionChange() {
  window.dispatchEvent(new Event(SESSION_EVENT));
}

export const session = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => {
    sessionStorage.setItem(TOKEN_KEY, token);
    notifySessionChange();
  },
  clear: () => {
    sessionStorage.removeItem(TOKEN_KEY);
    notifySessionChange();
  },
};

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) throw new Error("The email or password is incorrect.");
  return response.json();
}

export async function api<T>(path: string): Promise<T> {
  return request<T>(path);
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = session.get();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    session.clear();
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!response.ok) throw new Error("We could not load this information. Please try again.");
  return response.json();
}

export async function downloadCsv(path: string): Promise<Blob> {
  const token = session.get();
  const response = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (response.status === 401) {
    session.clear();
    throw new Error("Your session has expired. Please sign in again.");
  }
  if (!response.ok) throw new Error("We could not prepare that export. Please try again.");
  return response.blob();
}
