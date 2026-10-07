"use server";

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import { createClient } from "@/lib/supabase/server";
import { profileUpdateSchema, noteSchema } from "@/lib/validation/profile";
import { ActionResponse } from "./auth";

// CẬP NHẬT THÔNG TIN HỒ SƠ KHÁCH HÀNG (PROFILE)
export async function updateProfileAction(formData: FormData): Promise<ActionResponse> {
  const rawData = {
    fullName: formData.get("fullName"),
    phone: formData.get("phone") || "",
    address: formData.get("address") || "",
    avatarUrl: formData.get("avatarUrl") || "",
  };

  const validation = profileUpdateSchema.safeParse(rawData);
  if (!validation.success) {
    const fieldErrors: Record<string, string> = {};
    validation.error.issues.forEach((err) => {
      const path = err.path[0]?.toString();
      if (path) fieldErrors[path] = err.message;
    });
    return {
      success: false,
      message: "Dữ liệu hồ sơ không hợp lệ.",
      fieldErrors,
    };
  }

  const supabase = await createClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) {
    return {
      success: false,
      message: "Bạn chưa đăng nhập hoặc phiên làm việc đã kết thúc.",
    };
  }

  // Cập nhật Database trực tiếp với RLS bảo vệ
  const { error } = await supabase
    .from("profiles")
    .update({
      full_name: validation.data.fullName,
      phone: validation.data.phone || null,
      address: validation.data.address || null,
      avatar_url: validation.data.avatarUrl || null,
    })
    .eq("id", user.id);

  if (error) {
    return {
      success: false,
      message: "Không thể lưu thông tin: " + error.message,
    };
  }

  // Ghi nhận Activity Log
  const userAgent = headers().get("user-agent") || "Không xác định";
  await supabase.from("customer_activity_logs").insert({
    user_id: user.id,
    action: "Cập nhật thông tin hồ sơ cá nhân",
    device_info: userAgent.slice(0, 150),
  });

  // Revalidate cache của Next.js để dữ liệu hiển thị tức thì
  revalidatePath("/profile");
  revalidatePath("/dashboard");

  return {
    success: true,
    message: "Thông tin hồ sơ đã được đồng bộ lên Cloud thành công!",
  };
}

// TẠO GHI CHÚ MỚI (DÙNG ĐỂ KIỂM THỬ ĐỒNG BỘ REALTIME ĐA THIẾT BỊ)
export async function createNoteAction(formData: FormData): Promise<ActionResponse> {
  const rawData = {
    title: formData.get("title"),
    content: formData.get("content") || "",
  };

  const validation = noteSchema.safeParse(rawData);
  if (!validation.success) {
    return {
      success: false,
      message: validation.error.issues[0]?.message || "Dữ liệu không hợp lệ",
    };
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return {
      success: false,
      message: "Vui lòng đăng nhập để thực hiện thao tác này.",
    };
  }

  const { error } = await supabase.from("customer_notes").insert({
    user_id: user.id,
    title: validation.data.title,
    content: validation.data.content || null,
  });

  if (error) {
    return {
      success: false,
      message: "Lỗi lưu ghi chú: " + error.message,
    };
  }

  revalidatePath("/dashboard");
  return {
    success: true,
    message: "Đã tạo ghi chú và đồng bộ lên Cloud!",
  };
}

// XÓA GHI CHÚ
export async function deleteNoteAction(noteId: string): Promise<ActionResponse> {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return {
      success: false,
      message: "Vui lòng đăng nhập.",
    };
  }

  const { error } = await supabase
    .from("customer_notes")
    .delete()
    .eq("id", noteId)
    .eq("user_id", user.id);

  if (error) {
    return {
      success: false,
      message: "Không thể xóa ghi chú: " + error.message,
    };
  }

  revalidatePath("/dashboard");
  return {
    success: true,
    message: "Đã xóa ghi chú thành công!",
  };
}
