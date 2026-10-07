"use client";

import { useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { registerAction } from "@/lib/actions/auth";
import { User, Mail, Lock, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2, ShieldCheck } from "lucide-react";

export function RegisterForm() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setFieldErrors({});

    const formData = new FormData(event.currentTarget);

    startTransition(async () => {
      const result = await registerAction(formData);
      if (!result.success) {
        setErrorMessage(result.message);
        if (result.fieldErrors) setFieldErrors(result.fieldErrors);
      } else {
        setSuccessMessage(result.message);
        // Nếu thành công và session tạo ngay
        if (result.message.includes("chuyển hướng")) {
          setTimeout(() => {
            router.push("/dashboard");
            router.refresh();
          }, 800);
        }
      }
    });
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl shadow-slate-200/50 dark:shadow-none">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">
            Tạo tài khoản mới
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Đăng ký để đồng bộ dữ liệu tập trung trên Cloud
          </p>
        </div>

        {errorMessage && (
          <div className="mb-5 flex items-start gap-3 p-3.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-xl text-rose-700 dark:text-rose-300 text-sm animate-fadeIn">
            <AlertCircle className="h-5 w-5 shrink-0 mt-0.5 text-rose-500" />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div className="mb-5 flex items-start gap-3 p-3.5 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/60 rounded-xl text-emerald-700 dark:text-emerald-300 text-sm animate-fadeIn">
            <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5 text-emerald-500" />
            <div>
              <p className="font-medium">{successMessage}</p>
              <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
                Sau khi kích hoạt, bạn có thể đăng nhập trên mọi trình duyệt Chrome, Edge, Firefox.
              </p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Full name input */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Họ và tên
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <User className="h-4 w-4" />
              </div>
              <input
                id="register-fullname"
                name="fullName"
                type="text"
                required
                placeholder="Nguyễn Văn A"
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                  fieldErrors.fullName ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
                } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
              />
            </div>
            {fieldErrors.fullName && (
              <p className="mt-1 text-xs text-rose-500">{fieldErrors.fullName}</p>
            )}
          </div>

          {/* Email input */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Email
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail className="h-4 w-4" />
              </div>
              <input
                id="register-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="tenban@domain.com"
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                  fieldErrors.email ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
                } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
              />
            </div>
            {fieldErrors.email && (
              <p className="mt-1 text-xs text-rose-500">{fieldErrors.email}</p>
            )}
          </div>

          {/* Password input */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Mật khẩu (Tối thiểu 6 ký tự gồm chữ & số)
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="h-4 w-4" />
              </div>
              <input
                id="register-password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                placeholder="••••••••"
                className={`w-full pl-10 pr-10 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                  fieldErrors.password ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
                } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus:outline-none"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {fieldErrors.password && (
              <p className="mt-1 text-xs text-rose-500">{fieldErrors.password}</p>
            )}
          </div>

          {/* Confirm Password input */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5 uppercase tracking-wider">
              Xác nhận mật khẩu
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <input
                id="register-confirm-password"
                name="confirmPassword"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                placeholder="••••••••"
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-800/80 border ${
                  fieldErrors.confirmPassword ? "border-rose-500 ring-1 ring-rose-500" : "border-slate-200 dark:border-slate-700"
                } rounded-xl text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500 transition-all`}
              />
            </div>
            {fieldErrors.confirmPassword && (
              <p className="mt-1 text-xs text-rose-500">{fieldErrors.confirmPassword}</p>
            )}
          </div>

          {/* Submit button */}
          <button
            id="register-submit-button"
            type="submit"
            disabled={isPending}
            className="w-full mt-2 flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium text-sm rounded-xl shadow-md shadow-emerald-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all active:scale-[0.99]"
          >
            {isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Đang xử lý đăng ký...</span>
              </>
            ) : (
              <span>Đăng ký tài khoản Cloud</span>
            )}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-slate-100 dark:border-slate-800 text-center">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Đã có tài khoản?{" "}
            <Link
              href="/login"
              className="font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 hover:underline"
            >
              Đăng nhập tại đây
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
