import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";

export const metadata = {
  title: "Quên mật khẩu - CloudSync AI",
  description: "Khôi phục mật khẩu tài khoản qua email liên kết.",
};

export default function ForgotPasswordPage() {
  return (
    <div className="py-12 sm:py-20 px-4">
      <ForgotPasswordForm />
    </div>
  );
}
