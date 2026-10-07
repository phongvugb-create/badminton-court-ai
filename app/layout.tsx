import type { Metadata } from "next";
import "./globals.css";
import { createClient } from "@/lib/supabase/server";
import { Navbar } from "@/components/ui/Navbar";

export const metadata: Metadata = {
  title: "CloudSync AI - Hệ thống Khách hàng & Đồng bộ Đa trình duyệt",
  description: "Giải pháp quản lý tài khoản khách hàng lưu trữ Cloud PostgreSQL, đồng bộ dữ liệu tức thì trên Chrome, Edge, Brave, Firefox và Mobile.",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  let fullName: string | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from("profiles")
      .select("full_name")
      .eq("id", user.id)
      .single();
    if (profile) {
      fullName = (profile as { full_name: string | null }).full_name;
    }
  }

  return (
    <html lang="vi" className="h-full">
      <body className="min-h-full flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased selection:bg-emerald-500 selection:text-white">
        <Navbar userEmail={user?.email} userName={fullName} />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900/60 py-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <span>© 2026 CloudSync Sports AI. All rights reserved.</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400">
              PostgreSQL • Supabase Auth & Realtime • Next.js SSR
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
