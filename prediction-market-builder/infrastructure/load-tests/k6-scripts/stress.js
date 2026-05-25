import http from 'k6/http';
import { check, sleep } from 'k6';
import { randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

export const options = {
  stages: [
    { target: 50, duration: '2m' },
    { target: 100, duration: '3m' },
    { target: 200, duration: '3m' },
    { target: 200, duration: '2m' },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],
    http_req_failed: ['rate<0.05'],
  },
};

const BASE_URL = 'http://localhost:8000';

const endpoints = [
  { method: 'GET', url: '/api/markets', body: null, weight: 35 },
  { method: 'GET', url: '/api/markets/search?q=crypto', body: null, weight: 10 },
  { method: 'GET', url: '/api/strategies', body: null, weight: 15 },
  { method: 'GET', url: '/api/analytics/performance', body: null, weight: 10 },
  { method: 'GET', url: '/api/risk/summary', body: null, weight: 8 },
  { method: 'GET', url: '/api/portfolio', body: null, weight: 7 },
  { method: 'GET', url: '/api/research/status', body: null, weight: 5 },
  { method: 'POST', url: '/api/paper/orders', body: JSON.stringify({ market: 'stresstest', side: 'buy', quantity: 1, price: 0.5 }), weight: 5 },
  { method: 'POST', url: '/api/chat/stream', body: JSON.stringify({ message: 'ping' }), weight: 3 },
  { method: 'GET', url: '/api/health', body: null, weight: 2 },
];

const totalWeight = endpoints.reduce((s, e) => s + e.weight, 0);

function pickEndpoint() {
  let r = Math.random() * totalWeight;
  for (const ep of endpoints) {
    r -= ep.weight;
    if (r <= 0) return ep;
  }
  return endpoints[endpoints.length - 1];
}

export default function () {
  const ep = pickEndpoint();
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.request(ep.method, `${BASE_URL}${ep.url}`, ep.body, params);

  check(res, {
    'status acceptable (200 or 401)': (r) => r.status === 200 || r.status === 401,
  });

  sleep(randomIntBetween(0.2, 1.5));
}
