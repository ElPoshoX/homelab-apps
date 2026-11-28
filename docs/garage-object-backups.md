# Garage object backups

TrueNAS pulls the selected Garage buckets through the LAN S3 service at
`192.168.5.13:9000`. The encrypted dataset is
`HomeLab/Kubernetes-Object-Backups`. These are TrueNAS Cloud Sync tasks, not
rsync tasks: rsync cannot enumerate or authenticate against the S3 API.

| Bucket | TrueNAS path | Daily start |
| --- | --- | --- |
| `mimir-bucket` | `mimir-bucket/` | 00:00 |
| `loki-bucket` | `loki-bucket/` | 00:15 |
| `loki-chunks` | `loki-chunks/` | 00:30 |
| `loki-ruler` | `loki-ruler/` | 00:45 |
| `loki-admin` | `loki-admin/` | 01:00 |
| `tempo-bucket` | `tempo-bucket/` | 01:15 |
| `postgres-backup` | `postgres-backup/` | 01:30 |

Each task pulls with `SYNC` transfer mode. S3 signatures must use region
`garage`; the TrueNAS S3 credential must have `skip_region` disabled. The
Garage LAN NetworkPolicy permits TrueNAS (`192.168.5.135/32`).

A daily ZFS snapshot of the dataset runs at 04:00 and is retained for seven
days. The snapshot protects a recent copy when the source deletes an object
and the next sync mirrors that deletion. It does not replace a separate
off-site backup. Check that all Cloud Sync tasks completed successfully before
relying on the snapshot for a restore point.

To restore, first identify a complete Cloud Sync run and matching ZFS snapshot.
Restore the selected bucket objects from the snapshot to a staging location,
then upload them to the appropriate Garage bucket using S3 credentials scoped
to that bucket. Verify the application against the restored data before
resuming writes. For PostgreSQL, use the CloudNativePG restore workflow with
the base backup and WAL archive under `postgres-backup/postgres-18/`; copying
objects alone does not restore a running database.
