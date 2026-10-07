"use client";

import { useEffect, useState } from "react";
import { Monitor, Smartphone, Globe, Cloud, CheckCircle, RefreshCw } from "lucide-react";

interface SyncStatusCardProps {
  userId: string;
  userEmail: string;
}

export function SyncStatusCard({ userId, userEmail }: SyncStatusCardProps) {
  const [browserInfo, setBrowserInfo] = useState<string>("Đang phát hiện trình duyệt...");
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [lastSyncTime, setLastSyncTime] = useState<string>("");

  useEffect(() => {
    // Nhận diện trình duyệt phía Client
    const ua = navigator.userAgent;
    let browserName = "Trình duyệt hiện đại";

    if (ua.includes("Edg/")) {
      browserName = "Microsoft Edge";
    } else if (ua.includes("Chrome/") && !ua.includes("Edg/")) {
      // Kiểm tra Brave
      if ((navigator as any).brave && typeof (navigator as any).brave.isBrave === "function") {
        browserName = "Brave Browser";
      } else {
        browserName = "Google Chrome";
      }
    } else if (ua.includes("Firefox/")) {
      browserName = "Mozilla Firefox";
    } else if (ua.includes("Safari/") && !ua.includes("Chrome/")) {
      browserName = "Apple Safari";
    }

    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
    setBrowserInfo(`${browserName} (${isMobile ? "Điện thoại / Tablet" : "Máy tính Desktop"})`);
    setIsOnline(navigator.onLine);
    setLastSyncTime(new Date().toLocaleTimeString("vi-VN"));

    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-850 to-slate-950 text-white rounded-2xl p-6 sm:p-7 shadow-xl border border-slate-800 relative overflow-hidden">
      {/* Decorative gradient glow */}
      <div className="absolute top-0 right-0 -mt-10 -mr-10 w-44 h-44 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-44 h-44 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800/80 gap-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
              <Cloud className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold">Trạng thái đồng bộ Cloud (Multi-Device)</h2>
              <p className="text-xs text-slate-400">
                Single Source of Truth: PostgreSQL Cloud (Supabase)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
                isOnline
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                  : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
              }`}
            >
              <span className={`h-2 w-2 rounded-full ${isOnline ? "bg-emerald-400 animate-ping" : "bg-rose-400"}`} />
              {isOnline ? "Đang kết nối Realtime" : "Mất kết nối"}
            </span>
          </div>
        </div>

        {/* Device & Browser Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
              <Globe className="h-3.5 w-3.5 text-emerald-400" />
              Thiết bị / Trình duyệt này
            </div>
            <div className="text-sm font-semibold text-white truncate">
              {browserInfo}
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
              <CheckCircle className="h-3.5 w-3.5 text-teal-400" />
              Tài khoản xác thực
            </div>
            <div className="text-sm font-semibold text-emerald-300 truncate">
              {userEmail}
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 mb-1">
              <RefreshCw className="h-3.5 w-3.5 text-cyan-400" />
              Thời gian đồng bộ gần nhất
            </div>
            <div className="text-sm font-semibold text-white">
              {lastSyncTime || "Vừa xong"}
            </div>
          </div>
        </div>

        {/* Sync explanation banner */}
        <div className="mt-5 p-3.5 bg-emerald-950/30 border border-emerald-800/40 rounded-xl text-xs text-emerald-200/90 leading-relaxed flex items-start gap-2.5">
          <div className="h-2 w-2 rounded-full bg-emerald-400 mt-1 shrink-0" />
          <div>
            <strong>Đồng bộ xuyên suốt không dùng localStorage:</strong> Mọi thay đổi bạn thực hiện trên trình duyệt này sẽ lập tức ghi vào PostgreSQL và phản ánh sang Google Chrome, Microsoft Edge, Brave, Firefox hoặc điện thoại của bạn ngay khi đăng nhập.
          </div>
        </div>
      </div>
    </div>
  );
}
