const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };

function handleUnauthorized() {
  // Clear persisted auth state and redirect to login
  if (typeof window !== "undefined") {
    localStorage.removeItem("cookit-auth");
    window.location.href = "/login";
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    handleUnauthorized();
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = (errorData as { detail?: string }).detail;
    throw new Error(detail ?? res.statusText);
  }

  if (res.status === 204) {
    return undefined as unknown as T;
  }

  return res.json() as Promise<T>;
}

export const api = {
  get<T>(path: string, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "GET" });
  },

  post<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "POST", body });
  },

  async postForm<T>(path: string, formData: FormData): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      credentials: "include",
      body: formData,
    });

    if (res.status === 401) {
      handleUnauthorized();
      throw new Error("Session expired. Please log in again.");
    }

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: res.statusText }));
      const detail = (errorData as { detail?: string }).detail;
      throw new Error(detail ?? res.statusText);
    }

    return res.json() as Promise<T>;
  },

  patch<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "PATCH", body });
  },

  del<T>(path: string, options?: Omit<RequestOptions, "method" | "body">) {
    return request<T>(path, { ...options, method: "DELETE" });
  },
};
