import translationsData from "./i18n.json";

export type Locale = "en" | "hi" | "pa" | "mr" | "te" | "ta" | "bn" | "gu" | "kn";

export interface LanguageInfo {
  code: Locale;
  label: string;
  nativeLabel: string;
  region: string;
  voiceLang: string;
}

export const SUPPORTED_LANGUAGES: LanguageInfo[] = [
  { code: "en", label: "English", nativeLabel: "English", region: "National / Default", voiceLang: "en-IN" },
  { code: "hi", label: "Hindi", nativeLabel: "हिन्दी", region: "UP, MP, Bihar, RJ, HR", voiceLang: "hi-IN" },
  { code: "pa", label: "Punjabi", nativeLabel: "ਪੰਜਾਬੀ", region: "Punjab, Haryana", voiceLang: "pa-IN" },
  { code: "mr", label: "Marathi", nativeLabel: "मराठी", region: "Maharashtra", voiceLang: "mr-IN" },
  { code: "te", label: "Telugu", nativeLabel: "తెలుగు", region: "AP, Telangana", voiceLang: "te-IN" },
  { code: "ta", label: "Tamil", nativeLabel: "தமிழ்", region: "Tamil Nadu", voiceLang: "ta-IN" },
  { code: "bn", label: "Bengali", nativeLabel: "বাংলা", region: "West Bengal, Assam", voiceLang: "bn-IN" },
  { code: "gu", label: "Gujarati", nativeLabel: "ગુજરાતી", region: "Gujarat", voiceLang: "gu-IN" },
  { code: "kn", label: "Kannada", nativeLabel: "ಕನ್ನಡ", region: "Karnataka", voiceLang: "kn-IN" },
];

export const translations: Record<string, Record<string, string>> = translationsData as Record<string, Record<string, string>>;

export function t(locale: Locale, key: string): string {
  return translations[locale]?.[key] ?? translations["en"]?.[key] ?? key;
}
