export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[];

export interface Profile {
  id: string;
  email: string;
  full_name: string | null;
  phone: string | null;
  avatar_url: string | null;
  address: string | null;
  role: 'customer' | 'admin' | 'staff';
  created_at: string;
  updated_at: string;
}

export interface CustomerActivityLog {
  id: string;
  user_id: string;
  action: string;
  device_info: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface CustomerAddress {
  id: string;
  user_id: string;
  label: string;
  receiver_name: string;
  phone: string;
  address_line: string;
  is_default: boolean;
  created_at: string;
}

export interface CustomerNote {
  id: string;
  user_id: string;
  title: string;
  content: string | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerNotification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export type GenericRelationship = {
  foreignKeyName: string;
  columns: string[];
  isOneToOne?: boolean;
  referencedRelation: string;
  referencedColumns: string[];
};

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: Profile;
        Insert: {
          id: string;
          email: string;
          full_name?: string | null;
          phone?: string | null;
          avatar_url?: string | null;
          address?: string | null;
          role?: 'customer' | 'admin' | 'staff';
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          email?: string;
          full_name?: string | null;
          phone?: string | null;
          avatar_url?: string | null;
          address?: string | null;
          role?: 'customer' | 'admin' | 'staff';
          created_at?: string;
          updated_at?: string;
        };
        Relationships: GenericRelationship[];
      };
      customer_activity_logs: {
        Row: CustomerActivityLog;
        Insert: {
          id?: string;
          user_id: string;
          action: string;
          device_info?: string | null;
          ip_address?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          action?: string;
          device_info?: string | null;
          ip_address?: string | null;
          created_at?: string;
        };
        Relationships: GenericRelationship[];
      };
      customer_addresses: {
        Row: CustomerAddress;
        Insert: {
          id?: string;
          user_id: string;
          label: string;
          receiver_name: string;
          phone: string;
          address_line: string;
          is_default?: boolean;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          label?: string;
          receiver_name?: string;
          phone?: string;
          address_line?: string;
          is_default?: boolean;
          created_at?: string;
        };
        Relationships: GenericRelationship[];
      };
      customer_notes: {
        Row: CustomerNote;
        Insert: {
          id?: string;
          user_id: string;
          title: string;
          content?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          title?: string;
          content?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Relationships: GenericRelationship[];
      };
      customer_notifications: {
        Row: CustomerNotification;
        Insert: {
          id?: string;
          user_id: string;
          title: string;
          message: string;
          is_read?: boolean;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          title?: string;
          message?: string;
          is_read?: boolean;
          created_at?: string;
        };
        Relationships: GenericRelationship[];
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
  };
}
