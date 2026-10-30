import { mkdir } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';

const schema = [
  `CREATE TABLE IF NOT EXISTS windi_qr_orders (
    id TEXT PRIMARY KEY, project TEXT NOT NULL, account TEXT NOT NULL, code TEXT NOT NULL,
    idempotency_key TEXT NOT NULL, fingerprint TEXT NOT NULL, data TEXT NOT NULL,
    UNIQUE(project, idempotency_key), UNIQUE(account, code))`,
  `CREATE TABLE IF NOT EXISTS windi_qr_events (
    account TEXT NOT NULL, transaction_id TEXT NOT NULL, order_id TEXT NOT NULL,
    data TEXT NOT NULL, PRIMARY KEY(account, transaction_id))`,
];
const sqliteQueues = new Map();
const postgresSql = sql => sql.replace(/\bwindi_qr_(orders|events)\b/g, name => `windi_qr_private.${name}`);

// A transaction encloses lookup, replay protection, validation, and the paid transition.
// PostgreSQL uses one client and an account-scoped transaction lock across instances.
export async function createPostgresStore(pool) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query("SELECT pg_advisory_xact_lock(hashtextextended('windi-qr-schema-v1', 0))");
    await client.query('CREATE SCHEMA IF NOT EXISTS windi_qr_private');
    await client.query('REVOKE ALL ON SCHEMA windi_qr_private FROM PUBLIC');
    for (const sql of schema) await client.query(postgresSql(sql));
    for (const name of ['windi_qr_orders', 'windi_qr_events']) {
      await client.query(`ALTER TABLE windi_qr_private.${name} ENABLE ROW LEVEL SECURITY`);
      await client.query(`REVOKE ALL ON windi_qr_private.${name} FROM PUBLIC`);
    }
    // Supabase's browser roles may inherit table grants from default privileges.
    // Only the backend table owner/service role should access payment records.
    await client.query(`DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON SCHEMA windi_qr_private FROM anon;
        REVOKE ALL ON ALL TABLES IN SCHEMA windi_qr_private FROM anon;
      END IF;
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON SCHEMA windi_qr_private FROM authenticated;
        REVOKE ALL ON ALL TABLES IN SCHEMA windi_qr_private FROM authenticated;
      END IF;
    END $$`);
    await client.query('COMMIT');
  } catch (error) { await client.query('ROLLBACK'); throw error; }
  finally { client.release(); }
  return {
    transaction: async (account, work) => {
      const connection = await pool.connect();
      try {
        await connection.query('BEGIN');
        await connection.query('SELECT pg_advisory_xact_lock(hashtextextended($1, 0))', [`windi-qr:${account}`]);
        const result = await work((sql, args = []) => connection.query(postgresSql(sql), args));
        await connection.query('COMMIT');
        return result;
      } catch (error) { await connection.query('ROLLBACK'); throw error; }
      finally { connection.release(); }
    },
    close: () => pool.end(),
  };
}

export async function createSqliteStore(path) {
  const { DatabaseSync } = await import('node:sqlite');
  if (path !== ':memory:') await mkdir(dirname(resolve(path)), { recursive: true });
  const db = new DatabaseSync(path);
  db.exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;');
  for (const sql of schema) db.exec(sql);
  // Avoid blocking the event loop when two connections use the same file.
  const key = path === ':memory:' ? Symbol() : resolve(path);
  if (!sqliteQueues.has(key)) sqliteQueues.set(key, { pending: Promise.resolve(), refs: 0 });
  const queue = sqliteQueues.get(key);
  queue.refs++;
  const query = async (sql, args = []) => {
    // Numbered PostgreSQL placeholders are bound by name in SQLite.
    const params = Object.fromEntries(args.map((value, index) => [`$${index + 1}`, value]));
    const statement = db.prepare(sql);
    return { rows: statement.all(params) };
  };
  return {
    transaction: (_account, work) => {
      const result = queue.pending.then(async () => {
        db.exec('BEGIN IMMEDIATE');
        try { const value = await work(query); db.exec('COMMIT'); return value; }
        catch (error) { db.exec('ROLLBACK'); throw error; }
      });
      queue.pending = result.catch(() => {});
      return result;
    },
    close: async () => { await queue.pending; db.close(); if (--queue.refs === 0) sqliteQueues.delete(key); },
  };
}
