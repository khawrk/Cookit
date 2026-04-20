"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useLogin, useRegister } from "@/lib/hooks/useAuth";

export default function LoginPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loginMutation = useLogin();
  const registerMutation = useRegister();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (mode === "login") {
        await loginMutation.mutateAsync({ email, password });
      } else {
        await registerMutation.mutateAsync({ email, password, name: name || undefined });
      }
      router.push("/fridge");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("login.somethingWentWrong"));
    }
  }

  const isLoading = loginMutation.isPending || registerMutation.isPending;

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Brand mark */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🥦</div>
          <h1 className="text-2xl font-bold text-slate-900">{t("nav.brand")}</h1>
          <p className="text-slate-500 text-sm mt-1">
            {mode === "login" ? t("login.signInSubtitle") : t("login.registerSubtitle")}
          </p>
        </div>

        <Card>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {mode === "register" && (
              <Input
                label={t("login.nameLabel")}
                id="name"
                type="text"
                placeholder={t("login.namePlaceholder")}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            )}
            <Input
              label={t("login.emailLabel")}
              id="email"
              type="email"
              placeholder={t("login.emailPlaceholder")}
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Input
              label={t("login.passwordLabel")}
              id="password"
              type="password"
              placeholder="••••••••"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <Button type="submit" loading={isLoading} className="w-full mt-1">
              {mode === "login" ? t("login.signInButton") : t("login.createAccountButton")}
            </Button>
          </form>

          <p className="mt-5 text-center text-sm text-slate-500">
            {mode === "login" ? t("login.noAccount") : t("login.alreadyHaveAccount")}{" "}
            <button
              type="button"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}
              className="text-green-600 hover:underline font-medium"
            >
              {mode === "login" ? t("login.registerLink") : t("login.signInButton")}
            </button>
          </p>
        </Card>
      </div>
    </div>
  );
}
