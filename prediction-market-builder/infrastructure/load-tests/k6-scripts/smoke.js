import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.99', abortOnFail: false }],
  },
};

const BASE_URL = 'http://localhost:8000';

const endpoints = [
  { method: 'GET', url: '/health', expected: [200] },
  { method: 'GET', url: '/api/markets', expected: [200, 401] },
  { method: 'GET', url: '/api/markets/search?q=crypto', expected: [200, 401] },
  { method: 'GET', url: '/api/strategies', expected: [200, 401] },
  { method: 'GET', url: '/api/risk/summary', expected: [200, 401] },
  { method: 'GET', url: '/api/analytics/summary', expected: [200, 401] },
  { method: 'GET', url: '/api/portfolio', expected: [200, 401] },
  { method: 'GET', url: '/api/research/stats', expected: [200, 401] },
  { method: 'POST', url: '/api/auth/login', body: JSON.stringify({ email: 'test@test.com', password: 'wrongpass' }), expected: [401, 422] },
  { method: 'POST', url: '/api/chat/message', body: JSON.stringify({ message: 'ping' }), expected: [200, 401, 422] },
  { method: 'POST', url: '/api/paper/orders', body: JSON.stringify({ wallet_id: 'default', platform: 'polymarket', market_id: 'm1', market_title: 'test', side: 'buy', amount: 100, price: 0.55, mode: 'paper' }), expected: [200, 401, 422] },
];

export default function () {
  for (const ep of endpoints) {
    const params = {
      headers: { 'Content-Type': 'application/json' },
    };

    const res = http.request(ep.method, `${BASE_URL}${ep.url}`, ep.body || null, params);

    check(res, {
      [`${ep.method} ${ep.url} status in [${ep.expected.join(',')}]`]: (r) =>
        ep.expected.includes(r.status),
      [`${ep.method} ${ep.url} response time < 5s`]: (r) => r.timings.duration < 5000,
    });

    sleep(0.5);
  }
}
