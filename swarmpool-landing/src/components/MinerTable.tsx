// Miner Table / Leaderboard Component

import { useState, useEffect } from 'react';
import { fetchPoolState, getLeaderboard, truncateENS, getStatusClass, getStatusIcon, formatUSDC } from '../lib/pool';
import type { PoolState, LeaderboardEntry, MinerInfo } from '../lib/types';

interface MinerRowProps {
  miner: MinerInfo;
  rank: number;
}

function MinerRow({ miner, rank }: MinerRowProps) {
  const statusClass = getStatusClass(miner.status);
  const statusIcon = getStatusIcon(miner.status);

  return (
    <tr>
      <td className="text-[--color-text-dim]">#{rank}</td>
      <td>
        <span className={statusClass}>{statusIcon}</span>
        <span className="ml-2">{truncateENS(miner.ens, 24)}</span>
      </td>
      <td className="text-[--color-text-dim] hidden md:table-cell">{miner.gpu}</td>
      <td className="text-[--color-cyan]">{miner.jobs_completed.toLocaleString()}</td>
      <td className="text-[--color-green] hidden sm:table-cell">{formatUSDC(miner.total_earned)}</td>
      <td className="hidden lg:table-cell">
        <span className={miner.uptime_percent >= 99 ? 'text-[--color-green]' : 'text-[--color-text-dim]'}>
          {miner.uptime_percent.toFixed(1)}%
        </span>
      </td>
    </tr>
  );
}

export function MinerLeaderboard() {
  const [state, setState] = useState<PoolState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const data = await fetchPoolState();
      if (data) setState(data);
      setLoading(false);
    };
    load();

    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="terminal-box p-6">
        <div className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 bg-[--color-border] rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!state || state.active_miners.length === 0) {
    return (
      <div className="terminal-box p-6 text-center">
        <p className="text-[--color-text-dim]">No active miners</p>
      </div>
    );
  }

  const sortedMiners = [...state.active_miners].sort(
    (a, b) => b.jobs_completed - a.jobs_completed
  );

  return (
    <div className="terminal-box overflow-hidden">
      <div className="p-4 border-b border-[--color-border]">
        <h3 className="text-lg font-bold glow-text">MINER LEADERBOARD</h3>
        <p className="text-sm text-[--color-text-dim]">
          Top performers by jobs completed
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Miner</th>
              <th className="hidden md:table-cell">GPU</th>
              <th>Jobs</th>
              <th className="hidden sm:table-cell">Earned</th>
              <th className="hidden lg:table-cell">Uptime</th>
            </tr>
          </thead>
          <tbody>
            {sortedMiners.slice(0, 10).map((miner, index) => (
              <MinerRow key={miner.ens} miner={miner} rank={index + 1} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ActiveMiners() {
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

  const onlineMiners = state.active_miners.filter(m => m.status === 'online');
  const busyMiners = state.active_miners.filter(m => m.status === 'busy');
  const offlineMiners = state.active_miners.filter(m => m.status === 'offline');

  return (
    <div className="terminal-box p-6">
      <h3 className="text-lg font-bold glow-text mb-4">MINER STATUS</h3>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold status-online">{onlineMiners.length}</div>
          <div className="text-xs text-[--color-text-dim]">Online</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold status-busy">{busyMiners.length}</div>
          <div className="text-xs text-[--color-text-dim]">Busy</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold status-offline">{offlineMiners.length}</div>
          <div className="text-xs text-[--color-text-dim]">Offline</div>
        </div>
      </div>

      <div className="space-y-2">
        {state.active_miners.slice(0, 5).map((miner) => (
          <div
            key={miner.ens}
            className="flex items-center justify-between py-2 border-b border-[--color-border] last:border-0"
          >
            <div className="flex items-center gap-2">
              <span className={getStatusClass(miner.status)}>
                {getStatusIcon(miner.status)}
              </span>
              <span className="text-sm">{truncateENS(miner.ens, 18)}</span>
            </div>
            <div className="text-xs text-[--color-text-dim]">
              {miner.gpu}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
