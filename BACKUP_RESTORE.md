# MongoDB backup and restore

## Backup

Use a restricted service account and encrypted storage. For self-managed MongoDB:

```powershell
mongodump --uri "$env:MONGODB_URL" --db civiclens --archive="civiclens-YYYYMMDD.archive" --gzip
```

For MongoDB Atlas, configure scheduled cloud backups and periodic restore drills. Include object-storage media in a separate versioned backup plan; MongoDB stores metadata, not necessarily the binary evidence.

## Restore drill

1. Restore into an isolated staging database first.
2. Verify document counts, indexes, complaint/media relationships and a sample of signed-media access.
3. Stop application writes, capture a final backup, then restore only with an approved incident change.
4. Rotate credentials if the incident involved exposure; record the drill or recovery result.

```powershell
mongorestore --uri "$env:MONGODB_URL" --archive="civiclens-YYYYMMDD.archive" --gzip --drop
```

`--drop` is destructive. Use it only for the explicitly approved target database after a verified backup.
