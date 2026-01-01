// SwarmPool Data Fetching

import type { PoolState, Epoch, LeaderboardEntry } from './types';

// IPFS gateways for fallback
const IPFS_GATEWAYS = [
  'https://w3s.link/ipfs',
  'https://ipfs.io/ipfs',
  'https://cloudflare-ipfs.com/ipfs',
];

// For local development / static deployment
const LOCAL_DATA_PATH = '/data';

// Check if we're in browser and have live API configured
const USE_LIVE_API = typeof window !== 'undefined' &&
  (import.meta.env.PUBLIC_USE_LIVE_API === 'true' || false);

const API_URL = import.meta.env.PUBLIC_API_URL || '';

/**
 * Fetch pool state from IPFS or local data
 */
export async function fetchPoolState(): Promise<PoolState | null> {
  try {
    // Try local data first (for static deployment)
    const response = await fetch(`${LOCAL_DATA_PATH}/state.json`);
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.error('Failed to fetch local pool state:', error);
  }

  // If local fails and we have IPFS CID configured, try IPFS
  const ipfsCid = import.meta.env.PUBLIC_POOL_STATE_CID;
  if (ipfsCid) {
    for (const gateway of IPFS_GATEWAYS) {
      try {
        const response = await fetch(`${gateway}/${ipfsCid}`);
        if (response.ok) {
          return await response.json();
        }
      } catch {
        continue;
      }
    }
  }

  return null;
}

/**
 * Fetch specific epoch data
 */
export async function fetchEpoch(epochId: string): Promise<Epoch | null> {
  try {
    const response = await fetch(`${LOCAL_DATA_PATH}/epochs/${epochId}.json`);
    if (response.ok) {
      return await response.json();
    }
  } catch (error) {
    console.error('Failed to fetch epoch:', error);
  }
  return null;
}

/**
 * Get leaderboard from pool state
 */
export function getLeaderboard(state: PoolState): LeaderboardEntry[] {
  return state.active_miners
    .sort((a, b) => b.jobs_completed - a.jobs_completed)
    .map((miner, index) => ({
      rank: index + 1,
      ens: miner.ens,
      jobs_completed: miner.jobs_completed,
      total_earned: miner.total_earned,
      avg_completion_time: 1.5 + Math.random() * 0.5, // Simulated
      uptime_percent: miner.uptime_percent,
    }));
}

/**
 * Format timestamp to relative time
 */
export function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return `${diffSecs}s ago`;
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

/**
 * Format USDC amount
 */
export function formatUSDC(amount: number | string): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return `$${num.toFixed(2)}`;
}

/**
 * Truncate ENS or address
 */
export function truncateENS(ens: string, maxLength: number = 20): string {
  if (ens.length <= maxLength) return ens;
  return ens.slice(0, maxLength - 3) + '...';
}

/**
 * Get status color class
 */
export function getStatusClass(status: string): string {
  switch (status) {
    case 'online':
    case 'active':
    case 'completed':
      return 'status-online';
    case 'busy':
    case 'claimed':
    case 'pending':
      return 'status-busy';
    case 'offline':
    case 'sealed':
      return 'status-offline';
    default:
      return '';
  }
}

/**
 * Get status icon
 */
export function getStatusIcon(status: string): string {
  switch (status) {
    case 'online':
    case 'active':
      return '●';
    case 'busy':
    case 'claimed':
      return '◐';
    case 'offline':
    case 'sealed':
      return '○';
    default:
      return '?';
  }
}
