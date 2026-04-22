import { useMutation } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/authStore";
import type { LoginPayload, RegisterPayload, Token, User } from "@/types/auth";

export function useLogin() {
  const setUser = useAuthStore((s) => s.setUser);
  return useMutation({
    mutationFn: (payload: LoginPayload) => api.post<Token>("/api/auth/login", payload),
    onSuccess: async (data) => {
      // Store token for mobile browsers where cross-origin httpOnly cookies are blocked
      localStorage.setItem("cookit-token", data.access_token);
      const user = await api.get<User>("/api/auth/me").catch(() => null);
      if (user) setUser(user);
    },
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: (payload: RegisterPayload) => api.post<User>("/api/auth/register", payload),
  });
}

export function useLogout() {
  const clearUser = useAuthStore((s) => s.clearUser);
  return useMutation({
    mutationFn: () => api.post<void>("/api/auth/logout"),
    onSuccess: () => {
      localStorage.removeItem("cookit-token");
      clearUser();
    },
  });
}
