"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import {
  registerSchema,
  loginSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
} from "@/lib/validation/auth";

export interface ActionResponse {
  success: boolean;
  message: string;
  fieldErrors?: Record<string, string>;
}

// 1. ACTION ĐĂNG KÝ TÀI KHOẢN MỚI
export async function registerAction(formData: FormData): Promise<ActionResponse> {
  const rawData = {
    fullName: formData.get("fullName"),
    email: formData.get("email"),
    password: formData.get("password"),
    confirmPassword: formData.get("confirmPassword"),
  };

  const validation = registerSchema.safeParse(rawData);
  if (!validation.success) {
    const fieldErrors: Record<string, string> = {};
    validation.error.issues.forEach((err) => {
      const path = err.path[0]?.toString();
      if (path) fieldErrors[path] = err.message;
    });
    return {
      success: false,
      message: "Dữ liệu đăng ký không hợp lệ, vui lòng kiểm tra lại.",
      fieldErrors,
    };
  }

  const { fullName, email, password } = validation.data;
  const supabase = await createClient();
  const origin = headers().get("origin") || "";

  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
      },
      emailRedirectTo: `${origin}/auth/callback`,
    },
  });

  if (error) {
    // Tránh để lộ lỗi nội bộ nhưng giải thích rõ trường hợp email đã tồn tại
    if (error.message.toLowerCase().includes("user already registered")) {
      return {
        success: false,
        message: "Email này đã được đăng ký. Vui lòng sử dụng email khác hoặc đăng nhập.",
      };
    }
    return {
      success: false,
      message: error.message || "Đăng ký không thành công. Vui lòng thử lại sau.",
    };
  }

  // Trường hợp Supabase yêu cầu xác minh email
  if (data.user && data.user.identities && data.user.identities.length === 0) {
    return {
      success: false,
      message: "Email này đã tồn tại trong hệ thống. Vui lòng đăng nhập.",
    };
  }

  if (data.session) {
    // Nếu Supabase tắt chế độ confirm email, session được tạo ngay
    return {
      success: true,
      message: "Đăng ký thành công! Đang chuyển hướng...",
    };
  }

  return {
    success: true,
    message: "Đăng ký thành công! Vui lòng kiểm tra hộp thư email của bạn để xác nhận tài khoản.",
  };
}

// 2. ACTION ĐĂNG NHẬP
export async function loginAction(formData: FormData): Promise<ActionResponse> {
  const rawData = {
    email: formData.get("email"),
    password: formData.get("password"),
  };

  const validation = loginSchema.safeParse(rawData);
  if (!validation.success) {
    const fieldErrors: Record<string, string> = {};
    validation.error.issues.forEach((err) => {
      const path = err.path[0]?.toString();
      if (path) fieldErrors[path] = err.message;
    });
    return {
      success: false,
      message: "Vui lòng nhập đầy đủ thông tin đăng nhập.",
      fieldErrors,
    };
  }

  const { email, password } = validation.data;
  const supabase = await createClient();

  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (error) {
    if (error.message.toLowerCase().includes("invalid login credentials")) {
      return {
        success: false,
        message: "Email hoặc mật khẩu không chính xác.",
      };
    }
    if (error.message.toLowerCase().includes("email not confirmed")) {
      return {
        success: false,
        message: "Tài khoản chưa được kích hoạt qua email. Vui lòng kiểm tra hòm thư của bạn.",
      };
    }
    return {
      success: false,
      message: "Đăng nhập thất bại. Vui lòng thử lại sau.",
    };
  }

  if (data.user) {
    // Ghi nhận Activity Log vào cơ sở dữ liệu
    const userAgent = headers().get("user-agent") || "Không xác định";
    await supabase.from("customer_activity_logs").insert({
      user_id: data.user.id,
      action: "Đăng nhập vào hệ thống",
      device_info: userAgent.slice(0, 150),
    });
  }

  return {
    success: true,
    message: "Đăng nhập thành công!",
  };
}

// 3. ACTION ĐĂNG XUẤT
export async function logoutAction() {
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}

// 4. ACTION QUÊN MẬT KHẨU
export async function forgotPasswordAction(formData: FormData): Promise<ActionResponse> {
  const email = formData.get("email");
  const validation = forgotPasswordSchema.safeParse({ email });

  if (!validation.success) {
    return {
      success: false,
      message: "Vui lòng nhập địa chỉ email hợp lệ.",
    };
  }

  const supabase = await createClient();
  const origin = headers().get("origin") || "";

  const { error } = await supabase.auth.resetPasswordForEmail(validation.data.email, {
    redirectTo: `${origin}/auth/callback?next=/reset-password`,
  });

  if (error) {
    return {
      success: false,
      message: "Không thể gửi email đặt lại mật khẩu. Vui lòng thử lại sau.",
    };
  }

  return {
    success: true,
    message: "Liên kết đặt lại mật khẩu đã được gửi đến email của bạn. Vui lòng kiểm tra hộp thư.",
  };
}

// 5. ACTION ĐẶT LẠI MẬT KHẨU (RESET PASSWORD)
export async function resetPasswordAction(formData: FormData): Promise<ActionResponse> {
  const rawData = {
    password: formData.get("password"),
    confirmPassword: formData.get("confirmPassword"),
  };

  const validation = resetPasswordSchema.safeParse(rawData);
  if (!validation.success) {
    const fieldErrors: Record<string, string> = {};
    validation.error.issues.forEach((err) => {
      const path = err.path[0]?.toString();
      if (path) fieldErrors[path] = err.message;
    });
    return {
      success: false,
      message: "Mật khẩu mới không hợp lệ hoặc không khớp.",
      fieldErrors,
    };
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return {
      success: false,
      message: "Phiên làm việc đã hết hạn hoặc không hợp lệ. Vui lòng gửi lại yêu cầu quên mật khẩu.",
    };
  }

  const { error } = await supabase.auth.updateUser({
    password: validation.data.password,
  });

  if (error) {
    return {
      success: false,
      message: "Không thể đổi mật khẩu: " + error.message,
    };
  }

  // Ghi nhận Activity Log
  const userAgent = headers().get("user-agent") || "Không xác định";
  await supabase.from("customer_activity_logs").insert({
    user_id: user.id,
    action: "Cập nhật mật khẩu mới",
    device_info: userAgent.slice(0, 150),
  });

  return {
    success: true,
    message: "Mật khẩu đã được cập nhật thành công! Đang chuyển hướng...",
  };
}
