const API_BASE_URL = import.meta.env.VITE_API_URL || ""

export function getApiBaseUrl(): string {
  return API_BASE_URL
}

export function getAuthToken(): string | null {
  return localStorage.getItem("auth_token")
}

export function setAuthToken(token: string): void {
  localStorage.setItem("auth_token", token)
}

export function clearAuthToken(): void {
  localStorage.removeItem("auth_token")
}

export async function apiFetch(
  endpoint: string,
  init?: RequestInit
): Promise<Response> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  }

  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json"
  }

  const token = getAuthToken()
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  return fetch(`${API_BASE_URL}${endpoint}`, {
    ...init,
    headers,
  })
}
