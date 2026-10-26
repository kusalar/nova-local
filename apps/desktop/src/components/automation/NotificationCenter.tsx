import React, { useState, useEffect } from 'react';
import { 
  Bell, 
  Check, 
  Clock, 
  Trash2, 
  Volume2, 
  VolumeX, 
  CheckSquare, 
  Plus, 
  AlertCircle,
  RotateCw
} from 'lucide-react';
import { NotificationItem, ReminderItem } from '../../types';
import { apiService } from '../../services/api';

export const NotificationCenter: React.FC = () => {
  const [tab, setTab] = useState<'notifications' | 'reminders'>('notifications');
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [newReminderText, setNewReminderText] = useState('');
  const [ttsEnabled, setTtsEnabled] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    try {
      const [notifs, rems, prefs] = await Promise.all([
        apiService.listNotifications(false, 50),
        apiService.listReminders(true),
        apiService.getNotificationPreferences(),
      ]);
      setNotifications(notifs);
      setReminders(rems);
      setTtsEnabled(prefs.tts_enabled || false);
    } catch (e) {
      console.error('Failed to load notifications/reminders:', e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleMarkRead = async (id: number) => {
    await apiService.markNotificationRead(id);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
  };

  const handleDismiss = async (id: number) => {
    await apiService.dismissNotification(id);
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const handleSnooze = async (id: number) => {
    await apiService.snoozeNotification(id, 15);
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const handleToggleTts = async () => {
    const nextVal = !ttsEnabled;
    setTtsEnabled(nextVal);
    await apiService.updateNotificationPreferences({ tts_enabled: nextVal });
  };

  const handleAddReminder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReminderText.trim()) return;
    try {
      const created = await apiService.createReminder(newReminderText.trim());
      setReminders(prev => [created, ...prev]);
      setNewReminderText('');
    } catch (err) {
      console.error('Failed to add reminder:', err);
    }
  };

  const handleCompleteReminder = async (id: number) => {
    await apiService.completeReminder(id);
    setReminders(prev => prev.filter(r => r.id !== id));
  };

  return (
    <div className="space-y-4 p-5 bg-slate-900/60 rounded-xl border border-cyan-500/20 shadow-lg shadow-cyan-950/20">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setTab('notifications')}
            className={`px-3 py-1 text-xs font-mono uppercase tracking-wider rounded transition-colors ${
              tab === 'notifications'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Notifications ({notifications.filter(n => !n.read).length} new)
          </button>
          <button
            onClick={() => setTab('reminders')}
            className={`px-3 py-1 text-xs font-mono uppercase tracking-wider rounded transition-colors ${
              tab === 'reminders'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Reminders ({reminders.length})
          </button>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleToggleTts}
            title={ttsEnabled ? 'Spoken TTS notifications active' : 'Spoken TTS notifications muted'}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded border transition-colors ${
              ttsEnabled
                ? 'bg-cyan-950/60 border-cyan-500/40 text-cyan-400'
                : 'border-slate-800 text-slate-500 hover:text-slate-300'
            }`}
          >
            {ttsEnabled ? <Volume2 className="w-3.5 h-3.5" /> : <VolumeX className="w-3.5 h-3.5" />}
            TTS {ttsEnabled ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      {/* NOTIFICATIONS TAB */}
      {tab === 'notifications' && (
        <div className="space-y-2.5 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
          {notifications.length === 0 ? (
            <div className="text-center py-10 text-slate-500 font-mono text-xs">
              No notifications at this time.
            </div>
          ) : (
            notifications.map(notif => (
              <div
                key={notif.id}
                className={`p-3 rounded-lg border transition-all flex items-start justify-between ${
                  notif.read
                    ? 'bg-slate-950/40 border-slate-800/80 text-slate-400'
                    : 'bg-slate-950/80 border-cyan-500/30 text-slate-100 shadow-md shadow-cyan-950/20'
                }`}
              >
                <div className="space-y-1 pr-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                      {notif.type}
                    </span>
                    <h4 className="text-xs font-bold">{notif.title}</h4>
                    <span className="text-[10px] text-slate-500 font-mono">
                      {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 whitespace-pre-wrap">{notif.message}</p>
                </div>

                <div className="flex items-center space-x-1 flex-shrink-0">
                  {!notif.read && (
                    <button
                      onClick={() => handleMarkRead(notif.id)}
                      title="Mark as read"
                      className="p-1 rounded text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition-colors"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  )}
                  <button
                    onClick={() => handleSnooze(notif.id)}
                    title="Snooze 15 minutes"
                    className="p-1 rounded text-slate-400 hover:text-amber-400 hover:bg-slate-800 transition-colors"
                  >
                    <Clock className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleDismiss(notif.id)}
                    title="Dismiss"
                    className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* REMINDERS TAB */}
      {tab === 'reminders' && (
        <div className="space-y-4">
          {/* Add Reminder Form */}
          <form onSubmit={handleAddReminder} className="flex space-x-2">
            <input
              type="text"
              placeholder="e.g. Review NOVA v0.7 architecture..."
              value={newReminderText}
              onChange={e => setNewReminderText(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-700 rounded px-3 py-1.5 text-xs text-slate-200 font-mono focus:border-cyan-400 focus:outline-none"
            />
            <button
              type="submit"
              className="px-4 py-1.5 text-xs font-mono uppercase bg-cyan-500 text-slate-950 font-bold rounded hover:bg-cyan-400 transition-colors flex items-center gap-1 shadow-md shadow-cyan-500/20"
            >
              <Plus className="w-3.5 h-3.5" />
              Add
            </button>
          </form>

          {/* Reminders List */}
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1 custom-scrollbar">
            {reminders.length === 0 ? (
              <div className="text-center py-8 text-slate-500 font-mono text-xs">
                No active smart reminders. Create one above or speak to NOVA.
              </div>
            ) : (
              reminders.map(rem => (
                <div
                  key={rem.id}
                  className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 flex items-center justify-between"
                >
                  <div className="flex items-center space-x-2.5">
                    <button
                      onClick={() => handleCompleteReminder(rem.id)}
                      className="text-slate-500 hover:text-emerald-400 transition-colors"
                    >
                      <CheckSquare className="w-4 h-4" />
                    </button>
                    <span className="text-xs text-slate-200 font-mono">{rem.text}</span>
                  </div>

                  {rem.due_at && (
                    <span className="text-[10px] text-amber-400/90 font-mono flex items-center gap-1">
                      <Clock className="w-3 h-3 text-amber-400" />
                      Due: {new Date(rem.due_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
