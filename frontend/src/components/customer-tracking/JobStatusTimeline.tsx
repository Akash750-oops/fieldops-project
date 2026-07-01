import React, { useEffect, useState, useRef } from 'react';
import api from '../../services/api';
import { TimelineItem, type TransitionHistoryItem } from './TimelineItem';
import { Loader2, RefreshCw, History, CalendarClock } from 'lucide-react';

interface JobStatusTimelineProps {
  jobId: string | number;
  currentStatus: string;
}

export const SkeletonTimeline: React.FC = () => {
  return (
    <div className="flex flex-col gap-4 w-full animate-pulse select-none" data-testid="timeline-skeleton">
      {[1, 2, 3].map((n) => (
        <div key={n} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className="w-4 h-4 rounded-full bg-slate-200 dark:bg-slate-700" />
            {n < 3 && <div className="w-0.5 flex-1 bg-slate-100 dark:bg-slate-800 my-1 min-h-[40px]" />}
          </div>
          <div className="flex-1 bg-slate-50 dark:bg-slate-800/50 border border-slate-100/50 dark:border-slate-800 rounded-xl h-16" />
        </div>
      ))}
    </div>
  );
};

export const JobStatusTimeline: React.FC<JobStatusTimelineProps> = ({ jobId, currentStatus }) => {
  const [history, setHistory] = useState<TransitionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const containerRef = useRef<HTMLDivElement | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/jobs/${jobId}/history`);
      setHistory(response.data || []);
    } catch (e) {
      console.error('[JobStatusTimeline] Error loading status history:', e);
      setError('Failed to fetch status transition timeline history.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchHistory();
    }
  }, [jobId]);

  // Scroll to the active pulsing timeline item
  useEffect(() => {
    if (!loading && history.length > 0) {
      const timer = setTimeout(() => {
        const activeEl = containerRef.current?.querySelector('.timeline-item-active');
        if (activeEl) {
          activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [loading, history]);

  if (loading) {
    return (
      <div className="flex flex-col p-4 w-full">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5">
          <History size={13} />
          Status History
        </h4>
        <SkeletonTimeline />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-850 rounded-xl gap-3 w-full">
        <span className="text-xs text-rose-500 font-semibold">{error}</span>
        <button
          onClick={fetchHistory}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold rounded-lg shadow-sm transition cursor-pointer"
        >
          <RefreshCw size={11} className="shrink-0" />
          Retry Fetching
        </button>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center bg-slate-50/50 dark:bg-slate-900/30 border border-slate-100/50 dark:border-slate-850 rounded-xl gap-2 w-full">
        <CalendarClock className="w-8 h-8 text-slate-300 mx-auto mb-1" />
        <span className="text-slate-900 dark:text-slate-100 font-bold text-sm">No status changes</span>
        <span className="text-slate-400 text-xs max-w-xs">No status transitions recorded yet for this job ID.</span>
      </div>
    );
  }

  // Find index of current status or fallback to last item in history
  const activeIdx = history.findIndex((h) => h.to_status.toUpperCase() === currentStatus.toUpperCase());
  const finalActiveIdx = activeIdx !== -1 ? activeIdx : history.length - 1;

  return (
    <div className="flex flex-col w-full h-full" ref={containerRef}>
      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-1.5 select-none">
        <History size={13} />
        Status History
      </h4>
      <div className="flex-1 overflow-y-auto pr-1 max-h-[360px] custom-scrollbar scroll-smooth">
        {history.map((item, idx) => (
          <TimelineItem
            key={item.id}
            item={item}
            isCurrent={idx === finalActiveIdx}
            isLast={idx === history.length - 1}
          />
        ))}
      </div>
    </div>
  );
};

export default JobStatusTimeline;
