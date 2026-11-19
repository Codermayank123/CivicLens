import { getOfflineQueue, removeQueueItem, updateQueueItemStatus } from './db';
import { complaintService } from '../complaint.service';
import toast from 'react-hot-toast';

class SyncManager {
  private isSyncing = false;

  async syncAll(): Promise<{ synced: number; failed: number }> {
    if (this.isSyncing) return { synced: 0, failed: 0 };
    if (!navigator.onLine) {
      return { synced: 0, failed: 0 };
    }

    this.isSyncing = true;
    let synced = 0;
    let failed = 0;

    try {
      const queue = await getOfflineQueue();
      const pendingItems = queue.filter((i) => i.status === 'pending' || i.status === 'failed');

      for (const item of pendingItems) {
        try {
          await updateQueueItemStatus(item.id, 'syncing');
          if (item.type === 'create_complaint') {
            const payload = { ...item.payload };
            if (Array.isArray(payload.media_files) && payload.media_files.length > 0) {
              const uploadedMedia = await Promise.all(
                payload.media_files.map((file: File) => complaintService.uploadMedia(file))
              );
              payload.media_urls = uploadedMedia.map((media) => media.url);
              payload.media_metadata = uploadedMedia.map(({ file_name, file_size, mime_type }) => ({
                file_name,
                file_size,
                mime_type,
              }));
              delete payload.media_files;
            }
            await complaintService.create(payload);
            await removeQueueItem(item.id);
            synced++;
          }
        } catch (err: any) {
          failed++;
          await updateQueueItemStatus(item.id, 'failed', err?.message || 'Network sync error');
        }
      }

      if (synced > 0) {
        toast.success(`Synced ${synced} offline complaint(s) with government portal!`);
      }
    } finally {
      this.isSyncing = false;
    }

    return { synced, failed };
  }

  listenForOnline() {
    window.addEventListener('online', () => {
      toast.success('Internet connection restored! Syncing offline reports...');
      this.syncAll();
    });

    window.addEventListener('offline', () => {
      toast.error('You are offline. Reports will be saved locally and synced once reconnected.');
    });
  }
}

export const syncManager = new SyncManager();
