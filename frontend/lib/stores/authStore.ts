import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/types/auth";

interface AuthState {
  user: User | null;
  setUser: (user: User) => void;
  clearUser: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      setUser: (user) => set({ user }),
      clearUser: () => set({ user: null }),
    }),
    { name: "cookit-auth" }
  )
);
