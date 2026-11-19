import React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, CheckCheck } from 'lucide-react';
import { notificationService } from '../services/notification.service';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useI18n } from '../i18n';

export const NotificationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const { data, isLoading } = useQuery({ queryKey: ['notifications'], queryFn: () => notificationService.getNotifications(), refetchInterval: 15_000 });
  const markRead = useMutation({ mutationFn: () => notificationService.markAsRead(), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }) });
  return <div className="max-w-3xl mx-auto space-y-5">
    <div className="flex items-center justify-between gap-3"><div><h1 className="heritage-page-title">{t('notifications')}</h1><p className="heritage-subtitle">{t('notificationsDescription')}</p></div><Button variant="outline" size="sm" onClick={() => markRead.mutate()} isLoading={markRead.isPending} leftIcon={<CheckCheck className="w-4 h-4" />}>{t('markAllRead')}</Button></div>
    <Card className="divide-y divide-[#e7d7bf]">{isLoading ? <p className="p-6 text-sm text-slate-500">{t('loading')}</p> : data?.notifications.length ? data.notifications.map((item) => <article key={item.id} className={`p-5 ${item.is_read ? 'opacity-70' : 'bg-[#fffaf3]'}`}><div className="flex gap-3"><Bell className="w-4 h-4 mt-0.5 text-[#e87924]" /><div><h2 className="font-semibold text-[#29232b] text-sm">{item.title}</h2><p className="mt-1 text-sm text-slate-600">{item.message}</p><time className="mt-2 block text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</time></div></div></article>) : <p className="p-8 text-center text-sm text-slate-500">{t('noNotifications')}</p>}</Card>
  </div>;
};
