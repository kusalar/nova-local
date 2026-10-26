import React, { useState, useEffect } from 'react';
import { 
  Archive, 
  Plus, 
  RotateCcw, 
  ShieldCheck, 
  CheckCircle, 
  X, 
  RefreshCw, 
  AlertTriangle, 
  HardDrive,
  Calendar,
  Lock
} from 'lucide-react';
import { BackupMetadata, RestorePreview } from '../../types';
import { apiService } from '../../services/api';

export const BackupManager: React.FC = () => {
  const [backups, setBackups] = useState<BackupMetadata[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [newDesc, setNewDesc] = useState<string>('');
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Restore Modal State
  const [restorePreview, setRestorePreview] = useState<RestorePreview | null>(null);
  const [restoring, setRestoring] = useState<boolean>(false);

  const loadBackups = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await apiService.listDatabaseBackups();
      setBackups(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load backups');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBackups();
  }, []);

  const handleCreateBackup = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await apiService.createDatabaseBackup(newDesc.trim() || undefined);
      setIsCreating(false);
      setNewDesc('');
      setSuccessMsg('Database backup created successfully.');
      setTimeout(() => setSuccessMsg(null), 3000);
      loadBackups();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create backup');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async (backupId: string) => {
    try {
      const res = await apiService.validateDatabaseBackup(backupId);
      if (res.valid) {
        setSuccessMsg(`Backup '${backupId}' verified: Integrity OK, SHA-256 match.`);
      } else {
        setErrorMsg(`Backup validation error: ${res.error}`);
      }
      setTimeout(() => {
        setSuccessMsg(null);
        setErrorMsg(null);
      }, 4000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to validate backup');
    }
  };

  const handlePreviewRestore = async (backupId: string) => {
    try {
      setErrorMsg(null);
      const preview = await apiService.previewDatabaseRestore(backupId);
      setRestorePreview(preview);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to preview restore');
    }
  };

  const handleExecuteRestore = async () => {
    if (!restorePreview) return;
    try {
      setRestoring(true);
      await apiService.executeDatabaseRestore(restorePreview.backup_id, true);
      setRestorePreview(null);
      setSuccessMsg('Database restored successfully from backup.');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadBackups();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to restore database');
    } finally {
      setRestoring(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Banner and Actions */}
      <div className="p-3.5 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-mono text-nova-cyan">
          <Archive className="w-4 h-4" />
          <span>TRANSACTIONAL DATABASE BACKUP & RESTORE RECOVERY</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadBackups}
            className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
            title="Refresh backups"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => setIsCreating(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-nova-cyan/20 border border-nova-cyan/50 text-nova-cyan hover:bg-nova-cyan/30 text-xs font-mono tracking-wider transition-all shadow-[0_0_10px_rgba(0,240,255,0.15)]"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>CREATE BACKUP</span>
          </button>
        </div>
      </div>

      {successMsg && (
        <div className="p-3 rounded bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 text-xs font-mono flex items-center gap-2">
          <CheckCircle className="w-3.5 h-3.5" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)}><X className="w-3.5 h-3.5" /></button>
        </div>
      )}

      {/* Create Backup Form */}
      {isCreating && (
        <form onSubmit={handleCreateBackup} className="p-4 rounded-xl bg-nova-dark/95 border border-nova-cyan/40 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-nova-border/60 pb-2">
            <h4 className="text-xs font-mono text-nova-cyan uppercase tracking-wider flex items-center gap-2">
              <Archive className="w-3.5 h-3.5" />
              Create SQLite Online Backup
            </h4>
            <button
              type="button"
              onClick={() => setIsCreating(false)}
              className="text-slate-400 hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div>
            <label className="block text-xs font-mono text-slate-400 mb-1">
              Backup Description / Note (Optional)
            </label>
            <input
              type="text"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder="e.g. Pre-refactor milestone snapshot"
              className="w-full bg-nova-surface border border-nova-border rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-nova-cyan"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-nova-border/60">
            <button
              type="button"
              onClick={() => setIsCreating(false)}
              className="px-3 py-1 rounded text-xs font-mono text-slate-400 hover:text-slate-200"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded bg-nova-cyan text-nova-dark font-mono font-semibold text-xs tracking-wider hover:bg-nova-teal transition-all flex items-center gap-1.5"
            >
              <span>EXECUTE BACKUP</span>
            </button>
          </div>
        </form>
      )}

      {/* Restore Confirmation Modal */}
      {restorePreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg p-5 rounded-xl bg-nova-dark border border-amber-500/60 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-nova-border/60 pb-2">
              <div className="flex items-center gap-2 text-amber-400 font-mono text-xs font-bold uppercase tracking-wider">
                <AlertTriangle className="w-4 h-4" />
                <span>Confirm Database Restoration</span>
              </div>
              <button
                onClick={() => setRestorePreview(null)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs font-mono text-amber-200/90 leading-relaxed">
              {restorePreview.warning}
            </p>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded bg-nova-surface border border-nova-border/70">
                <span className="text-[10px] text-slate-400 block mb-1">ACTIVE DATABASE</span>
                <div>Records: {restorePreview.current_state?.total_records}</div>
                <div>Tables: {restorePreview.current_state?.tables_count}</div>
              </div>

              <div className="p-3 rounded bg-nova-surface border border-nova-border/70">
                <span className="text-[10px] text-slate-400 block mb-1">BACKUP TO RESTORE</span>
                <div>Records: {restorePreview.backup_state?.total_records}</div>
                <div>Tables: {restorePreview.backup_state?.tables_count}</div>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-nova-border/60">
              <button
                type="button"
                onClick={() => setRestorePreview(null)}
                className="px-3 py-1.5 rounded text-xs font-mono text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteRestore}
                disabled={restoring}
                className="px-4 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white font-mono text-xs font-semibold tracking-wider transition-all flex items-center gap-1.5"
              >
                <RotateCcw className={`w-3.5 h-3.5 ${restoring ? 'animate-spin' : ''}`} />
                <span>{restoring ? 'RESTORING...' : 'CONFIRM & RESTORE'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Backups List */}
      {backups.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-nova-border/50 rounded-xl text-slate-500 font-mono text-xs">
          No database backups recorded yet. Click "Create Backup" to save an online snapshot.
        </div>
      ) : (
        <div className="space-y-2.5">
          {backups.map((b) => (
            <div
              key={b.backup_id}
              className="p-3.5 rounded-xl bg-nova-surface/40 hover:bg-nova-surface/60 border border-nova-border/60 transition-all flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-slate-100">{b.backup_id}</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-nova-dark border border-nova-border text-nova-cyan uppercase">
                    {b.trigger}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    ({(b.size_bytes / 1024).toFixed(1)} KB · {b.total_records} records)
                  </span>
                </div>
                <p className="text-[11px] text-slate-400">{b.description}</p>
                <p className="text-[9px] text-slate-500 select-all font-mono mt-0.5">
                  SHA256: {b.sha256}
                </p>
              </div>

              <div className="flex items-center gap-2 self-end md:self-center">
                <button
                  onClick={() => handleValidate(b.backup_id)}
                  className="px-2.5 py-1 rounded bg-nova-surface hover:bg-nova-surface/80 border border-nova-border text-slate-300 hover:text-nova-cyan transition-colors text-xs flex items-center gap-1"
                  title="Verify checksum and SQLite integrity"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Verify</span>
                </button>

                <button
                  onClick={() => handlePreviewRestore(b.backup_id)}
                  className="px-2.5 py-1 rounded bg-amber-950/70 hover:bg-amber-900/80 border border-amber-500/40 text-amber-300 transition-colors text-xs flex items-center gap-1"
                  title="Restore database from this snapshot"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Restore</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
