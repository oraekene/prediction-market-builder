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

## Actual Results (SQLite, local dev)

### Smoke Test
- **22/22 checks passed** (100%) — all endpoints respond correctly
- Average response time: **8.2ms**
- P95 response time: **17ms**

### Load Test (10 VUs × 5 min)
- P95 response time: **16.1ms** (target: <1s ✅)
- All response times < 2s: **100%**
- Throughput: **~6.6 req/s**

### Stress Test (ramp 1→200 VUs over 10 min)
- **Breaking point**: ~**160–170 concurrent VUs**
- P95 response time: **48.6s** (target: <5s ❌ — threshold breached at ~150 VUs)
- P90 response time: **20.5s**
- Median response time: **2.08s** (fine until ~120 VUs)
- Successful requests (status 200): **7.17%**
- Maximum throughput: **~13 req/s** at 200 VUs
- **36 interrupted iterations** — connections forcibly reset by the server

### Bottlenecks (SQLite)

The primary bottleneck is **SQLite's single-writer lock**:

| Issue | Impact |
|-------|--------|
| SQLite serializes all writes | Auth login/register POSTs queue behind each other |
| No connection pooling | Each request opens a new connection to the file |
| 2 uvicorn workers | Both contend on the same SQLite file |
| Auth per VU | 200 simultaneous login attempts at ~150 VUs flood the DB lock |

### Production Recommendations

| Change | Expected Improvement | Priority |
|--------|---------------------|----------|
| PostgreSQL | Eliminates write-lock contention; 10×+ throughput | High |
| 4+ uvicorn workers | Better utilization of multi-core CPU | High |
| PgBouncer connection pooling | Reduces connection overhead | Medium |
| Rate limiting (~150 req/s) | Prevents saturation, keeps P95 < 1s | Medium |
| Redis caching for /markets, /strategies | Reduces DB reads by ~60% | Medium |
| Read replicas for analytics/research | Isolates heavy queries from writes | Low |

After switching to PostgreSQL and increasing workers, re-run the stress test to find the new breaking point.
