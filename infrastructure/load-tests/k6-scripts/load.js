import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '5m',
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const unauthenticatedMix = [
  { weight: 100, method: 'GET', url: '/health', body: null },
];

// Try login first, fall back to register
const __LOGIN = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({ email: 'loadtest@k6.io', password: 'k6pass123' }), { headers: { 'Content-Type': 'application/json' } });
let TOKEN = __LOGIN.status === 200 ? __LOGIN.json('access_token') : null;
if (!TOKEN) {
  const __REG = http.post(`${BASE_URL}/api/auth/register`, JSON.stringify({ email: 'loadtest@k6.io', password: 'k6pass123' }), { headers: { 'Content-Type': 'application/json' } });
  TOKEN = __REG.status === 200 ? __REG.json('access_token') : null;
}
const AUTH_HEADER = TOKEN ? { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json' } : null;

const trafficMix = AUTH_HEADER ? [
  { weight: 40, method: 'GET', url: '/api/markets', body: null },
  { weight: 20, method: 'GET', url: '/api/strategies', body: null },
  { weight: 15, method: 'GET', url: '/api/analytics/summary', body: null },
  { weight: 10, method: 'GET', url: '/api/risk/summary', body: null },
  { weight: 10, method: 'GET', url: '/api/portfolio', body: null },
  { weight: 5, method: 'POST', url: '/api/paper/orders', body: JSON.stringify({ wallet_id: 'default', platform: 'polymarket', market_id: 'm1', market_title: 'loadtest', side: 'buy', amount: 100, price: 0.55, mode: 'paper' }) },
] : unauthenticatedMix;

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
  const params = { headers: AUTH_HEADER || { 'Content-Type': 'application/json' } };
  const res = http.request(ep.method, `${BASE_URL}${ep.url}`, ep.body, params);

  check(res, {
    'status ok': (r) => r.status >= 200 && r.status < 500,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });
  sleep(0.1);
}
