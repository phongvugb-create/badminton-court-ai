"use client";

import { useEffect, useState, useTransition } from "react";
import { CustomerNote } from "@/types/database";
import { createClient } from "@/lib/supabase/client";
import { createNoteAction, deleteNoteAction } from "@/lib/actions/profile";
import { Zap, Plus, Trash2, Loader2, Sparkles, AlertCircle } from "lucide-react";

interface RealtimeNotesCardProps {
  userId: string;
  initialNotes: CustomerNote[];
}

export function RealtimeNotesCard({ userId, initialNotes }: RealtimeNotesCardProps) {
  const [notes, setNotes] = useState<CustomerNote[]>(initialNotes);
  const [isPending, startTransition] = useTransition();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [realtimeEventMsg, setRealtimeEventMsg] = useState<string | null>(null);

  // KẾT NỐI SUPABASE REALTIME WEBSOCKET
  useEffect(() => {
    const supabase = createClient();

    // Lắng nghe các thay đổi trên bảng customer_notes dành riêng cho user này
    const channel = supabase
      .channel(`user-notes-${userId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "customer_notes",
          filter: `user_id=eq.${userId}`,
        },
        (payload) => {
          if (payload.eventType === "INSERT") {
            const newNote = payload.new as CustomerNote;
            setNotes((prev) => [newNote, ...prev.filter((n) => n.id !== newNote.id)]);
            showNotification(`Đã đồng bộ ghi chú mới từ thiết bị khác: "${newNote.title}"`);
          } else if (payload.eventType === "DELETE") {
            const oldId = payload.old.id;
            setNotes((prev) => prev.filter((n) => n.id !== oldId));
            showNotification("Đã đồng bộ thao tác xóa ghi chú từ thiết bị khác.");
          } else if (payload.eventType === "UPDATE") {
            const updated = payload.new as CustomerNote;
            setNotes((prev) => prev.map((n) => (n.id === updated.id ? updated : n)));
            showNotification(`Đã cập nhật ghi chú: "${updated.title}"`);
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [userId]);

  const showNotification = (msg: string) => {
    setRealtimeEventMsg(msg);
    setTimeout(() => {
      setRealtimeEventMsg(null);
    }, 4000);
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    const formData = new FormData();
    formData.append("title", title);
    formData.append("content", content);

    startTransition(async () => {
      const res = await createNoteAction(formData);
      if (res.success) {
        setTitle("");
        setContent("");
      }
    });
  };

  const handleDeleteNote = (noteId: string) => {
    startTransition(async () => {
      await deleteNoteAction(noteId);
    });
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-sm">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-amber-50 dark:bg-amber-950/50 rounded-xl text-amber-500">
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
              Ghi chú & Lời nhắc Realtime
              <span className="text-[10px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300 px-2 py-0.5 rounded-full">
                Supabase Realtime CDC
              </span>
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Mở 2 cửa sổ trình duyệt (Chrome và Edge) để xem dữ liệu nhảy tức thì
            </p>
          </div>
        </div>
      </div>

      {realtimeEventMsg && (
        <div className="mb-4 flex items-center gap-2 p-3 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 rounded-xl text-xs text-emerald-700 dark:text-emerald-300 animate-fadeIn">
          <Sparkles className="h-4 w-4 shrink-0 text-emerald-500" />
          <span>{realtimeEventMsg}</span>
        </div>
      )}

      {/* Form thêm ghi chú mới */}
      <form onSubmit={handleAddNote} className="mb-6 space-y-3 bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Tiêu đề ghi chú (ví dụ: Lịch tập sân cầu lông thứ 7)..."
          required
          className="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
        />
        <textarea
          rows={2}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Nội dung chi tiết..."
          className="w-full px-3.5 py-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
        />
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isPending || !title.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium text-xs rounded-lg shadow-sm shadow-emerald-600/20 disabled:opacity-50 transition-all"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Plus className="h-3.5 w-3.5" />
            )}
            <span>Thêm và Đồng bộ ngay</span>
          </button>
        </div>
      </form>

      {/* Danh sách ghi chú */}
      {notes.length === 0 ? (
        <div className="text-center py-8 px-4 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
          <AlertCircle className="h-8 w-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">Chưa có ghi chú nào</p>
          <p className="text-xs text-slate-400 mt-0.5">
            Thêm ghi chú ở trên để kiểm tra đồng bộ tức thì trên thiết bị khác!
          </p>
        </div>
      ) : (
        <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
          {notes.map((note) => (
            <div
              key={note.id}
              className="group flex items-start justify-between p-3.5 bg-slate-50 hover:bg-slate-100/80 dark:bg-slate-800/40 dark:hover:bg-slate-800/80 border border-slate-100 dark:border-slate-800 rounded-xl transition-all"
            >
              <div className="pr-3">
                <h4 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {note.title}
                </h4>
                {note.content && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                    {note.content}
                  </p>
                )}
                <span className="inline-block mt-2 text-[10px] text-slate-400 font-mono">
                  {new Date(note.created_at).toLocaleString("vi-VN")}
                </span>
              </div>
              <button
                onClick={() => handleDeleteNote(note.id)}
                title="Xóa ghi chú này"
                className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition-all"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
