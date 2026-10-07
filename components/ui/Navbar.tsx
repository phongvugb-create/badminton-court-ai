"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { logoutAction } from "@/lib/actions/auth";
import { User, LogOut, LayoutDashboard, Settings, Cloud, Smartphone, Monitor } from "lucide-react";

interface NavbarProps {
  userEmail?: string | null;
  userName?: string | null;
}

export function Navbar({ userEmail, userName }: NavbarProps) {
  const pathname = usePathname();

  const isAuthPage =
    pathname === "/login" ||
    pathname === "/register" ||
    pathname === "/forgot-password" ||
    pathname === "/reset-password";

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200/80 bg-white/80 backdrop-blur-md dark:border-slate-800 dark:bg-slate-900/80">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo & Brand */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 text-white shadow-md shadow-emerald-500/20 transition-transform group-hover:scale-105">
              <Cloud className="h-5 w-5" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                CloudSync<span className="text-emerald-500 font-extrabold">AI</span>
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs font-medium text-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 dark:text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-800">
                Multi-Browser Sync
              </span>
            </div>
          </Link>
        </div>

        {/* Sync Device Badges */}
        <div className="hidden lg:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
          <span className="flex items-center gap-1">
            <Monitor className="h-3.5 w-3.5 text-emerald-500" />
            Chrome • Edge • Firefox
          </span>
          <span className="text-slate-300 dark:text-slate-600">|</span>
          <span className="flex items-center gap-1">
            <Smartphone className="h-3.5 w-3.5 text-teal-500" />
            Mobile
          </span>
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse ml-1" />
        </div>

        {/* Navigation Action Links */}
        <div className="flex items-center gap-3">
          {userEmail ? (
            <>
              <nav className="flex items-center gap-1 sm:gap-2">
                <Link
                  href="/dashboard"
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    pathname === "/dashboard"
                      ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <LayoutDashboard className="h-4 w-4" />
                  <span className="hidden sm:inline">Dashboard</span>
                </Link>

                <Link
                  href="/profile"
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    pathname === "/profile"
                      ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <User className="h-4 w-4" />
                  <span className="hidden sm:inline">Hồ sơ</span>
                </Link>

                <Link
                  href="/settings"
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    pathname === "/settings"
                      ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                  }`}
                >
                  <Settings className="h-4 w-4" />
                  <span className="hidden sm:inline">Cài đặt</span>
                </Link>
              </nav>

              <div className="h-5 w-px bg-slate-200 dark:bg-slate-700 mx-1 hidden sm:block" />

              {/* User badge & Logout */}
              <div className="flex items-center gap-2">
                <div className="hidden md:flex flex-col text-right">
                  <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 max-w-[140px] truncate">
                    {userName || userEmail.split("@")[0]}
                  </span>
                  <span className="text-[11px] text-slate-400 truncate max-w-[140px]">
                    {userEmail}
                  </span>
                </div>
                <form action={logoutAction}>
                  <button
                    type="submit"
                    title="Đăng xuất khỏi thiết bị này"
                    className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-rose-600 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40 transition-colors border border-rose-100 dark:border-rose-900/50"
                  >
                    <LogOut className="h-4 w-4" />
                    <span className="hidden sm:inline">Đăng xuất</span>
                  </button>
                </form>
              </div>
            </>
          ) : (
            !isAuthPage && (
              <div className="flex items-center gap-2">
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                >
                  Đăng nhập
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm shadow-emerald-500/20 transition-colors"
                >
                  Đăng ký ngay
                </Link>
              </div>
            )
          )}
        </div>
      </div>
    </header>
  );
}
