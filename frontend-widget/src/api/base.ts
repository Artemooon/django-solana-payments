function getCookie(name: string) {
  if (!document.cookie) {
    return null;
  }

  const cookie = document.cookie
    .split(";")
    .map((chunk) => chunk.trim())
    .find((chunk) => chunk.startsWith(`${name}=`));

  if (!cookie) {
    return null;
  }

  return decodeURIComponent(cookie.slice(name.length + 1));
}

function getCsrfHeaders(url: string, init?: RequestInit) {
  const method = (init?.method || "GET").toUpperCase();
  if (["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    return {};
  }

  const requestUrl = new URL(url, window.location.origin);
  if (requestUrl.origin !== window.location.origin) {
    return {};
  }

  const csrfToken = getCookie("csrftoken");
  if (!csrfToken) {
    return {};
  }

  return {
    "X-CSRFToken": csrfToken,
  };
}

function getApiErrorMessage(payload: unknown, fallbackMessage: string) {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }

  return fallbackMessage;
}

export function buildApiUrl(baseUrl: string, path: string) {
  const normalizedBaseUrl = baseUrl.endsWith("/") ? baseUrl : `${baseUrl}/`;
  const rootUrl = new URL(normalizedBaseUrl, window.location.origin);
  return new URL(path, rootUrl).toString();
}

export function getApiListPayload<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) {
    return payload as T[];
  }

  if (
    payload &&
    typeof payload === "object" &&
    "results" in payload &&
    Array.isArray(payload.results)
  ) {
    return payload.results as T[];
  }

  throw new Error("Expected list response from payment tokens endpoint.");
}

export async function fetchApiJson(url: string, init?: RequestInit) {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");

  if (init?.body) {
    headers.set("Content-Type", "application/json");
  }

  for (const [key, value] of Object.entries(getCsrfHeaders(url, init))) {
    headers.set(key, value);
  }

  const response = await fetch(url, {
    credentials: "same-origin",
    ...init,
    headers,
  });

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload, "Payment API request failed."));
  }

  return payload;
}
