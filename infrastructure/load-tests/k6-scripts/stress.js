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
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = 'http://localhost:8000';

const endpoints = [
  { method: 'GET', url: '/api/markets', body: null, weight: 35 },
  { method: 'GET', url: '/api/markets?search=crypto', body: null, weight: 10 },
  { method: 'GET', url: '/api/strategies', body: null, weight: 15 },
  { method: 'GET', url: '/api/analytics/summary', body: null, weight: 10 },
  { method: 'GET', url: '/api/risk/summary', body: null, weight: 8 },
  { method: 'GET', url: '/api/portfolio', body: null, weight: 7 },
  { method: 'GET', url: '/api/research/stats', body: null, weight: 5 },
  { method: 'POST', url: '/api/paper/orders', body: JSON.stringify({ wallet_id: 'default', platform: 'polymarket', market_id: 'm1', market_title: 'stresstest', side: 'buy', amount: 100, price: 0.55, mode: 'paper' }), weight: 5 },
  { method: 'POST', url: '/api/chat/message', body: JSON.stringify({ message: 'ping' }), weight: 3 },
  { method: 'GET', url: '/health', body: null, weight: 2 },
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

// Cache auth tokens per VU
let vuToken = null;

function getHeaders() {
  if (!vuToken) {
    let loginRes = http.post(`${BASE_URL}/api/auth/login`,
      JSON.stringify({ email: 'stresstest@k6.io', password: 'k6pass123' }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    if (loginRes.status === 200) {
      vuToken = loginRes.json('access_token');
    } else {
      let regRes = http.post(`${BASE_URL}/api/auth/register`,
        JSON.stringify({ email: 'stresstest@k6.io', password: 'k6pass123' }),
        { headers: { 'Content-Type': 'application/json' } }
      );
      if (regRes.status === 200) {
        vuToken = regRes.json('access_token');
      }
    }
  }
  return { 'Authorization': `Bearer ${vuToken}`, 'Content-Type': 'application/json' };
}

export default function () {
  const headers = getHeaders();
  const ep = pickEndpoint();
  const res = http.request(ep.method, `${BASE_URL}${ep.url}`, ep.body, { headers });

  check(res, {
    'status 200': (r) => r.status === 200,
  });

  sleep(randomIntBetween(0.2, 1.5));
}
