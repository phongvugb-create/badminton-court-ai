import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { Shield, Key, Database, Globe } from "lucide-react";

export const metadata = {
  title: "Cài đặt tài khoản - CloudSync AI",
  description: "Cấu hình bảo mật và tùy chọn tài khoản.",
};

export default async function SettingsPage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Cài đặt bảo mật & Tài khoản
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Quản lý mật khẩu và các cơ chế bảo mật đám mây
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Đổi mật khẩu */}
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Key className="h-5 w-5 text-emerald-500" />
            <span>Đổi mật khẩu tài khoản</span>
          </h2>
          <ResetPasswordForm />
        </div>

        {/* Thông tin chính sách bảo mật */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Shield className="h-5 w-5 text-teal-500" />
            <span>Chính sách bảo mật dữ liệu</span>
          </h2>

          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-sm space-y-4 text-xs">
            <div className="flex items-start gap-3">
              <Database className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800 dark:text-slate-200 block text-sm">
                  Row Level Security (RLS)
                </strong>
                <p className="text-slate-500 dark:text-slate-400 mt-0.5">
                  Mỗi truy vấn được kiểm soát bằng chính sách phân quyền cấp hàng trong PostgreSQL. Không ai ngoài bạn có thể truy xuất dữ liệu cá nhân của bạn.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Shield className="h-4 w-4 text-teal-500 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800 dark:text-slate-200 block text-sm">
                  Session Cookie an toàn
                </strong>
                <p className="text-slate-500 dark:text-slate-400 mt-0.5">
                  Không lưu thông tin nhạy cảm trong localStorage. Session token được mã hóa và truyền tải qua giao thức HTTPS.
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <Globe className="h-4 w-4 text-cyan-500 shrink-0 mt-0.5" />
              <div>
                <strong className="text-slate-800 dark:text-slate-200 block text-sm">
                  Đồng bộ đa trình duyệt độc lập
                </strong>
                <p className="text-slate-500 dark:text-slate-400 mt-0.5">
                  Hệ thống cấp phiên làm việc riêng biệt cho từng trình duyệt (Chrome, Edge, Firefox, Brave) nhưng cùng liên kết đến một User ID trung tâm.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
