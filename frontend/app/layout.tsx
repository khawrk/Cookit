"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/authStore";
import type { User } from "@/types/auth";

const PUBLIC_PATHS = ["/login", "/register"];

function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, setUser } = useAuthStore();
  const [checking, setChecking] = useState(!user);

  useEffect(() => {
    if (PUBLIC_PATHS.some((p) => pathname?.startsWith(p))) {
      setChecking(false);
      return;
    }
    if (user) {
      setChecking(false);
      return;
    }
    // Verify session is still valid via /api/auth/me
    api
      .get<User>("/api/auth/me")
      .then((u) => {
        setUser(u);
        setChecking(false);
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [pathname]);

  if (checking && !PUBLIC_PATHS.some((p) => pathname?.startsWith(p))) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-6 h-6 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}

function Nav() {
  const pathname = usePathname();

  if (PUBLIC_PATHS.some((p) => pathname?.startsWith(p))) return null;

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur border-b border-slate-200">
      <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/fridge" className="flex items-center gap-2 font-bold text-lg text-slate-900">
          <span className="text-2xl">🥦</span>
          <span>Cookit</span>
        </Link>
        <nav className="flex items-center gap-1">
          <Link
            href="/fridge"
            className={[
              "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              pathname?.startsWith("/fridge")
                ? "bg-green-50 text-green-700"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100",
            ].join(" ")}
          >
            My Fridge
          </Link>
          <Link
            href="/recipes"
            className={[
              "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              pathname?.startsWith("/recipes")
                ? "bg-green-50 text-green-700"
                : "text-slate-600 hover:text-slate-900 hover:bg-slate-100",
            ].join(" ")}
          >
            Recipes
          </Link>
        </nav>
      </div>
    </header>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());

  return (
    <html lang="en">
      <body>
        <QueryClientProvider client={queryClient}>
          <AuthGuard>
            <Nav />
            <main>{children}</main>
          </AuthGuard>
        </QueryClientProvider>
      </body>
    </html>
  );
}
