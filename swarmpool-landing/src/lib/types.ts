// SwarmPool Data Types

export interface MinerInfo {
  ens: string;
  status: 'online' | 'busy' | 'offline';
  gpu: string;
  vram_gb: number;
  hashrate: string;
  jobs_completed: number;
  total_earned: string;
  last_seen: string;
  uptime_percent: number;
}

export interface Job {
  job_id: string;
  model: string;
  status: 'pending' | 'claimed' | 'completed';
  client: string;
  submitted_at: string;
  claimed_by?: string;
  claimed_at?: string;
  completed_at?: string;
  price_usdc: string;
  proof_cid?: string;
}

export interface Epoch {
  epoch_id: string;
  status: 'active' | 'sealed';
  started_at: string;
  ended_at?: string;
  jobs_completed: number;
  total_volume_usdc: string;
  miners_paid: number;
  merkle_root?: string;
  settlement_tx?: string;
}

export interface PoolState {
  pool_id: string;
  pool_name: string;
  coordinator: string;
  total_jobs: number;
  total_proofs: number;
  total_volume_usdc: number;
  current_epoch: Epoch;
  pending_jobs: Job[];
  recent_completions: Job[];
  active_miners: MinerInfo[];
  epochs: Epoch[];
  last_updated: string;
  stats: {
    avg_completion_time: number;
    jobs_per_hour: number;
    active_miner_count: number;
    pending_job_count: number;
  };
}

export interface LeaderboardEntry {
  rank: number;
  ens: string;
  jobs_completed: number;
  total_earned: string;
  avg_completion_time: number;
  uptime_percent: number;
}
