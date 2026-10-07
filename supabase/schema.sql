-- ==============================================================================
-- DATABASE SCHEMA & ROW LEVEL SECURITY (RLS) FOR MULTI-DEVICE CLOUD SYNC
-- ==============================================================================
-- Dùng để chạy trực tiếp trên Supabase SQL Editor
-- Đảm bảo tuân thủ nghiêm ngặt chuẩn bảo mật RLS và Realtime.

-- 1. BẬT CÁC EXTENSION CẦN THIẾT
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. TẠO BẢNG PROFILES (HỒ SƠ KHÁCH HÀNG TRUNG TÂM)
-- Liên kết 1-1 trực tiếp với auth.users thông qua ID UUID
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    phone TEXT,
    avatar_url TEXT,
    address TEXT,
    role TEXT DEFAULT 'customer' CHECK (role IN ('customer', 'admin', 'staff')),
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Index để tối ưu tìm kiếm theo email
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);

-- 3. TẠO CÁC BẢNG MỞ RỘNG (EXTENDED DATA)
-- Bảng 3.1: Lịch sử hoạt động và đồng bộ phiên (Customer Activity Logs)
CREATE TABLE IF NOT EXISTS public.customer_activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    action TEXT NOT NULL, -- 'login', 'update_profile', 'change_password', 'sync_session', v.v.
    device_info TEXT,     -- Ví dụ: 'Chrome 124 on Windows', 'Safari Mobile on iOS'
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON public.customer_activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at ON public.customer_activity_logs(created_at DESC);

-- Bảng 3.2: Sổ địa chỉ khách hàng (Addresses)
CREATE TABLE IF NOT EXISTS public.customer_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    label TEXT NOT NULL,         -- 'Nhà riêng', 'Cơ quan', 'Sân thể thao quen thuộc'
    receiver_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address_line TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_addresses_user_id ON public.customer_addresses(user_id);

-- Bảng 3.3: Ghi chú & Lời nhắc cá nhân (Customer Notes - dùng để test Realtime đa thiết bị)
CREATE TABLE IF NOT EXISTS public.customer_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customer_notes_user_id ON public.customer_notes(user_id);

-- Bảng 3.4: Thông báo cá nhân (Notifications)
CREATE TABLE IF NOT EXISTS public.customer_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON public.customer_notifications(user_id);

-- ==============================================================================
-- 4. DATABASE TRIGGERS & FUNCTIONS
-- ==============================================================================

-- 4.1 Trigger tự động cập nhật updated_at
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_profiles_updated_at ON public.profiles;
CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS set_customer_notes_updated_at ON public.customer_notes;
CREATE TRIGGER set_customer_notes_updated_at
    BEFORE UPDATE ON public.customer_notes
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 4.2 Trigger tự động tạo Profile khi user mới được xác thực trong auth.users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url, phone, address)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'avatar_url', ''),
        COALESCE(NEW.raw_user_meta_data->>'phone', ''),
        COALESCE(NEW.raw_user_meta_data->>'address', '')
    )
    ON CONFLICT (id) DO UPDATE
    SET email = EXCLUDED.email;
    
    -- Ghi nhận log khởi tạo tài khoản đầu tiên
    INSERT INTO public.customer_activity_logs (user_id, action, device_info)
    VALUES (NEW.id, 'Tài khoản được đăng ký thành công', 'Cloud System');

    -- Tạo thông báo chào mừng
    INSERT INTO public.customer_notifications (user_id, title, message)
    VALUES (NEW.id, 'Chào mừng bạn!', 'Tài khoản của bạn đã được kết nối với hệ thống Cloud Sync.');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- ==============================================================================
-- 5. ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================
-- Kích hoạt RLS trên tất cả các bảng
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_notifications ENABLE ROW LEVEL SECURITY;

-- 5.1 Policies cho bảng PROFILES
-- User chỉ được SELECT profile của chính mình
CREATE POLICY "Users can view own profile"
    ON public.profiles
    FOR SELECT
    USING (auth.uid() = id);

-- User chỉ được UPDATE profile của chính mình
CREATE POLICY "Users can update own profile"
    ON public.profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- User có thể tự insert nếu trigger chưa chạy (fallback an toàn)
CREATE POLICY "Users can insert own profile"
    ON public.profiles
    FOR INSERT
    WITH CHECK (auth.uid() = id);

-- 5.2 Policies cho bảng CUSTOMER_ACTIVITY_LOGS
CREATE POLICY "Users can view own activity logs"
    ON public.customer_activity_logs
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own activity logs"
    ON public.customer_activity_logs
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- 5.3 Policies cho bảng CUSTOMER_ADDRESSES
CREATE POLICY "Users can view own addresses"
    ON public.customer_addresses
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own addresses"
    ON public.customer_addresses
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own addresses"
    ON public.customer_addresses
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own addresses"
    ON public.customer_addresses
    FOR DELETE
    USING (auth.uid() = user_id);

-- 5.4 Policies cho bảng CUSTOMER_NOTES
CREATE POLICY "Users can view own notes"
    ON public.customer_notes
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notes"
    ON public.customer_notes
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notes"
    ON public.customer_notes
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own notes"
    ON public.customer_notes
    FOR DELETE
    USING (auth.uid() = user_id);

-- 5.5 Policies cho bảng CUSTOMER_NOTIFICATIONS
CREATE POLICY "Users can view own notifications"
    ON public.customer_notifications
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications"
    ON public.customer_notifications
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ==============================================================================
-- 6. BẬT SUPABASE REALTIME (CDC)
-- ==============================================================================
-- Thêm các bảng vào danh sách broadcast realtime của Supabase
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'profiles'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.profiles;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'customer_notes'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.customer_notes;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables 
        WHERE pubname = 'supabase_realtime' AND tablename = 'customer_notifications'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE public.customer_notifications;
    END IF;
END $$;
