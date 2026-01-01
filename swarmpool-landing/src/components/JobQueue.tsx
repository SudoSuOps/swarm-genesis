// Job Queue Component

import { useState, useEffect } from 'react';
import { fetchPoolState, formatRelativeTime, truncateENS, formatUSDC } from '../lib/pool';
import type { PoolState, Job } from '../lib/types';

function JobRow({ job, type }: { job: Job; type: 'pending' | 'completed' }) {
  const isPending = type === 'pending';

  return (
    <div className="flex items-center justify-between py-3 border-b border-[--color-border] last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-xs ${isPending ? 'tag-pending' : 'tag-live'} tag`}>
            {isPending ? 'PENDING' : 'DONE'}
          </span>
          <code className="text-sm text-[--color-cyan] truncate">
            {job.job_id.slice(0, 12)}...
          </code>
        </div>
        <div className="text-xs text-[--color-text-dim] mt-1">
          {job.model} • {truncateENS(job.client, 16)}
        </div>
      </div>
      <div className="text-right">
        <div className="text-sm font-medium text-[--color-green]">
          {formatUSDC(job.price_usdc)}
        </div>
        <div className="text-xs text-[--color-text-dim]">
          {formatRelativeTime(job.submitted_at)}
        </div>
      </div>
    </div>
  );
}

export function PendingJobs() {
  const [state, setState] = useState<PoolState | null>(null);

  useEffect(() => {
    fetchPoolState().then(setState);
    const interval = setInterval(async () => {
      const data = await fetchPoolState();
      if (data) setState(data);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!state) return null;

  const pending = state.pending_jobs || [];

  return (
    <div className="terminal-box overflow-hidden">
      <div className="p-4 border-b border-[--color-border] flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-[--color-amber]">PENDING JOBS</h3>
          <p className="text-sm text-[--color-text-dim]">Waiting for miners</p>
        </div>
        <div className="text-2xl font-bold text-[--color-amber]">
          {pending.length}
        </div>
      </div>
      <div className="p-4 max-h-80 overflow-y-auto">
        {pending.length === 0 ? (
          <div className="text-center py-8 text-[--color-text-dim]">
            <p>No pending jobs</p>
            <p className="text-sm mt-1">All jobs are being processed</p>
          </div>
        ) : (
          pending.slice(0, 10).map((job) => (
            <JobRow key={job.job_id} job={job} type="pending" />
          ))
        )}
      </div>
    </div>
  );
}

export function RecentCompletions() {
  const [state, setState] = useState<PoolState | null>(null);

  useEffect(() => {
    fetchPoolState().then(setState);
    const interval = setInterval(async () => {
      const data = await fetchPoolState();
      if (data) setState(data);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!state) return null;

  const completions = state.recent_completions || [];

  return (
    <div className="terminal-box overflow-hidden">
      <div className="p-4 border-b border-[--color-border] flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold glow-text">RECENT COMPLETIONS</h3>
          <p className="text-sm text-[--color-text-dim]">Latest verified proofs</p>
        </div>
        <div className="text-2xl font-bold glow-text">
          {completions.length}
        </div>
      </div>
      <div className="p-4 max-h-80 overflow-y-auto">
        {completions.length === 0 ? (
          <div className="text-center py-8 text-[--color-text-dim]">
            <p>No recent completions</p>
          </div>
        ) : (
          completions.slice(0, 10).map((job) => (
            <JobRow key={job.job_id} job={job} type="completed" />
          ))
        )}
      </div>
    </div>
  );
}

export function JobFeed() {
  const [state, setState] = useState<PoolState | null>(null);

  useEffect(() => {
    fetchPoolState().then(setState);
    const interval = setInterval(async () => {
      const data = await fetchPoolState();
      if (data) setState(data);
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  if (!state) return null;

  // Combine and sort by time
  const allJobs = [
    ...state.pending_jobs.map(j => ({ ...j, _type: 'pending' as const })),
    ...state.recent_completions.map(j => ({ ...j, _type: 'completed' as const })),
  ].sort((a, b) =>
    new Date(b.submitted_at).getTime() - new Date(a.submitted_at).getTime()
  );

  return (
    <div className="terminal-box overflow-hidden">
      <div className="p-4 border-b border-[--color-border]">
        <h3 className="text-lg font-bold glow-text cursor-blink">LIVE FEED</h3>
      </div>
      <div className="divide-y divide-[--color-border] max-h-96 overflow-y-auto">
        {allJobs.slice(0, 15).map((job) => (
          <div
            key={job.job_id}
            className={`p-3 ${job._type === 'completed' ? 'bg-[--color-green-dark]/10' : ''}`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={job._type === 'pending' ? 'status-busy' : 'status-online'}>
                  {job._type === 'pending' ? '◐' : '●'}
                </span>
                <code className="text-xs">{job.job_id.slice(0, 8)}</code>
                <span className="text-xs text-[--color-text-dim]">{job.model}</span>
              </div>
              <span className="text-xs text-[--color-green]">{formatUSDC(job.price_usdc)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
