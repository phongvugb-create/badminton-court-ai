"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Profile } from "@/types/database";
import { updateProfileAction } from "@/lib/actions/profile";
import { User, Phone, MapPin, Image, Save, Loader2, CheckCircle2, AlertCircle, ShieldAlert } from "lucide-react";

interface ProfileEditFormProps {
  initialProfile: Profile;
}

export function ProfileEditForm({ initialProfile }: ProfileEditFormProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [avatarPreview, setAvatarPreview] = useState<string>(initialProfile.avatar_url || "");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);
    setFieldErrors({});

    const formData = new FormData(event.currentTarget);

    startTransition(async () => {
      const result = await updateProfileAction(formData);
      if (!result.success) {
        setErrorMessage(result.message);
        if (result.fieldErrors) setFieldErrors(result.fieldErrors);
      } else {
        setSuccessMessage(result.message);
        router.refresh();
      }
    });
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 sm:p-8 shadow-sm">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-6 mb-6 border-b border-slate-100 dark:border-slate-800 gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Thông tin hồ sơ khách hàng
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Dữ liệu được lưu trữ trên PostgreSQL Cloud và đồng bộ thời gian thực
          </p>
        </div>

        {/* Cloud User ID Tag */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 rounded-xl text-xs font-mono border border-slate-200 dark:border-slate-700">
          <span className="text-slate-400">UUID:</span>
          <span className="font-semibold text-emerald-600 dark:text-emerald-400">
            {initialProfile.id.slice(0, 8)}...{initialProfile.id.slice(-6)}
          </span>
        </div>
      </div>

      {errorMessage && (
        <div className="mb-6 flex items-start gap-3 p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl text-rose-700 dark:text-rose-300 text-sm">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5 text-rose-500" />
          <span>{errorMessage}</span>
        </div>
      )}

      {successMessage && (
        <div className="mb-6 flex items-start gap-3 p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 rounded-xl text-emerald-700 dark:text-emerald-300 text-sm">
          <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5 text-emerald-500" />
          <span>{successMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Read-only Email Field */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Email đăng ký (Cố định bảo mật)
            </label>
            <input
              type="email"
              disabled
              value={initialProfile.email}
              className="w-full px-4 py-2.5 bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 rounded-xl text-sm text-slate-500 dark:text-slate-400 cursor-not-allowed select-none"
            />
            <p className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <ShieldAlert className="h-3 w-3" /> Email được bảo vệ bởi Supabase Auth
            </p>
          </div>

          {/* Full Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Họ và tên
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <User className="h-4 w-4" />
              </div>
              <input
                name="fullName"
                type="text"
                required
                defaultValue={initialProfile.full_name || ""}
                placeholder="Nhập họ và tên đầy đủ"
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                  fieldErrors.fullName ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
                } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
              />
            </div>
            {fieldErrors.fullName && (
              <p className="mt-1 text-xs text-rose-500">{fieldErrors.fullName}</p>
            )}
          </div>

          {/* Phone */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Số điện thoại
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Phone className="h-4 w-4" />
              </div>
              <input
                name="phone"
                type="tel"
                defaultValue={initialProfile.phone || ""}
                placeholder="0912 345 678"
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                  fieldErrors.phone ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
                } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
              />
            </div>
            {fieldErrors.phone && (
              <p className="mt-1 text-xs text-rose-500">{fieldErrors.phone}</p>
            )}
          </div>

          {/* Avatar URL */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Ảnh đại diện (URL)
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Image className="h-4 w-4" />
              </div>
              <input
                name="avatarUrl"
                type="url"
                value={avatarPreview}
                onChange={(e) => setAvatarPreview(e.target.value)}
                placeholder="https://images.unsplash.com/..."
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                  fieldErrors.avatarUrl ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
                } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
              />
            </div>
            {fieldErrors.avatarUrl && (
              <p className="mt-1 text-xs text-rose-500">{fieldErrors.avatarUrl}</p>
            )}
          </div>
        </div>

        {/* Address */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
            Địa chỉ thường trú / liên hệ
          </label>
          <div className="relative">
            <div className="absolute top-3 left-3.5 pointer-events-none text-slate-400">
              <MapPin className="h-4 w-4" />
            </div>
            <textarea
              name="address"
              rows={3}
              defaultValue={initialProfile.address || ""}
              placeholder="Số nhà, tên đường, quận/huyện, thành phố..."
              className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                fieldErrors.address ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
              } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
            />
          </div>
          {fieldErrors.address && (
            <p className="mt-1 text-xs text-rose-500">{fieldErrors.address}</p>
          )}
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button
            type="submit"
            disabled={isPending}
            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-sm rounded-xl shadow-md shadow-emerald-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all active:scale-[0.99]"
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Đang đồng bộ lên Cloud...</span>
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                <span>Lưu thông tin hồ sơ</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
