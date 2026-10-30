// Explicit operator connection test. Uploads only a tiny random marker, then
// removes it in finally. Provider credentials never enter the report/app.
import { createHash, createHmac, randomUUID } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';

const required = name => {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing ${name}`);
  return value;
};
const account = required('R2_ACCOUNT_ID');
const access = required('R2_ACCESS_KEY_ID');
const secret = required('R2_SECRET_ACCESS_KEY');
const bucket = required('R2_BUCKET');
if (!/^[a-f0-9]{32}$/i.test(account)) throw new Error('R2_ACCOUNT_ID must contain the 32-character account ID only');
if (!/^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$/.test(bucket)) throw new Error('Invalid R2_BUCKET');
const publicBase = new URL(required('R2_PUBLIC_BASE_URL'));
if (publicBase.protocol !== 'https:' || publicBase.username || publicBase.password || publicBase.search || publicBase.hash) throw new Error('R2_PUBLIC_BASE_URL must be a clean HTTPS public base URL');
if (publicBase.hostname.endsWith('.r2.cloudflarestorage.com')) throw new Error('R2_PUBLIC_BASE_URL is the private S3 endpoint; use a public download domain');
const endpoint = new URL(process.env.R2_ENDPOINT_URL || `https://${account}.r2.cloudflarestorage.com`);
if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password || ![`${account}.r2.cloudflarestorage.com`, `${account}.eu.r2.cloudflarestorage.com`, `${account}.fedramp.r2.cloudflarestorage.com`].includes(endpoint.hostname) || endpoint.pathname !== '/' || endpoint.search || endpoint.hash) throw new Error('Invalid R2_ENDPOINT_URL');
const hash = value => createHash('sha256').update(value).digest('hex');
const hmac = (key, value) => createHmac('sha256', key).update(value).digest();
const encode = value => encodeURIComponent(value).replace(/[!'()*]/g, c => '%' + c.charCodeAt(0).toString(16).toUpperCase());
async function signed(method, key = '', body = '', query = {}) {
  const url = new URL(endpoint);
  url.pathname = '/' + [bucket, ...key.split('/').filter(Boolean)].map(encode).join('/');
  const canonicalQuery = Object.entries(query).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${encode(k)}=${encode(v)}`).join('&');
  url.search = canonicalQuery;
  const date = new Date().toISOString().replace(/[:-]|\.\d{3}/g, ''), day = date.slice(0, 8);
  const payloadHash = hash(body);
  const headers = { host: url.host, 'x-amz-content-sha256': payloadHash, 'x-amz-date': date };
  const names = Object.keys(headers).sort();
  const canonical = [method, url.pathname, canonicalQuery, names.map(n => `${n}:${headers[n]}\n`).join(''), names.join(';'), payloadHash].join('\n');
  const scope = `${day}/auto/s3/aws4_request`;
  const signingKey = hmac(hmac(hmac(hmac('AWS4' + secret, day), 'auto'), 's3'), 'aws4_request');
  const signature = hmac(signingKey, `AWS4-HMAC-SHA256\n${date}\n${scope}\n${hash(canonical)}`).toString('hex');
  headers.authorization = `AWS4-HMAC-SHA256 Credential=${access}/${scope}, SignedHeaders=${names.join(';')}, Signature=${signature}`;
  return fetch(url, { method, headers, body: method === 'PUT' ? body : undefined, redirect: 'error', signal: AbortSignal.timeout(20000) });
}
const checks = { bucketMatchesSelected: bucket === 'windi-bucket' };
const marker = `sachnoi/_connection-check/${randomUUID()}.txt`;
const content = 'Windi R2 connection test ' + randomUUID() + '\n';
let attempted = false;
async function record(name, response) {
  checks[name + 'Http'] = response.status;
  if (!response.ok) {
    const text = await response.text();
    const code = text.match(/<Code>([A-Za-z0-9]+)<\/Code>/)?.[1];
    if (code) checks[name + 'Error'] = code;
  }
  return response.ok;
}
try {
  checks.readBucket = await record('readBucket', await signed('GET', '', '', { 'list-type': '2', 'max-keys': '1', prefix: 'sachnoi/' }));
  if (checks.readBucket && checks.bucketMatchesSelected) {
    attempted = true;
    checks.writeObject = await record('writeObject', await signed('PUT', marker, content));
    if (checks.writeObject) {
      const download = new URL(publicBase.href.replace(/\/$/, '') + '/' + marker.split('/').map(encode).join('/'));
      const publicResult = await fetch(download, { redirect: 'error', signal: AbortSignal.timeout(20000) });
      checks.publicDownloadHttp = publicResult.status;
      checks.publicDownloadMatches = publicResult.ok && hash(await publicResult.text()) === hash(content);
    }
  }
} catch (error) {
  checks.networkError = ['ENOTFOUND', 'ECONNREFUSED', 'ETIMEDOUT', 'ECONNRESET'].includes(error.cause?.code) ? error.cause.code : error.name;
} finally {
  if (attempted) {
    try {
      checks.deletedTestObject = await record('deleteObject', await signed('DELETE', marker));
      if (checks.deletedTestObject) {
        const after = await signed('HEAD', marker);
        checks.testObjectAbsent = after.status === 404;
      }
    } catch { checks.deletedTestObject = false; }
  }
  mkdirSync('.qa/r2', { recursive: true });
  const report = { at: new Date().toISOString(), checks, uploadedMusicOrModels: false };
  // A failed cleanup records only the non-sensitive, random marker key for recovery.
  if (attempted && !checks.deletedTestObject) report.cleanupObjectKey = marker;
  writeFileSync('.qa/r2/connection.json', JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
if (!['bucketMatchesSelected', 'readBucket', 'writeObject', 'publicDownloadMatches', 'deletedTestObject', 'testObjectAbsent'].every(key => checks[key] === true)) process.exitCode = 1;
