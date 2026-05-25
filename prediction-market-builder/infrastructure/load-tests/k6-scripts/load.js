import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

export const options = {
  vus: 10,
  duration: '5m',
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = 'http://localhost:8000';

const trafficMix = [
  { weight: 40, method: 'GET', url: '/api/markets', body: null },
  { weight: 20, method: 'GET', url: '/api/strategies', body: null },
  { weight: 15, method: 'GET', url: '/api/analytics/performance', body: null },
  { weight: 10, method: 'GET', url: '/api/risk/summary', body: null },
  { weight: 10, method: 'GET', url: '/api/portfolio', body: null },
  { weight: 5, method: 'POST', url: '/api/paper/orders', body: JSON.stringify({ market: 'loadtest', side: 'buy', quantity: 1, price: 0.5 }) },
];

const totalWeight = trafficMix.reduce((s, e) => s + e.weight, 0);

function pickEndpoint() {
  let r = Math.random() * totalWeight;
  for (const ep of trafficMix) {
    r -= ep.weight;
    if (r <= 0) return ep;
  }
  return trafficMix[trafficMix.length - 1];
}

export default function () {
  const ep = pickEndpoint();
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.request(ep.method, `${BASE_URL}${ep.url}`, ep.body, params);

  check(res, {
    'status acceptable (200 or 401)': (r) => r.status === 200 || r.status === 401,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });

  sleep(randomIntBetween(0.5, 2.5));
}
