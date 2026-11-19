import React, { useState, useEffect } from 'react';
import { UploadCloud, RefreshCw, Trash2, CheckCircle2, Wifi, WifiOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { getOfflineQueue, removeQueueItem, OfflineQueueItem } from '../services/offline/db';
import { syncManager } from '../services/offline/syncManager';
import { useUIStore } from '../store/uiStore';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';

export const SyncQueuePage: React.FC = () => {
  const { isOnline } = useUIStore();
  const [queue, setQueue] = useState<OfflineQueueItem[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);

  const loadQueue = async () => {
    const items = await getOfflineQueue();
    setQueue(items);
  };

  useEffect(() => {
    loadQueue();
  }, []);

  const handleSync = async () => {
    if (!isOnline) {
      toast.error('Cannot sync while offline. Please connect to the internet.');
      return;
    }
    setIsSyncing(true);
    try {
      await syncManager.syncAll();
      await loadQueue();
    } finally {
      setIsSyncing(false);
    }
  };

  const handleDelete = async (id: string) => {
    await removeQueueItem(id);
    toast.success('Removed item from local offline queue.');
    await loadQueue();
  };

  return (
    <div className="max-w-4xl mx-auto py-4 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-slate-100 flex items-center gap-2.5">
            <UploadCloud className="w-7 h-7 text-indigo-600" /> Offline Synchronization Queue
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Complaints composed while offline in dead-zones are stored in IndexedDB and queued here.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadQueue}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
          <Button
            size="sm"
            onClick={handleSync}
            isLoading={isSyncing}
            disabled={!isOnline || queue.length === 0}
            leftIcon={<UploadCloud className="w-4 h-4" />}
          >
            Sync All Now
          </Button>
        </div>
      </div>

      {/* Network banner */}
      <div
        className={`p-4 rounded-xl border flex items-center justify-between ${
          isOnline
            ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300'
            : 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300'
        }`}
      >
        <div className="flex items-center gap-2 text-xs font-semibold">
          {isOnline ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
          <span>
            {isOnline
              ? 'Internet Connected. Automatic background syncing enabled.'
              : 'Device Offline. Reports will be stored safely in browser IndexedDB.'}
          </span>
        </div>
        <span className="text-xs font-mono font-bold">{queue.length} Pending item(s)</span>
      </div>

      {/* Queue items */}
      {queue.length === 0 ? (
        <Card className="p-12 text-center space-y-3">
          <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto" />
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Offline Queue is Clear
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            All reports have been successfully pushed to the central government database.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {queue.map((item) => (
            <Card key={item.id} className="p-4 flex items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-slate-500">{item.id}</span>
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      item.status === 'failed'
                        ? 'bg-rose-100 text-rose-700'
                        : item.status === 'syncing'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <h4 className="font-semibold text-sm text-slate-900 dark:text-slate-100">
                  {item.payload?.title || 'Civic Issue Report'}
                </h4>
                <p className="text-xs text-slate-500 line-clamp-1">{item.payload?.description}</p>
                <div className="text-[10px] text-slate-400 font-mono">
                  Created: {new Date(item.createdAt).toLocaleString()}
                </div>
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleDelete(item.id)}
                className="text-slate-400 hover:text-rose-600"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
