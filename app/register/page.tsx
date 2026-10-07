import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata = {
  title: "Đăng ký tài khoản - CloudSync AI",
  description: "Tạo tài khoản khách hàng mới để trải nghiệm đồng bộ hóa trên Cloud.",
};

export default function RegisterPage() {
  return (
    <div className="py-12 sm:py-20 px-4">
      <RegisterForm />
    </div>
  );
}
