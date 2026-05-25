import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 1,
  iterations: 1,
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.01', abortOnFail: true }],
  },
};

const BASE_URL = 'http://localhost:8000';

const endpoints = [
  { method: 'GET', url: '/api/health', expected: [200] },
  { method: 'GET', url: '/api/markets', expected: [200, 401] },
  { method: 'GET', url: '/api/markets/search?q=crypto', expected: [200, 401] },
  { method: 'POST', url: '/api/auth/login', expected: [200, 422, 401] },
  { method: 'GET', url: '/api/strategies', expected: [200, 401] },
  { method: 'GET', url: '/api/risk/summary', expected: [200, 401] },
  { method: 'POST', url: '/api/chat/stream', expected: [200, 422, 401] },
  { method: 'GET', url: '/api/analytics/performance', expected: [200, 401] },
  { method: 'GET', url: '/api/portfolio', expected: [200, 401] },
  { method: 'POST', url: '/api/paper/orders', expected: [200, 422, 401] },
  { method: 'GET', url: '/api/research/status', expected: [200, 401] },
];

export default function () {
  for (const ep of endpoints) {
    const params = {
      headers: { 'Content-Type': 'application/json' },
    };

    let body = null;
    if (ep.method === 'POST') {
      if (ep.url === '/api/auth/login') {
        body = JSON.stringify({ username: 'test', password: 'test' });
      } else if (ep.url === '/api/chat/stream') {
        body = JSON.stringify({ message: 'ping' });
      } else if (ep.url === '/api/paper/orders') {
        body = JSON.stringify({ market: 'test', side: 'buy', quantity: 1, price: 0.5 });
      }
    }

    const res = http.request(ep.method, `${BASE_URL}${ep.url}`, body, params);

    check(res, {
      [`${ep.method} ${ep.url} status in [${ep.expected.join(',')}]`]: (r) =>
        ep.expected.includes(r.status),
      [`${ep.method} ${ep.url} response time < 5s`]: (r) => r.timings.duration < 5000,
    });

    sleep(0.5);
  }
}
