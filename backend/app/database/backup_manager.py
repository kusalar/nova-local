import os
import shutil
import hashlib
import sqlite3
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config import settings
from .db_manager import db_manager

logger = logging.getLogger("nova.database.backup")

class BackupManager:
    """
    Manages automated and manual SQLite backups, integrity validation,
    retention policies, and transactional rollback restoration for NOVA v0.9.
    """

    def __init__(self, backup_dir: Optional[str] = None, default_db_path: Optional[str] = None):
        self.default_db_path = default_db_path or settings.DATABASE_PATH
        self.backup_dir = backup_dir or os.path.join(settings.ROOT_DIR, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)
        self.max_retention = 15  # Default keep last 15 backups

    def _compute_sha256(self, filepath: str) -> str:
        """Computes SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def create_backup(
        self, 
        trigger: str = "manual", 
        description: Optional[str] = None,
        db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates an online, safe SQLite backup using SQLite's backup API
        to avoid tearing or partial writes.
        """
        source_path = db_path or self.default_db_path
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source database '{source_path}' does not exist.")

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_id = f"backup_{timestamp_str}_{uuid.uuid4().hex[:6]}"
        backup_filename = f"{backup_id}.db"
        target_path = os.path.join(self.backup_dir, backup_filename)
        meta_filename = f"{backup_id}.meta.json"
        meta_path = os.path.join(self.backup_dir, meta_filename)

        logger.info(f"Initiating database backup [{trigger}] -> {target_path}...")

        # 1. Use SQLite's backup API for consistent, online backup
        source_conn = db_manager.get_connection(source_path)
        dest_conn = sqlite3.connect(target_path)
        try:
            with dest_conn:
                source_conn.backup(dest_conn, pages=-1)
        finally:
            dest_conn.close()
            source_conn.close()

        # 2. Verify integrity of the backup file immediately
        integrity = db_manager.check_integrity(target_path)
        if not integrity.get("healthy"):
            # Backup corrupted during creation -> remove and fail
            if os.path.exists(target_path):
                os.remove(target_path)
            raise RuntimeError(f"Backup integrity verification failed: {integrity.get('messages')}")

        # 3. Read metadata and compute SHA-256
        file_size = os.path.getsize(target_path)
        sha256_hash = self._compute_sha256(target_path)
        db_status = db_manager.get_database_status(target_path)

        metadata = {
            "backup_id": backup_id,
            "filename": backup_filename,
            "path": target_path,
            "trigger": trigger,
            "description": description or f"NOVA database backup ({trigger})",
            "created_at": datetime.now().isoformat(),
            "size_bytes": file_size,
            "sha256": sha256_hash,
            "app_version": settings.VERSION,
            "tables_count": db_status.get("tables_count", 0),
            "total_records": db_status.get("total_records", 0),
            "table_counts": db_status.get("table_counts", {}),
            "healthy": True
        }

        # 4. Save metadata JSON alongside backup
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Backup '{backup_id}' successfully created ({file_size} bytes, SHA256: {sha256_hash[:12]}...).")

        # 5. Apply retention pruning
        self._prune_old_backups()

        return metadata

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups sorted newest first."""
        backups = []
        if not os.path.exists(self.backup_dir):
            return []

        for fname in os.listdir(self.backup_dir):
            if fname.endswith(".meta.json"):
                meta_path = os.path.join(self.backup_dir, fname)
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    db_file = os.path.join(self.backup_dir, meta.get("filename", ""))
                    meta["file_exists"] = os.path.exists(db_file)
                    backups.append(meta)
                except Exception as e:
                    logger.warning(f"Failed reading backup meta '{fname}': {e}")

        # Sort descending by creation date
        backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return backups

    def validate_backup(self, backup_id: str) -> Dict[str, Any]:
        """
        Validates a backup's existence, SHA-256 checksum match, and SQLite integrity.
        """
        meta_path = os.path.join(self.backup_dir, f"{backup_id}.meta.json")
        if not os.path.exists(meta_path):
            return {"valid": False, "error": f"Backup metadata '{backup_id}' not found."}

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        backup_file = os.path.join(self.backup_dir, meta.get("filename", ""))
        if not os.path.exists(backup_file):
            return {"valid": False, "error": f"Backup database file '{backup_file}' does not exist on disk."}

        # Verify hash
        actual_hash = self._compute_sha256(backup_file)
        expected_hash = meta.get("sha256")
        if expected_hash and actual_hash != expected_hash:
            return {
                "valid": False, 
                "error": f"Checksum mismatch! Expected {expected_hash}, calculated {actual_hash}."
            }

        # Verify SQLite integrity
        integrity = db_manager.check_integrity(backup_file)
        if not integrity.get("healthy"):
            return {
                "valid": False,
                "error": f"SQLite corruption detected: {integrity.get('messages')}"
            }

        return {
            "valid": True,
            "backup_id": backup_id,
            "filename": meta.get("filename"),
            "size_bytes": os.path.getsize(backup_file),
            "sha256": actual_hash,
            "tables_count": meta.get("tables_count", 0),
            "total_records": meta.get("total_records", 0),
            "created_at": meta.get("created_at")
        }

    def restore_preview(self, backup_id: str, target_db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Provides a comparative dry-run preview before executing database restoration.
        """
        validation = self.validate_backup(backup_id)
        if not validation.get("valid"):
            return {"can_restore": False, "error": validation.get("error")}

        target = target_db_path or self.default_db_path
        current_status = db_manager.get_database_status(target)

        backup_file = os.path.join(self.backup_dir, validation.get("filename", ""))
        backup_status = db_manager.get_database_status(backup_file)

        # Generate a confirmation token for restore execution
        confirmation_token = f"restore_confirm_{uuid.uuid4().hex[:12]}"

        return {
            "can_restore": True,
            "backup_id": backup_id,
            "confirmation_token": confirmation_token,
            "target_database": target,
            "current_state": {
                "size_bytes": current_status.get("size_bytes", 0),
                "total_records": current_status.get("total_records", 0),
                "tables_count": current_status.get("tables_count", 0),
                "healthy": current_status.get("healthy", False)
            },
            "backup_state": {
                "size_bytes": backup_status.get("size_bytes", 0),
                "total_records": backup_status.get("total_records", 0),
                "tables_count": backup_status.get("tables_count", 0),
                "created_at": validation.get("created_at")
            },
            "warning": (
                "Restoring will replace the active database. A safety snapshot "
                "of your current database will be saved automatically prior to restore."
            )
        }

    def restore_backup(
        self, 
        backup_id: str, 
        confirmed: bool = False,
        target_db_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes safe database restoration.
        Never overwrites current database without taking an immediate pre-restore snapshot first.
        """
        if not confirmed:
            raise PermissionError("Explicit confirmation (confirmed=True) is required to restore database.")

        validation = self.validate_backup(backup_id)
        if not validation.get("valid"):
            raise ValueError(f"Cannot restore invalid backup: {validation.get('error')}")

        target = target_db_path or self.default_db_path
        backup_file = os.path.join(self.backup_dir, validation.get("filename", ""))

        # 1. Take safety snapshot of current active DB
        safety_meta = None
        if os.path.exists(target):
            safety_meta = self.create_backup(
                trigger="pre_restore_safety",
                description=f"Automated safety snapshot before restoring {backup_id}",
                db_path=target
            )

        # 2. Copy backup into temporary staging location first
        staging_path = f"{target}.restoring"
        try:
            shutil.copy2(backup_file, staging_path)

            # Check integrity of staged file
            staged_integrity = db_manager.check_integrity(staging_path)
            if not staged_integrity.get("healthy"):
                raise RuntimeError("Staged restoration file failed integrity check. Aborting.")

            # 3. Clean up existing WAL/SHM files to avoid lock/WAL mismatch
            for suffix in ["-wal", "-shm"]:
                wal_aux = f"{target}{suffix}"
                if os.path.exists(wal_aux):
                    try:
                        os.remove(wal_aux)
                    except Exception as e:
                        logger.warning(f"Could not remove aux file {wal_aux}: {e}")

            # 4. Atomic file replacement
            if os.path.exists(target):
                os.replace(staging_path, target)
            else:
                shutil.move(staging_path, target)

            logger.info(f"Database successfully restored from '{backup_id}'.")

            # 5. Reset DB manager connection state and re-verify
            db_manager._initialized_paths.discard(target)
            new_status = db_manager.get_database_status(target)

            return {
                "success": True,
                "restored_backup_id": backup_id,
                "safety_backup_id": safety_meta.get("backup_id") if safety_meta else None,
                "timestamp": datetime.now().isoformat(),
                "new_status": new_status
            }

        except Exception as e:
            if os.path.exists(staging_path):
                os.remove(staging_path)
            logger.error(f"Restoration failed: {e}")
            raise RuntimeError(f"Database restoration failed: {str(e)}")

    def _prune_old_backups(self):
        """Retains up to max_retention backups, pruning oldest manual/auto backups."""
        backups = self.list_backups()
        if len(backups) <= self.max_retention:
            return

        to_prune = backups[self.max_retention:]
        for b in to_prune:
            # Don't prune pre_restore_safety snapshots if possible
            if b.get("trigger") == "pre_restore_safety":
                continue
            backup_id = b.get("backup_id")
            db_file = os.path.join(self.backup_dir, b.get("filename", ""))
            meta_file = os.path.join(self.backup_dir, f"{backup_id}.meta.json")

            try:
                if os.path.exists(db_file):
                    os.remove(db_file)
                if os.path.exists(meta_file):
                    os.remove(meta_file)
                logger.info(f"Pruned old backup: {backup_id}")
            except Exception as e:
                logger.warning(f"Failed pruning {backup_id}: {e}")

backup_manager = BackupManager()
