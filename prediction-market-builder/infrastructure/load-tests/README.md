# K6 Load Tests — Prediction Market Strategy Builder

## Prerequisites

- [k6](https://k6.io/docs/getting-started/installation/) installed (`choco install k6`, `brew install k6`, or download from k6.io)
- The API server running locally at `http://localhost:8000`

## Running the Tests

All commands are run from the `infrastructure/load-tests/` directory:

```powershell
# Smoke test — 1 user, 1 iteration through all endpoints
k6 run k6-scripts/smoke.js

# Load test — 10 VUs for 5 minutes
k6 run k6-scripts/load.js

# Stress test — ramp from 1 to 200 VUs over 10 minutes
k6 run k6-scripts/stress.js
```

For verbose output during debugging:

```powershell
k6 run --verbose k6-scripts/smoke.js
```

## Test Descriptions

### Smoke (`smoke.js`)

- 1 virtual user, single iteration
- Hits every endpoint sequentially with 0.5s think time
- Verifies status codes (accepts 200 and 401 for authenticated routes)
- **Purpose**: Confirm the API is alive and all routes respond before running heavier tests

### Load (`load.js`)

- 10 constant VUs for 5 minutes
- Weighted traffic mix:

| Endpoint          | Weight |
|--------------------|--------|
| GET /api/markets   | 40%    |
| GET /api/strategies| 20%    |
| GET /api/analytics | 15%    |
| GET /api/risk      | 10%    |
| GET /api/portfolio | 10%    |
| POST /api/orders   | 5%     |

- Random think time between requests (0.5–2.5s)
- **Thresholds**: P95 response time < 1s, error rate < 1%
- **Purpose**: Validate the API handles sustained nominal traffic

### Stress (`stress.js`)

- 4 stages ramping to 200 concurrent VUs:

| Stage | Target VUs | Duration |
|-------|------------|----------|
| 1     | 50         | 2 min    |
| 2     | 100        | 3 min    |
| 3     | 200        | 3 min    |
| 4     | 200 (hold) | 2 min    |

- Weighted traffic across all endpoints
- **Thresholds**: P95 response time < 5s, error rate < 5%
- **Purpose**: Find the breaking point — where latency spikes or errors climb

## Interpreting Results

Key metrics in the k6 output:

| Metric               | Meaning                                |
|----------------------|----------------------------------------|
| `http_req_duration`  | End-to-end response time (ms)          |
| `http_req_failed`    | Rate of non-2xx/401 responses           |
| `iterations`         | Total requests completed               |
| `vus`                | Concurrent virtual users               |
| `data_received`      | Total response data                    |

### Finding the Breaking Point (Stress Test)

Watch these signals as VUs increase:

1. **P95 latency crosses 5s** — the API is saturated; investigate DB queries, connection pools, or rate limiting
2. **Error rate climbs above 5%** — the server is rejecting or timing out requests; look for 429 (rate-limit), 503 (service unavailable), or connection resets
3. **Iteration rate plateaus or drops** — throughput has maxed out; the bottleneck has been reached
4. **Sudden jump in `http_req_duration` stddev** — the system is entering thundering-herd territory; consider adding a cache layer or autoscaling

After the stress run, note the VU count and stage where these thresholds were breached. That is your approximate breaking point.
