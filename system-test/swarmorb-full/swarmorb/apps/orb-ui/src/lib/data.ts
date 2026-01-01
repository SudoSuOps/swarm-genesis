/**
 * SwarmOrb Data Layer
 *
 * Fetches live data from Bee-1 API with fallback to static data.
 * For dev: reads from /data/ (sample_data copied here)
 * For prod: reads from Bee-1 API at configured URL
 */

// Base URL for data - can be overridden for production
const DATA_BASE = import.meta.env.PUBLIC_DATA_URL || '/data';

// Bee-1 API URL - set to your Bee-1 controller endpoint
const API_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

// Flag to control live API mode
const USE_LIVE_API = import.meta.env.PUBLIC_USE_LIVE_API === 'true' || true;

export interface EpochRef {
  epoch_id: string;
  start_time: string;
  end_time: string;
  status: string;
  bundle_ref: string;
  summary_hash: string;
  jobs_completed: number;
  total_distributed: string;
  agents_active: number;
}

export interface AgentSummary {
  ens: string;
  jobs_completed: number;
  total_earned: string;
  uptime_hours: number;
}

export interface AggregateStats {
  total_epochs: number;
  total_jobs: number;
  total_distributed: string;
  unique_agents: number;
  unique_clients: number;
  top_agents: AgentSummary[];
}

export interface OrbIndex {
  version: string;
  generated_at: string;
  coordinator: string;
  epochs: EpochRef[];
  stats: AggregateStats;
}

export interface LiveAgent {
  ens: string;
  status: 'online' | 'busy' | 'offline' | 'draining';
  last_heartbeat: string;
  current_job: string | null;
  jobs_this_epoch: number;
  uptime_this_epoch: number;
  hardware: {
    gpu: string;
    vram_gb: number;
    cpu: string;
    ram_gb: number;
  };
}

export interface LiveState {
  version: string;
  timestamp: string;
  coordinator: string;
  current_epoch: {
    epoch_id: string;
    started_at: string;
    ends_at: string;
    jobs_completed: number;
    jobs_in_progress: number;
    revenue_collected: string;
    work_pool: string;
    readiness_pool: string;
  };
  agents: LiveAgent[];
  queue: {
    pending: number;
    in_progress: number;
    avg_wait_seconds: number;
  };
}

export interface EpochSummary {
  epoch_id: string;
  start_time: string;
  end_time: string;
  coordinator: string;
  treasury: {
    total_revenue: string;
    work_pool: string;
    readiness_pool: string;
    protocol_fee: string;
    distributed: string;
    dust_rolled: string;
  };
  agents: {
    total_active: number;
    total_eligible: number;
    payouts: Array<{
      ens: string;
      jobs_completed: number;
      uptime_seconds: number;
      work_share: string;
      readiness_share: string;
      total_payout: string;
      poe_success_rate: number;
    }>;
  };
  jobs: {
    total_submitted: number;
    total_completed: number;
    total_failed: number;
    avg_execution_ms: number;
    by_task_type: Record<string, number>;
  };
  clients: {
    total_active: number;
    total_spent: string;
    top_clients: Array<{
      ens: string;
      jobs_submitted: number;
      total_spent: string;
    }>;
  };
}

/**
 * Fetch live stats from Bee-1 API
 */
