import { CustomerActivityLog } from "@/types/database";
import { History, Shield, Smartphone, Laptop } from "lucide-react";

interface ActivityLogsTableProps {
  logs: CustomerActivityLog[];
}

export function ActivityLogsTable({ logs }: ActivityLogsTableProps) {
  const getDeviceIcon = (info: string | null) => {
    if (!info) return <Shield className="h-4 w-4 text-emerald-500" />;
    const lower = info.toLowerCase();
    if (lower.includes("mobile") || lower.includes("android") || lower.includes("iphone")) {
      return <Smartphone className="h-4 w-4 text-teal-500" />;
    }
    return <Laptop className="h-4 w-4 text-indigo-500" />;
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
      <div className="flex items-center gap-2 pb-4 mb-4 border-b border-slate-100 dark:border-slate-800">
        <div className="p-2 bg-indigo-50 dark:bg-indigo-950/50 rounded-xl text-indigo-500">
          <History className="h-5 w-5" />
        </div>
        <div>
          <h3 className="font-bold text-slate-900 dark:text-white">
            Nhật ký hoạt động & Phiên đăng nhập
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Theo dõi mọi lần đăng nhập và thay đổi từ các trình duyệt khác nhau
          </p>
        </div>
      </div>

      {logs.length === 0 ? (
        <p className="text-sm text-slate-400 text-center py-6">
          Chưa có hoạt động nào được ghi nhận.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                <th className="py-2.5 px-3">Hành động</th>
                <th className="py-2.5 px-3">Thiết bị / Trình duyệt</th>
                <th className="py-2.5 px-3 text-right">Thời gian</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 px-3 font-medium text-slate-800 dark:text-slate-200">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      {log.action}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400 max-w-[280px] truncate">
                    <div className="flex items-center gap-1.5">
                      {getDeviceIcon(log.device_info)}
                      <span className="truncate" title={log.device_info || "Không xác định"}>
                        {log.device_info || "Hệ thống Cloud"}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-slate-400 text-right whitespace-nowrap font-mono">
                    {new Date(log.created_at).toLocaleString("vi-VN")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
