// Live Stats React Component

import { useState, useEffect } from 'react';
import { fetchPoolState, formatUSDC } from '../lib/pool';
import type { PoolState } from '../lib/types';

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  highlight?: boolean;
}

function StatCard({ label, value, subtext, highlight }: StatCardProps) {
  return (
    <div className="stat-card">
      <div className="text-xs text-[--color-text-dim] uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className={`text-2xl font-bold ${highlight ? 'glow-text' : 'text-[--color-text]'}`}>
        {value}
      </div>
      {subtext && (
        <div className="text-xs text-[--color-text-dim] mt-1">{subtext}</div>
      )}
    </div>
  );
}

export function LiveStats() {
  const [state, setState] = useState<PoolState | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    const load = async () => {
      const data = await fetchPoolState();
      if (data) {
        setState(data);
        setLastUpdate(new Date());
      }
      setLoading(false);
    };

    // Initial load
    load();

    // Poll every 10 seconds
    const interval = setInterval(load, 10000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="stat-card animate-pulse">
            <div className="h-4 bg-[--color-border] rounded w-20 mb-2"></div>
            <div className="h-8 bg-[--color-border] rounded w-24"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!state) {
    return (
      <div className="terminal-box p-6 text-center">
        <p className="text-[--color-red]">Failed to load pool state</p>
        <p className="text-sm text-[--color-text-dim] mt-2">Check connection and try again</p>
      </div>
    );
  }

  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Jobs"
          value={state.total_jobs.toLocaleString()}
          subtext={`${state.stats.jobs_per_hour}/hr`}
          highlight
        />
        <StatCard
          label="Total Volume"
          value={formatUSDC(state.total_volume_usdc)}
          subtext="All time"
        />
        <StatCard
          label="Active Miners"
          value={state.stats.active_miner_count}
          subtext={`${state.active_miners.length} registered`}
          highlight
        />
        <StatCard
          label="Pending Jobs"
          value={state.stats.pending_job_count}
          subtext={`~${state.stats.avg_completion_time.toFixed(1)}s avg`}
        />
      </div>

      {lastUpdate && (
        <div className="text-xs text-[--color-text-dim] mt-4 text-right">
          Updated: {lastUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}

export function EpochStats() {
  const [state, setState] = useState<PoolState | null>(null);

  useEffect(() => {
    fetchPoolState().then(setState);
    const interval = setInterval(async () => {
      const data = await fetchPoolState();
      if (data) setState(data);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!state) return null;

  const epoch = state.current_epoch;
  const progress = epoch.jobs_completed;
  const volume = parseFloat(epoch.total_volume_usdc);

  return (
    <div className="terminal-box p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold glow-text">{epoch.epoch_id.toUpperCase()}</span>
          <span className="tag tag-live pulse">ACTIVE</span>
        </div>
        <div className="text-sm text-[--color-text-dim]">
          Started: {new Date(epoch.started_at).toLocaleDateString()}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6 mb-4">
        <div>
          <div className="text-xs text-[--color-text-dim] uppercase">Jobs Completed</div>
          <div className="text-xl font-bold text-[--color-cyan]">{progress}</div>
        </div>
        <div>
          <div className="text-xs text-[--color-text-dim] uppercase">Volume</div>
          <div className="text-xl font-bold text-[--color-green]">{formatUSDC(volume)}</div>
        </div>
        <div>
          <div className="text-xs text-[--color-text-dim] uppercase">Miners Paid</div>
          <div className="text-xl font-bold">{epoch.miners_paid}</div>
        </div>
      </div>

      <div className="text-xs text-[--color-text-dim]">
        Settlement: 75% Miners | 25% Hive Ops
      </div>
    </div>
  );
}
