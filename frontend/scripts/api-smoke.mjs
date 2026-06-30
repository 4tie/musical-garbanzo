const baseUrl = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

async function getJson(path) {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { Accept: 'application/json' },
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  return { ok: response.ok, status: response.status, data };
}

function isBaselineRun(run) {
  const haystack = `${run?.mode ?? ''} ${run?.name ?? ''} ${run?.classification ?? ''}`.toLowerCase();
  return haystack.includes('baseline');
}

const [health, optimizationRuns, runs] = await Promise.all([
  getJson('/health'),
  getJson('/api/optimization/runs?limit=10'),
  getJson('/api/runs?limit=50'),
]);

const allRuns = Array.isArray(runs.data) ? runs.data : [];
const optRuns = Array.isArray(optimizationRuns.data) ? optimizationRuns.data : [];

console.log(
  JSON.stringify(
    {
      baseUrl,
      health: {
        ok: health.ok,
        status: health.status,
        backend: health.data?.backend ?? null,
      },
      optimizationRuns: {
        ok: optimizationRuns.ok,
        status: optimizationRuns.status,
        count: optRuns.length,
        latest: optRuns[0]
          ? {
              id: optRuns[0].id,
              status: optRuns[0].status,
              result_status: optRuns[0].result_status ?? null,
            }
          : null,
      },
      baselineRuns: {
        ok: runs.ok,
        status: runs.status,
        count: allRuns.filter(isBaselineRun).length,
      },
    },
    null,
    2,
  ),
);
