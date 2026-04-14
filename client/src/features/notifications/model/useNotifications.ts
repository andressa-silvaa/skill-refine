import { useCallback, useEffect, useRef, useState } from 'react';

import { useSession } from '@/entities/session';

import type { NotificationItem } from '../api/notificationsApi';
import { notificationsApi } from '../api/notificationsApi';

const UNREAD_CACHE_MS = 15_000;

export function useNotifications() {
  const { status: sessionStatus } = useSession();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const unreadFetchedAt = useRef<number>(0);

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationsApi.list({ limit: 30, offset: 0 });
      setItems(res.items);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : 'Erro ao carregar notificações'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchUnreadCount = useCallback(async (force = false) => {
    const now = Date.now();
    if (!force && now - unreadFetchedAt.current < UNREAD_CACHE_MS) return;
    try {
      const res = await notificationsApi.getUnreadCount();
      setUnreadCount(res.count);
      unreadFetchedAt.current = now;
    } catch {
      // Silently fail for badge; list will show error if opened
    }
  }, []);

  useEffect(() => {
    if (sessionStatus !== 'authenticated') {
      setUnreadCount(0);
      return;
    }
    fetchUnreadCount(true);
    const interval = setInterval(() => fetchUnreadCount(false), UNREAD_CACHE_MS);
    const onInvalidate = () => fetchUnreadCount(true);
    window.addEventListener('skill-refine:notifications-invalidate', onInvalidate);
    return () => {
      clearInterval(interval);
      window.removeEventListener('skill-refine:notifications-invalidate', onInvalidate);
    };
  }, [fetchUnreadCount, sessionStatus]);

  const markRead = useCallback(async (id: string) => {
    try {
      await notificationsApi.markRead(id);
      setItems((prev) =>
        prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // Optimistic update reverted on error would need refetch
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await notificationsApi.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, isRead: true })));
      setUnreadCount(0);
      unreadFetchedAt.current = 0;
    } catch {
      await fetchUnreadCount(true);
    }
  }, [fetchUnreadCount]);

  const deleteOne = useCallback(async (id: string) => {
    try {
      await notificationsApi.delete(id);
      const removed = items.find((n) => n.id === id);
      setItems((prev) => prev.filter((n) => n.id !== id));
      if (removed && !removed.isRead) {
        setUnreadCount((c) => Math.max(0, c - 1));
      }
    } catch {
      await fetchList();
      await fetchUnreadCount(true);
    }
  }, [items, fetchList, fetchUnreadCount]);

  const clearAll = useCallback(async () => {
    try {
      await notificationsApi.clearAll();
      setItems([]);
      setUnreadCount(0);
      unreadFetchedAt.current = 0;
    } catch {
      await fetchList();
      await fetchUnreadCount(true);
    }
  }, [fetchList, fetchUnreadCount]);

  return {
    items,
    unreadCount,
    loading,
    error,
    fetchList,
    fetchUnreadCount,
    markRead,
    markAllRead,
    deleteOne,
    clearAll,
  };
}

export function useNotificationsUnreadBadge() {
  const { status: sessionStatus } = useSession();
  const [unreadCount, setUnreadCount] = useState(0);
  const fetchedAt = useRef<number>(0);

  useEffect(() => {
    if (sessionStatus !== 'authenticated') {
      setUnreadCount(0);
      return;
    }
    const refresh = async () => {
      const now = Date.now();
      if (now - fetchedAt.current < UNREAD_CACHE_MS) return;
      try {
        const res = await notificationsApi.getUnreadCount();
        setUnreadCount(res.count);
        fetchedAt.current = now;
      } catch {
        // Silently fail
      }
    };
    void refresh();
    const interval = setInterval(() => void refresh(), UNREAD_CACHE_MS);
    return () => clearInterval(interval);
  }, [sessionStatus]);

  return { unreadCount, invalidate: () => { fetchedAt.current = 0; } };
}
