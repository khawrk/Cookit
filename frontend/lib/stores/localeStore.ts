"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

type Locale = "en" | "th";

interface LocaleState {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      locale: "en",
      setLocale: (locale) => set({ locale }),
    }),
    { name: "cookit-locale" }
  )
);
