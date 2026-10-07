import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { 
  Cloud, 
  ShieldCheck, 
  Zap, 
  Monitor, 
  Smartphone, 
  Database, 
  Lock, 
  CheckCircle,
  ArrowRight
} from "lucide-react";

export default async function HomePage() {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  return (
    <div className="relative overflow-hidden py-12 lg:py-20">
      {/* Background radial gradients */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-tr from-emerald-500/10 to-teal-400/10 rounded-full blur-3xl pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Hero Section */}
        <div className="text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 mb-6">
            <Zap className="h-3.5 w-3.5 text-emerald-600" />
            Hệ thống Quản lý Khách hàng & Đồng bộ Đa thiết bị
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight">
            Dữ liệu luôn đồng bộ <br />
            <span className="bg-gradient-to-r from-emerald-600 via-teal-500 to-cyan-500 bg-clip-text text-transparent">
              trên mọi trình duyệt & thiết bị
            </span>
          </h1>

          <p className="mt-6 text-base sm:text-lg text-slate-600 dark:text-slate-300 leading-relaxed">
            Giải quyết triệt để vấn đề phân mảnh dữ liệu giữa <strong>Chrome, Edge, Brave, Firefox</strong> và <strong>Mobile</strong>. Lưu trữ trung tâm trên PostgreSQL Cloud với bảo mật Row Level Security (RLS) tuyệt đối.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            {user ? (
              <Link
                href="/dashboard"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl shadow-lg shadow-emerald-600/25 transition-all text-sm group"
              >
                <span>Vào trang quản lý Dashboard</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
            ) : (
              <>
                <Link
                  href="/register"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl shadow-lg shadow-emerald-600/25 transition-all text-sm group"
                >
                  <span>Bắt đầu trải nghiệm ngay</span>
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  href="/login"
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-800 dark:text-white font-semibold rounded-xl border border-slate-200 dark:border-slate-700 transition-all text-sm shadow-sm"
                >
                  Đăng nhập tài khoản
                </Link>
              </>
            )}
          </div>
        </div>

        {/* Multi-Device Synchronous Flow Visual */}
        <div className="mt-16 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 sm:p-10 shadow-xl max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
              Kiến trúc đồng bộ chuẩn mực
            </span>
            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              Browser → Next.js SSR → Supabase Auth → PostgreSQL
            </h3>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-600 flex items-center justify-center">
                <Monitor className="h-6 w-6" />
              </div>
              <h4 className="font-bold text-slate-900 dark:text-white text-sm">Đa trình duyệt</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                Chrome, Edge, Brave, Firefox chia sẻ chung phiên bản dữ liệu mới nhất. Không phụ thuộc localStorage cục bộ.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 flex items-center justify-center">
                <Database className="h-6 w-6" />
              </div>
              <h4 className="font-bold text-slate-900 dark:text-white text-sm">PostgreSQL Cloud</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                Single Source of Truth. ACID compliant, hỗ trợ Realtime CDC và Row Level Security bảo vệ từng bản ghi.
              </p>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-teal-100 dark:bg-teal-950/60 text-teal-600 flex items-center justify-center">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <h4 className="font-bold text-slate-900 dark:text-white text-sm">Bảo mật RLS</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
                Người dùng A không bao giờ đọc hay sửa được dữ liệu người dùng B. Kiểm tra quyền trực tiếp tại server database.
              </p>
            </div>
          </div>
        </div>

        {/* Key Features Checklist */}
        <div className="mt-16 max-w-3xl mx-auto">
          <h3 className="text-xl font-bold text-slate-900 dark:text-white text-center mb-6">
            Các tính năng cốt lõi được xây dựng
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-sm">
            {[
              "Đăng ký, Đăng nhập, Đăng xuất bảo mật",
              "Xác minh tài khoản qua Email an toàn",
              "Quên mật khẩu & Đặt lại mật khẩu",
              "Hồ sơ khách hàng lưu trên PostgreSQL",
              "Tự động cập nhật không cần F5 (Realtime CDC)",
              "Nhật ký hoạt động chi tiết từng thiết bị",
              "Bảo vệ dữ liệu tuyệt đối bằng RLS",
              "Giao diện chuẩn Responsive Mobile-First"
            ].map((feature, i) => (
              <div key={i} className="flex items-center gap-2.5 p-3 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0" />
                <span className="text-slate-700 dark:text-slate-300 font-medium">{feature}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
