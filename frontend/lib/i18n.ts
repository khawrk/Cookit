import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "@/public/locales/en.json";
import th from "@/public/locales/th.json";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    th: { translation: th },
  },
  lng: "en",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false, // React already escapes
  },
});

export default i18n;
