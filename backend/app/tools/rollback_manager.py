import os
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple
import logging
from app.tools.execution_logger import execution_logger
from app.tools.permission_manager import permission_manager

logger = logging.getLogger("nova.tools.rollback")

class RollbackError(Exception):
    pass

class RollbackManager:
    """
    Safely reverts eligible file modifications where reliable.
    Guarantees no data loss and marks execution logs accordingly.
    """

    def can_rollback(self, execution_id: str) -> Tuple[bool, str]:
        """Check if an execution record can be rolled back."""
        record = execution_logger.get_execution(execution_id)
        if not record:
            return False, "Execution record not found."
        if not record.get("is_reversible"):
            return False, f"Tool '{record.get('tool_id')}' does not support rollback."
        if record.get("is_rolled_back"):
            return False, "This operation has already been rolled back."
        if record.get("status") != "COMPLETED":
            return False, "Only successfully completed operations can be rolled back."
        if not record.get("rollback_data"):
            return False, "No rollback metadata available for this operation."
        return True, "Operation is eligible for rollback."

    def rollback(self, execution_id: str) -> Dict[str, Any]:
        """Execute rollback for the given execution ID."""
        can_rb, reason = self.can_rollback(execution_id)
        if not can_rb:
            raise RollbackError(reason)

        record = execution_logger.get_execution(execution_id)
        rb_data = record.get("rollback_data", {})
        action = rb_data.get("action")

        try:
            if action == "move_file":
                # Move file back from destination to source
                src = rb_data.get("source")
                dst = rb_data.get("destination")
                if not dst or not Path(dst).exists():
                    raise RollbackError(f"Target file '{dst}' no longer exists; cannot move back.")
                if Path(src).exists():
                    raise RollbackError(f"Original source '{src}' already exists; cannot overwrite.")
                shutil.move(dst, src)
                detail = f"Moved '{dst}' back to '{src}'"

            elif action == "rename_file":
                # Rename file back from new_path to old_path
                old_path = rb_data.get("old_path")
                new_path = rb_data.get("new_path")
                if not new_path or not Path(new_path).exists():
                    raise RollbackError(f"File '{new_path}' no longer exists; cannot rename back.")
                if Path(old_path).exists():
                    raise RollbackError(f"Original filename '{old_path}' already exists.")
                os.rename(new_path, old_path)
                detail = f"Renamed '{new_path}' back to '{old_path}'"

            elif action == "copy_file":
                # Delete copied destination file if created by us
                dst = rb_data.get("destination")
                if not dst or not Path(dst).exists():
                    raise RollbackError(f"Copied file '{dst}' no longer exists.")
                os.remove(dst)
                detail = f"Deleted copied file '{dst}'"

            elif action == "create_folder":
                # Remove created directory only if still empty
                target_dir = rb_data.get("directory")
                if not target_dir or not Path(target_dir).exists():
                    raise RollbackError(f"Directory '{target_dir}' no longer exists.")
                p = Path(target_dir)
                if any(p.iterdir()):
                    raise RollbackError(f"Directory '{target_dir}' is not empty; refusing to delete.")
                p.rmdir()
                detail = f"Removed empty directory '{target_dir}'"

            else:
                raise RollbackError(f"Unsupported rollback action '{action}'")

            execution_logger.mark_rolled_back(execution_id)
            logger.info(f"Rollback successful for '{execution_id}': {detail}")

            return {
                "success": True,
                "execution_id": execution_id,
                "action": action,
                "detail": detail
            }

        except Exception as e:
            logger.error(f"Rollback failed for '{execution_id}': {e}")
            raise RollbackError(f"Rollback failed: {str(e)}")

rollback_manager = RollbackManager()
