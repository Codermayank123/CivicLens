import { openDB, DBSchema, IDBPDatabase } from 'idb';

export interface OfflineQueueItem {
  id: string;
  type: 'create_complaint';
  payload: any;
  createdAt: string;
  status: 'pending' | 'syncing' | 'failed';
  error?: string;
}

interface CivicLensDB extends DBSchema {
  complaints: {
    key: string;
    value: any;
  };
  sync_queue: {
    key: string;
    value: OfflineQueueItem;
    indexes: { 'by-status': string };
  };
}

let dbPromise: Promise<IDBPDatabase<CivicLensDB>> | null = null;

export function getDB() {
  if (!dbPromise) {
    dbPromise = openDB<CivicLensDB>('civiclens_offline_db', 1, {
      upgrade(db) {
        if (!db.objectStoreNames.contains('complaints')) {
          db.createObjectStore('complaints', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('sync_queue')) {
          const queueStore = db.createObjectStore('sync_queue', { keyPath: 'id' });
          queueStore.createIndex('by-status', 'status');
        }
      },
    });
  }
  return dbPromise;
}

export async function queueOfflineComplaint(payload: any): Promise<OfflineQueueItem> {
  const db = await getDB();
  const item: OfflineQueueItem = {
    id: `offline_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
    type: 'create_complaint',
    payload,
    createdAt: new Date().toISOString(),
    status: 'pending',
  };
  await db.put('sync_queue', item);
  return item;
}

export async function getOfflineQueue(): Promise<OfflineQueueItem[]> {
  const db = await getDB();
  return db.getAll('sync_queue');
}

export async function removeQueueItem(id: string): Promise<void> {
  const db = await getDB();
  await db.delete('sync_queue', id);
}

export async function updateQueueItemStatus(
  id: string,
  status: 'pending' | 'syncing' | 'failed',
  error?: string
): Promise<void> {
  const db = await getDB();
  const item = await db.get('sync_queue', id);
  if (item) {
    item.status = status;
    if (error) item.error = error;
    await db.put('sync_queue', item);
  }
}
