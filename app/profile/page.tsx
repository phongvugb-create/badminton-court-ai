import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ProfileEditForm } from "@/components/profile/ProfileEditForm";
import { Profile } from "@/types/database";

export const metadata = {
  title: "Hồ sơ cá nhân - CloudSync AI",
  description: "Xem và cập nhật thông tin cá nhân của bạn.",
};

export default async function ProfilePage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  let profile: Profile;
  const { data: profileData } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (profileData) {
    profile = profileData as Profile;
  } else {
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

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
          Quản lý tài khoản & Hồ sơ
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Mọi chỉnh sửa sẽ được lưu trực tiếp vào database PostgreSQL và đồng bộ sang tất cả các thiết bị.
        </p>
      </div>

      <ProfileEditForm initialProfile={profile} />
    </div>
  );
}
