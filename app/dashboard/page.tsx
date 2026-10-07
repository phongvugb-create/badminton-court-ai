import { redirect } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { SyncStatusCard } from "@/components/dashboard/SyncStatusCard";
import { RealtimeNotesCard } from "@/components/dashboard/RealtimeNotesCard";
import { ActivityLogsTable } from "@/components/dashboard/ActivityLogsTable";
import { Profile, CustomerNote, CustomerActivityLog } from "@/types/database";
import { 
  Mail, 
  Phone, 
  MapPin, 
  Calendar, 
  Edit3, 
  CheckCircle2, 
  Database
} from "lucide-react";

export const metadata = {
  title: "Bảng điều khiển - CloudSync AI",
  description: "Quản lý hồ sơ và theo dõi dữ liệu đồng bộ trên đám mây.",
};

export default async function DashboardPage() {
  const supabase = await createClient();

  // 1. Kiểm tra xác thực người dùng phía Server
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  // 2. Lấy dữ liệu hồ sơ từ bảng profiles (PostgreSQL)
  let profile: Profile;
  const { data: profileData } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (profileData) {
    profile = profileData as Profile;
  } else {
    // Fallback nếu trigger DB chưa kịp chạy khi đăng ký
    const defaultProfile = {
      id: user.id,
      email: user.email!,
      full_name: (user.user_metadata?.full_name as string) || user.email!.split("@")[0],
      phone: null,
      avatar_url: null,
      address: null,
      role: 'customer' as const,
    };
    await supabase.from("profiles").insert(defaultProfile);
    profile = {
      ...defaultProfile,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  }

  // 3. Lấy danh sách ghi chú thời gian thực
  const { data: notesData } = await supabase
    .from("customer_notes")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false });

  const notes: CustomerNote[] = (notesData as CustomerNote[]) || [];

  // 4. Lấy lịch sử hoạt động và phiên đăng nhập
  const { data: logsData } = await supabase
    .from("customer_activity_logs")
    .select("*")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(8);

  const logs: CustomerActivityLog[] = (logsData as CustomerActivityLog[]) || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* 1. Trạng thái đồng bộ đa trình duyệt */}
      <SyncStatusCard userId={user.id} userEmail={user.email!} />

      {/* 2. Thẻ hồ sơ tổng quan của khách hàng */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 sm:p-7 shadow-sm">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between pb-6 border-b border-slate-100 dark:border-slate-800 gap-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              {profile.avatar_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profile.avatar_url}
                  alt={profile.full_name || "Avatar"}
                  className="w-16 h-16 rounded-2xl object-cover ring-2 ring-emerald-500/20 shadow-md"
                />
              ) : (
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center font-bold text-2xl shadow-md">
                  {(profile.full_name || profile.email)[0].toUpperCase()}
                </div>
              )}
              <span className="absolute -bottom-1 -right-1 p-1 bg-emerald-500 text-white rounded-full ring-2 ring-white dark:ring-slate-900">
                <CheckCircle2 className="h-3.5 w-3.5" />
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 dark:text-white">
                  {profile.full_name || "Khách hàng"}
                </h1>
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  {profile.role === "admin" ? "Quản trị viên" : "Tài khoản khách hàng"}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1 flex items-center gap-1 font-mono">
                <Database className="h-3 w-3 text-emerald-500" />
                UID: {profile.id}
              </p>
            </div>
          </div>

          <Link
            href="/profile"
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-xs rounded-xl transition-all"
          >
            <Edit3 className="h-3.5 w-3.5" />
            <span>Chỉnh sửa hồ sơ</span>
          </Link>
        </div>

        {/* Thông tin chi tiết */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-1">
              <Mail className="h-3.5 w-3.5 text-slate-400" />
              Email xác thực
            </span>
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate block">
              {profile.email}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-1">
              <Phone className="h-3.5 w-3.5 text-slate-400" />
              Số điện thoại
            </span>
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200 block">
              {profile.phone || "Chưa cập nhật"}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-1">
              <MapPin className="h-3.5 w-3.5 text-slate-400" />
              Địa chỉ liên hệ
            </span>
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate block">
              {profile.address || "Chưa cập nhật"}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800/80">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-1">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              Ngày tạo tài khoản
            </span>
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200 block">
              {new Date(profile.created_at).toLocaleDateString("vi-VN")}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Khu vực tính năng: Realtime Notes & Activity Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <RealtimeNotesCard userId={user.id} initialNotes={notes} />
        <ActivityLogsTable logs={logs} />
      </div>
    </div>
  );
}