export async function fetchAPIStats(): Promise<any | null> {
  try {
    const res = await fetch(`${API_URL}/v1/stats`, {
      headers: { 'Accept': 'application/json' },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Fetch the main index.json or build from API
 */
export async function fetchIndex(): Promise<OrbIndex | null> {
  // Try API first if enabled
  if (USE_LIVE_API) {
    const apiStats = await fetchAPIStats();
    if (apiStats) {
      return transformAPIToIndex(apiStats);
    }
  }

  // Fall back to static data
  try {
    const res = await fetch(`${DATA_BASE}/orb/index.json`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Transform Bee-1 API response to OrbIndex format
 */
function transformAPIToIndex(api: any): OrbIndex {
  const epochs = api.epochs?.list || [];
  const workers = api.workers?.list || [];

  // Find sealed epochs for stats
  const sealedEpochs = epochs.filter((e: any) => e.status === 'sealed');

  // Build top agents from workers
  const topAgents: AgentSummary[] = workers.map((w: any) => ({
    ens: w.ens,
    jobs_completed: w.jobs_completed || 0,
    total_earned: ((w.jobs_completed || 0) * 0.093).toFixed(2), // Estimate based on $0.10 per job, 93% worker share
    uptime_hours: 24, // Placeholder
  }));

  return {
    version: '1.0.0',
    generated_at: api.updated_at || new Date().toISOString(),
    coordinator: 'bee1.swarmos.eth',
    epochs: sealedEpochs.map((e: any) => ({
      epoch_id: e.epoch_id,
      start_time: e.started_at,
      end_time: e.ended_at || '',
      status: e.status,
      bundle_ref: '',
      summary_hash: e.merkle_root || '',
      jobs_completed: e.jobs_completed,
      total_distributed: (e.total_volume_usdc * 0.93).toFixed(2), // 93% to workers
      agents_active: api.workers?.total || 1,
    })),
    stats: {
      total_epochs: api.epochs?.total || 1,
      total_jobs: api.jobs?.total || 0,
      total_distributed: ((api.volume?.total_usdc || 0) * 0.93).toFixed(2),
      unique_agents: api.workers?.total || 0,
      unique_clients: 1, // Placeholder
      top_agents: topAgents,
    },
  };
}

/**
 * Fetch live state from API or static file
 */
export async function fetchLive(): Promise<LiveState | null> {
  // Try API first if enabled
  if (USE_LIVE_API) {
    const apiStats = await fetchAPIStats();
    if (apiStats) {
      return transformAPIToLive(apiStats);
    }
  }

  // Fall back to static data
  try {
    const res = await fetch(`${DATA_BASE}/orb/live.json`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Transform Bee-1 API response to LiveState format
 */
function transformAPIToLive(api: any): LiveState {
  const currentEpoch = api.epochs?.list?.find((e: any) => e.status === 'active') || {};
  const workers = api.workers?.list || [];

  const revenue = api.volume?.current_epoch_usdc || 0;
  const workPool = revenue * 0.70;
  const readinessPool = revenue * 0.30;

  return {
    version: '1.0.0',
    timestamp: api.updated_at || new Date().toISOString(),
    coordinator: 'bee1.swarmos.eth',
    current_epoch: {
      epoch_id: currentEpoch.epoch_id || api.epochs?.current_id || 'epoch-001',
      started_at: currentEpoch.started_at || '',
      ends_at: '', // Open epoch
      jobs_completed: api.jobs?.current_epoch || 0,
      jobs_in_progress: api.jobs?.processing || 0,
      revenue_collected: revenue.toFixed(2),
      work_pool: workPool.toFixed(2),
      readiness_pool: readinessPool.toFixed(2),
    },
    agents: workers.map((w: any) => ({
      ens: w.ens,
      status: w.status || 'online',
      last_heartbeat: w.last_heartbeat || '',
      current_job: null,
      jobs_this_epoch: w.jobs_completed || 0,
      uptime_this_epoch: 86400, // 24h placeholder
      hardware: w.hardware || { gpu: 'Unknown', vram_gb: 0, cpu: 'Unknown', ram_gb: 0 },
    })),
    queue: {
      pending: api.queue?.spine_pending + api.queue?.chest_pending + api.queue?.cardiac_pending || 0,
      in_progress: api.queue?.processing || 0,
      avg_wait_seconds: 0,
    },
  };
}

/**
 * Fetch epoch summary from bundle
 */
export async function fetchEpochSummary(epochId: string): Promise<EpochSummary | null> {
  try {
    // For local dev, bundle_ref is relative path
    const res = await fetch(`${DATA_BASE}/audit/${epochId}/SUMMARY.json`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Fetch SIGNATURE.txt content
 */
export async function fetchSignature(epochId: string): Promise<string | null> {
  try {
    const res = await fetch(`${DATA_BASE}/audit/${epochId}/SIGNATURE.txt`);
    if (!res.ok) return null;
    return await res.text();
  } catch {
    return null;
  }
}

/**
 * Fetch epoch jobs
 */
export async function fetchEpochJobs(epochId: string): Promise<any | null> {
  try {
    const res = await fetch(`${DATA_BASE}/audit/${epochId}/jobs.json`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Fetch epoch agents
 */
export async function fetchEpochAgents(epochId: string): Promise<any | null> {
  try {
    const res = await fetch(`${DATA_BASE}/audit/${epochId}/agents.json`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

/**
 * Format a number as USD
 */
export function formatUSD(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(num);
}

/**
 * Format a date string
 */
export function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a timestamp
 */
export function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format relative time
 */
export function formatRelative(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
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
 * Truncate a hash for display
 */
export function truncateHash(hash: string, chars: number = 8): string {
  if (hash.length <= chars * 2) return hash;
  return `${hash.slice(0, chars)}...${hash.slice(-chars)}`;
}

/**
 * Format seconds as hours
 */
export function formatHours(seconds: number): string {
  const hours = seconds / 3600;
  return `${hours.toFixed(1)}h`;
}
