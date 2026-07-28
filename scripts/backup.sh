#!/bin/bash
set -e

# Backup script for AstroMatch: SQLite DB, Uploads, Reports, Logs

echo "=== Starting AstroMatch Backup ==="

# 1. Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
else
    # Fallback default if running in cron without Cwd
    export LOGS_DIR="logs"
    export UPLOADS_DIR="uploads"
    export REPORTS_DIR="reports"
    export DATABASE_URL="sqlite:////data/app.db"
fi

BACKUP_DIR="backups"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/astromatch_backup_$TIMESTAMP.tar.gz"

# 2. Resolve database path
DB_PATH=$(python3 -c "
import os
url = os.getenv('DATABASE_URL', 'sqlite:////data/app.db')
if url.startswith('sqlite:///./'):
    print(url.replace('sqlite:///./', ''))
elif url.startswith('sqlite:////'):
    print(url.replace('sqlite:////', '/'))
else:
    print(url.replace('sqlite:///', ''))
" 2>/dev/null || echo "/data/app.db")

echo "Resolved DB Path: $DB_PATH"

if [ ! -f "$DB_PATH" ]; then
    echo "WARNING: SQLite database file not found at $DB_PATH. Proceeding with files backup only."
    DB_PATH=""
fi

# 3. Create compressed archive
echo "Archiving files to $BACKUP_FILE..."
if [ -n "$DB_PATH" ]; then
    tar -czf "$BACKUP_FILE" "$DB_PATH" "$UPLOADS_DIR" "$REPORTS_DIR" "$LOGS_DIR"
else
    tar -czf "$BACKUP_FILE" "$UPLOADS_DIR" "$REPORTS_DIR" "$LOGS_DIR"
fi

echo "Backup created successfully: $BACKUP_FILE"

# 4. Prune / Rotate backups: Keep only the 7 most recent backups
echo "Pruning old backups..."
find "$BACKUP_DIR" -name "astromatch_backup_*.tar.gz" -type f | sort -r | tail -n +8 | xargs -I {} rm -f -- {}

echo "Backup rotation completed. Only the last 7 backups are retained."
echo "=== Backup Process Finished ==="
