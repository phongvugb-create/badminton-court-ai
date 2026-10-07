import { z } from "zod";

export const profileUpdateSchema = z.object({
  fullName: z
    .string()
    .min(2, "Họ và tên phải có ít nhất 2 ký tự")
    .max(100, "Họ và tên không vượt quá 100 ký tự"),
  phone: z
    .string()
    .regex(/^[0-9+() -]*$/, "Số điện thoại không hợp lệ")
    .max(20, "Số điện thoại tối đa 20 số")
    .optional()
    .or(z.literal("")),
  address: z
    .string()
    .max(255, "Địa chỉ tối đa 255 ký tự")
    .optional()
    .or(z.literal("")),
  avatarUrl: z
    .string()
    .url("Đường dẫn Avatar không hợp lệ")
    .optional()
    .or(z.literal("")),
});

export const noteSchema = z.object({
  title: z.string().min(1, "Tiêu đề không được để trống").max(120, "Tiêu đề tối đa 120 ký tự"),
  content: z.string().max(1000, "Nội dung tối đa 1000 ký tự").optional().or(z.literal("")),
});

export type ProfileUpdateInput = z.infer<typeof profileUpdateSchema>;
export type NoteInput = z.infer<typeof noteSchema>;
