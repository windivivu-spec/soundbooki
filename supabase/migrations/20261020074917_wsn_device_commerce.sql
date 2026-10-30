-- Sách Nói only: no changes to existing ecosystem tables, users or storage.
begin;
create table public.wsn_payments (
  id uuid primary key default gen_random_uuid(),
  provider_transaction_id text not null check (provider_transaction_id ~ '^[A-Za-z0-9_-]{1,128}$'),
  bank_account text not null check (bank_account ~ '^[0-9]{6,32}$'),
  device_code text not null check (device_code ~ '^SN[A-F0-9]{12}$'),
  amount_vnd integer not null check (amount_vnd = 189000),
  paid_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (bank_account, provider_transaction_id)
);
create table public.wsn_licenses (
  device_code text primary key check (device_code ~ '^SN[A-F0-9]{12}$'),
  latest_payment_id uuid not null references public.wsn_payments(id),
  expires_at timestamptz not null,
  revision integer not null default 1 check (revision > 0),
  license_payload jsonb not null,
  updated_at timestamptz not null default now()
);
alter table public.wsn_payments enable row level security;
alter table public.wsn_licenses enable row level security;
revoke all on public.wsn_payments, public.wsn_licenses from public, anon, authenticated;
grant select, insert, update on public.wsn_payments, public.wsn_licenses to service_role;
create function public.wsn_accept_payment(
  p_transaction_id text, p_bank_account text, p_device_code text,
  p_amount_vnd integer, p_paid_at timestamptz
) returns jsonb language plpgsql security invoker
set search_path = pg_catalog, public set timezone = 'UTC'
as $$
declare
  receipt public.wsn_payments;
  previous public.wsn_licenses;
  expiry timestamptz;
  license jsonb;
begin
  if p_device_code is null or p_device_code !~ '^SN[A-F0-9]{12}$'
    or p_transaction_id is null or p_transaction_id !~ '^[A-Za-z0-9_-]{1,128}$'
    or p_bank_account is null or p_bank_account !~ '^[0-9]{6,32}$'
    or p_amount_vnd is distinct from 189000
    or p_paid_at is null or not isfinite(p_paid_at)
    or p_paid_at < '2026-10-20T00:00:00+07:00'::timestamptz
    or p_paid_at > now() + interval '5 minutes' then
    raise exception 'Invalid Sách Nói receipt' using errcode = '22023';
  end if;
  -- Consistent lock order serializes duplicate callbacks and concurrent renewals.
  perform pg_advisory_xact_lock(hashtextextended('wsn/receipt/' || p_bank_account || '/' || p_transaction_id, 0));
  perform pg_advisory_xact_lock(hashtextextended('wsn/device/' || p_device_code, 0));
  select * into receipt from public.wsn_payments
    where bank_account = p_bank_account and provider_transaction_id = p_transaction_id;
  if found then
    if receipt.device_code <> p_device_code or receipt.amount_vnd <> p_amount_vnd or receipt.paid_at <> p_paid_at then
      raise exception 'Receipt conflict' using errcode = '22023';
    end if;
    select * into previous from public.wsn_licenses where device_code = p_device_code;
    return jsonb_build_object('status', 'duplicate', 'payload', previous.license_payload);
  end if;
  select * into previous from public.wsn_licenses where device_code = p_device_code;
  expiry := greatest(p_paid_at, previous.expires_at) + interval '1 year';
  insert into public.wsn_payments(provider_transaction_id, bank_account, device_code, amount_vnd, paid_at)
    values(p_transaction_id, p_bank_account, p_device_code, p_amount_vnd, p_paid_at) returning * into receipt;
  license := jsonb_build_object('schema', 2, 'product', 'windi-sach-noi-pro',
    'orderId', 'sepay-' || receipt.id::text, 'deviceCode', p_device_code,
    'issuedAt', to_char(least(p_paid_at, now()), 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'),
    'expiresAt', to_char(expiry, 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'));
  insert into public.wsn_licenses(device_code, latest_payment_id, expires_at, license_payload)
    values(p_device_code, receipt.id, expiry, license)
    on conflict(device_code) do update set latest_payment_id = excluded.latest_payment_id,
      expires_at = excluded.expires_at, license_payload = excluded.license_payload,
      revision = public.wsn_licenses.revision + 1, updated_at = now();
  return jsonb_build_object('status', 'paid', 'payload', license);
end;
$$;
revoke all on function public.wsn_accept_payment(text,text,text,integer,timestamptz) from public, anon, authenticated;
grant execute on function public.wsn_accept_payment(text,text,text,integer,timestamptz) to service_role;
comment on table public.wsn_payments is 'Sách Nói verified SePay receipts; backend access only.';
comment on table public.wsn_licenses is 'Sách Nói annual device entitlements; signed by the license Edge Function.';
commit;
