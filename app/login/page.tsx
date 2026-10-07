import { LoginForm } from "@/components/auth/LoginForm";

export const metadata = {
  title: "Đăng nhập - CloudSync AI",
  description: "Đăng nhập tài khoản để đồng bộ dữ liệu trên mọi thiết bị.",
};

export default function LoginPage() {
  return (
    <div className="py-12 sm:py-20 px-4">
      <LoginForm />
    </div>
  );
}
