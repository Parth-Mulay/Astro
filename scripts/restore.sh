#!/bin/bash
set -e

# Restore script for AstroMatch: Restore SQLite DB, Uploads, Reports, Logs from tar.gz

echo "=== Starting AstroMatch Restore ==="

# 1. Validate arguments
BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "ERROR: No backup file specified!"
    echo "Usage: ./restore.sh backups/astromatch_backup_YYYYMMDD_HHMMSS.tar.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file '$BACKUP_FILE' not found!"
    exit 1
fi

# 2. Warning and Confirmation
echo "WARNING: Restoring will overwrite current database, uploads, reports, and logs!"
read -p "Are you absolutely sure you want to proceed? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Restore cancelled by user."
    exit 0
fi

# 3. Extract Archive
echo "Restoring from $BACKUP_FILE..."
tar -xzf "$BACKUP_FILE" -C .

echo "=== Restore Process Completed Successfully ==="
echo "Please restart the AstroMatch application to apply all restored states."
