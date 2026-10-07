import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";

export const metadata = {
  title: "Đặt lại mật khẩu - CloudSync AI",
  description: "Thiết lập mật khẩu mới cho tài khoản của bạn.",
};

export default function ResetPasswordPage() {
  return (
    <div className="py-12 sm:py-20 px-4">
      <ResetPasswordForm />
    </div>
  );
}
