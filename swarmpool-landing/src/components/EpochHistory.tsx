// Epoch History Component

import { useState, useEffect } from 'react';
import { fetchPoolState, formatUSDC } from '../lib/pool';
import type { PoolState, Epoch } from '../lib/types';

function EpochRow({ epoch, isCurrent }: { epoch: Epoch; isCurrent: boolean }) {
  const volume = parseFloat(epoch.total_volume_usdc);
  const minerPayout = volume * 0.75;

  return (
    <tr className={isCurrent ? 'bg-[--color-green-dark]/10' : ''}>
      <td>
        <div className="flex items-center gap-2">
          <span className="font-medium">{epoch.epoch_id.toUpperCase()}</span>
          {isCurrent && <span className="tag tag-live pulse">ACTIVE</span>}
          {!isCurrent && epoch.status === 'sealed' && <span className="tag tag-sealed">SEALED</span>}
        </div>
      </td>
      <td className="text-[--color-cyan]">{epoch.jobs_completed.toLocaleString()}</td>
      <td className="text-[--color-green]">{formatUSDC(volume)}</td>
      <td className="hidden md:table-cell">{formatUSDC(minerPayout)}</td>
      <td className="hidden lg:table-cell">{epoch.miners_paid}</td>
      <td className="hidden sm:table-cell">
        {epoch.started_at ? new Date(epoch.started_at).toLocaleDateString() : '-'}
      </td>
      <td className="hidden md:table-cell">
        {epoch.merkle_root ? (
          <code className="text-xs text-[--color-text-dim]">
            {epoch.merkle_root.slice(0, 10)}...
          </code>
        ) : (
          <span className="text-[--color-text-dim]">-</span>
        )}
      </td>
    </tr>
  );
}

export function EpochHistory() {
  const [state, setState] = useState<PoolState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const data = await fetchPoolState();
      if (data) setState(data);
      setLoading(false);
    };
    load();

    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="terminal-box p-6">
        <div className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-[--color-border] rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="terminal-box p-6 text-center">
        <p className="text-[--color-red]">Failed to load epoch history</p>
      </div>
    );
  }

  const allEpochs = [state.current_epoch, ...(state.epochs || [])];

  return (
    <div className="terminal-box overflow-hidden">
      <div className="p-4 border-b border-[--color-border]">
        <h3 className="text-lg font-bold glow-text">EPOCH HISTORY</h3>
        <p className="text-sm text-[--color-text-dim]">
          Settlement cycles with on-chain proofs
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="terminal-table">
          <thead>
            <tr>
              <th>Epoch</th>
              <th>Jobs</th>
              <th>Volume</th>
              <th className="hidden md:table-cell">Miner Payout</th>
              <th className="hidden lg:table-cell">Miners</th>
              <th className="hidden sm:table-cell">Started</th>
              <th className="hidden md:table-cell">Merkle Root</th>
            </tr>
          </thead>
          <tbody>
            {allEpochs.map((epoch, index) => (
              <EpochRow key={epoch.epoch_id} epoch={epoch} isCurrent={index === 0} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function EpochSummary() {
  const [state, setState] = useState<PoolState | null>(null);

  useEffect(() => {
    fetchPoolState().then(setState);
  }, []);

  if (!state) return null;

  const totalEpochs = (state.epochs?.length || 0) + 1;
  const sealedEpochs = state.epochs?.filter(e => e.status === 'sealed').length || 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="stat-card">
        <div className="text-xs text-[--color-text-dim] uppercase">Total Epochs</div>
        <div className="text-2xl font-bold">{totalEpochs}</div>
      </div>
      <div className="stat-card">
        <div className="text-xs text-[--color-text-dim] uppercase">Sealed Epochs</div>
        <div className="text-2xl font-bold">{sealedEpochs}</div>
      </div>
      <div className="stat-card">
        <div className="text-xs text-[--color-text-dim] uppercase">Current Epoch</div>
        <div className="text-2xl font-bold glow-text">{state.current_epoch.epoch_id.toUpperCase()}</div>
      </div>
      <div className="stat-card">
        <div className="text-xs text-[--color-text-dim] uppercase">This Epoch</div>
        <div className="text-2xl font-bold text-[--color-cyan]">{state.current_epoch.jobs_completed} jobs</div>
      </div>
    </div>
  );
}
