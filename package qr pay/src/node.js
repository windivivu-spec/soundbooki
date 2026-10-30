import { Readable } from 'node:stream';

// Mount before express.json(); the adapter consumes the original bounded request stream.
export function nodeHandler(payments, options) {
  return async (req, res) => {
    try {
      const headers = new Headers();
      for (const [name, value] of Object.entries(req.headers)) {
        if (Array.isArray(value)) for (const item of value) headers.append(name, item);
        else if (value !== undefined) headers.set(name, value);
      }
      const method = req.method || 'GET';
      const request = new Request(new URL(req.originalUrl || req.url || '/', 'http://localhost'), {
        method, headers,
        ...(!['GET', 'HEAD'].includes(method) ? { body: Readable.toWeb(req), duplex: 'half' } : {}),
      });
      const response = await payments.handle(request, options);
      res.writeHead(response.status, Object.fromEntries(response.headers));
      res.end(Buffer.from(await response.arrayBuffer()));
    } catch {
      if (!res.headersSent) res.writeHead(503, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify({ error: 'Payment service temporarily unavailable' }));
    }
  };
}
