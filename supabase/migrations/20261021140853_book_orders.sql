-- Additive per-book ledger. Annual-license records are deliberately retained.
begin;
create table public.wsn_book_devices (
 device_code text primary key check(device_code ~ '^SN[A-F0-9]{12}$'),
 secret_hash text not null check(secret_hash ~ '^[a-f0-9]{64}$'),
 trials_used integer not null default 0 check(trials_used between 0 and 3),
 created_at timestamptz not null default now()
);
create table public.wsn_book_orders (
 id uuid primary key default gen_random_uuid(),
 device_code text not null references public.wsn_book_devices,
 request_key text not null check(request_key ~ '^[a-f0-9]{32}$'),
 kind text not null check(kind in ('book','trial')),
 payment_code text not null unique default ('SB'||upper(replace(gen_random_uuid()::text,'-',''))),
 content_hash text not null check(content_hash ~ '^[a-f0-9]{64}$'),
 payload jsonb not null,
 character_count integer not null check(character_count between 1 and 2000000),
 amount_vnd integer not null check(amount_vnd>=0),
 pricing_version text not null default 'book-v1',
 state text not null check(state in ('awaiting_payment','queued','processing','ready','failed','expired')),
 expires_at timestamptz not null default now()+interval '30 minutes',
 paid_at timestamptz,
 claim_token uuid,
 results jsonb not null default '[]',
 error text not null default '',
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(device_code,request_key),
 check((kind='trial' and amount_vnd=0 and character_count<=500) or (kind='book' and amount_vnd>=10000))
);
create index wsn_book_queue on public.wsn_book_orders(created_at) where state='queued';
create index wsn_book_device_history on public.wsn_book_orders(device_code,created_at desc);
create table public.wsn_book_receipts (
 bank_account text not null,
 transaction_id text not null,
 order_id uuid not null unique references public.wsn_book_orders,
 amount_vnd integer not null check(amount_vnd>0),
 paid_at timestamptz not null,
 primary key(bank_account,transaction_id)
);
create function public.wsn_book_price(p_characters integer) returns integer
language plpgsql immutable security invoker set search_path=pg_catalog as $$
begin
 if p_characters is null or p_characters<1 or p_characters>2000000 then raise exception 'Invalid character count';end if;
 return case when p_characters<=27000 then 10000 when p_characters<=54000 then 25000
 when p_characters<=108000 then 40000 else 40000+ceil((p_characters-108000)/54000.0)::integer*10000 end;
end;$$;
create function public.wsn_book_create(p_device text,p_secret text,p_payload jsonb,p_kind text,p_request text)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.wsn_book_devices; o public.wsn_book_orders; s jsonb; items jsonb='[]';
 total integer=0; remaining integer=500; snippet text; original_hash text; start_page integer;
begin
 if p_device is null or p_device !~ '^SN[A-F0-9]{12}$' or p_secret is null or p_secret !~ '^[a-f0-9]{64}$'
 or p_request is null or p_request !~ '^[a-f0-9]{32}$' or p_kind is null or p_kind not in ('book','trial') then raise exception 'Invalid identity';end if;
 if p_payload is null or jsonb_typeof(p_payload) is distinct from 'object'
 or jsonb_typeof(p_payload->'segments') is distinct from 'array' then raise exception 'Invalid book';end if;
 if p_payload->>'revision' is distinct from 'pro-cloud-modal-v1' or p_payload->>'language' is distinct from 'vi'
 or coalesce(p_payload->>'voice','') not in ('voice-002','voice-003','voice-004','voice-006','voice-007','voice-008')
 or jsonb_array_length(p_payload->'segments') not between 1 and 20000
 or length(coalesce(p_payload->>'title','')) not between 1 and 500
 or coalesce(p_payload->>'openingPage','') !~ '^\d{1,6}$' then raise exception 'Invalid book settings';end if;
 start_page=(p_payload->>'openingPage')::integer;
 for s in select value from jsonb_array_elements(p_payload->'segments') loop
  if jsonb_typeof(s->'text') is distinct from 'string' or length(s->>'text') not between 1 and 2000
  or coalesce(s->>'id','') !~ '^[a-f0-9]{32}$' or coalesce(s->>'page','') !~ '^\d{1,6}$'
  or coalesce(s->>'index','') !~ '^\d{1,6}$' then raise exception 'Invalid segment';end if;
  total=total+length(s->>'text');
  if p_kind='book' then items=items||jsonb_build_array(s);
  elsif (s->>'page')::integer>=start_page and remaining>0 then
   snippet=left(s->>'text',remaining);items=items||jsonb_build_array(s||jsonb_build_object('text',snippet));remaining=remaining-length(snippet);
  end if;
 end loop;
 if total>2000000 or jsonb_array_length(items)=0 then raise exception 'Invalid book size';end if;
 if (select count(distinct value->>'id') from jsonb_array_elements(items))<>jsonb_array_length(items)
 or (select count(distinct value->>'index') from jsonb_array_elements(items))<>jsonb_array_length(items) then raise exception 'Duplicate segment';end if;
 -- Bind both the paid version and a trial to the original complete snapshot.
 original_hash=encode(sha256(convert_to(p_payload::text,'UTF8')),'hex');
 p_payload=jsonb_build_object('title',p_payload->>'title','voice',p_payload->>'voice','language','vi',
  'revision','pro-cloud-modal-v1','segments',items);
 total=(select sum(length(value->>'text')) from jsonb_array_elements(items));
 perform pg_advisory_xact_lock(hashtextextended('wsn/books/device/'||p_device,0));
 insert into public.wsn_book_devices(device_code,secret_hash) values(p_device,p_secret) on conflict do nothing;
 select * into d from public.wsn_book_devices where device_code=p_device for update;
 if d.secret_hash<>p_secret then raise exception 'Device key mismatch';end if;
 select * into o from public.wsn_book_orders where device_code=p_device and request_key=p_request;
 if found then
  if o.content_hash<>original_hash or o.kind<>p_kind then raise exception 'Request conflict';end if;
  return to_jsonb(o)-'claim_token';
 end if;
 -- An identical full-book purchase is reusable, including after an app restart.
 if p_kind='book' then
  select * into o from public.wsn_book_orders where device_code=p_device and kind='book'
   and content_hash=original_hash and (state in ('queued','processing','ready','failed') or (state='awaiting_payment' and expires_at>now()))
   order by created_at desc limit 1;
  if found then return to_jsonb(o)-'claim_token';end if;
 else
  if d.trials_used>=3 then raise exception 'Trial limit reached';end if;
  update public.wsn_book_devices set trials_used=trials_used+1 where device_code=p_device;
 end if;
 insert into public.wsn_book_orders(device_code,request_key,kind,content_hash,payload,character_count,amount_vnd,state)
 values(p_device,p_request,p_kind,original_hash,p_payload,total,case when p_kind='trial' then 0 else public.wsn_book_price(total) end,
 case when p_kind='trial' then 'queued' else 'awaiting_payment' end) returning * into o;
 return to_jsonb(o)-'claim_token';
end;$$;
create function public.wsn_book_confirm(p_code text,p_transaction text,p_account text,p_expected_account text,p_amount integer,p_paid_at timestamptz)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare o public.wsn_book_orders; r public.wsn_book_receipts;
begin
 if p_transaction is null or p_transaction !~ '^[A-Za-z0-9_-]{1,128}$' or p_account is null
 or p_account !~ '^[0-9]{6,32}$' or p_account is distinct from p_expected_account
 or p_paid_at is null or not isfinite(p_paid_at) or p_paid_at>now()+interval '5 minutes' then raise exception 'Invalid receipt';end if;
 perform pg_advisory_xact_lock(hashtextextended('wsn/receipt/'||p_account||'/'||p_transaction,0));
 select * into o from public.wsn_book_orders where payment_code=p_code for update;
 if not found or o.kind<>'book' then raise exception 'Unknown book order';end if;
 if p_amount is distinct from o.amount_vnd or p_paid_at<o.created_at-interval '1 minute' or p_paid_at>o.expires_at then raise exception 'Receipt does not match quote';end if;
 select * into r from public.wsn_book_receipts where bank_account=p_account and transaction_id=p_transaction;
 if found then
  if r.order_id<>o.id or r.amount_vnd<>p_amount or r.paid_at<>p_paid_at then raise exception 'Receipt conflict';end if;
  return jsonb_build_object('status','duplicate','orderId',o.id);
 end if;
 if exists(select 1 from public.wsn_payments where bank_account=p_account and provider_transaction_id=p_transaction)
 or o.paid_at is not null then raise exception 'Receipt already used';end if;
 insert into public.wsn_book_receipts values(p_account,p_transaction,o.id,p_amount,p_paid_at);
 update public.wsn_book_orders set paid_at=p_paid_at,state='queued',updated_at=now() where id=o.id;
 return jsonb_build_object('status','paid','orderId',o.id);
end;$$;
create function public.wsn_book_claim(p_order uuid default null) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare o public.wsn_book_orders;
begin
 select * into o from public.wsn_book_orders where state='queued' and (p_order is null or id=p_order)
 order by created_at for update skip locked limit 1;
 if not found then return null;end if;
 if o.kind='book' and o.paid_at is null then raise exception 'Unpaid book';end if;
 update public.wsn_book_orders set state='processing',claim_token=gen_random_uuid(),updated_at=now()
 where id=o.id returning * into o;
 return to_jsonb(o);
end;$$;
create function public.wsn_book_audio(p_order uuid,p_claim uuid,p_segment text,p_sha text)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare o public.wsn_book_orders; item jsonb;
begin
 select * into o from public.wsn_book_orders where id=p_order for update;
 if not found or o.claim_token is distinct from p_claim or o.state not in ('processing','ready')
 or p_sha is null or p_sha !~ '^[a-f0-9]{64}$'
 or not exists(select 1 from jsonb_array_elements(o.payload->'segments') where value->>'id'=p_segment) then raise exception 'Invalid audio claim';end if;
 select value into item from jsonb_array_elements(o.results) where value->>'id'=p_segment;
 if found then
  if item->>'sha256'<>p_sha then raise exception 'Audio conflict';end if;
 else
  o.results=o.results||jsonb_build_array(jsonb_build_object('id',p_segment,'sha256',p_sha,'path',o.id::text||'/'||p_segment||'.wav'));
 end if;
 update public.wsn_book_orders set results=o.results,state=case when jsonb_array_length(o.results)=jsonb_array_length(o.payload->'segments') then 'ready' else 'processing' end,updated_at=now() where id=o.id;
 return jsonb_build_object('done',jsonb_array_length(o.results),'total',jsonb_array_length(o.payload->'segments'));
end;$$;

create function public.wsn_book_immutable() returns trigger language plpgsql security invoker set search_path=pg_catalog as $$
begin
 if (new.device_code,new.request_key,new.kind,new.payment_code,new.content_hash,new.payload,new.character_count,new.amount_vnd,new.pricing_version,new.created_at,new.expires_at)
 is distinct from (old.device_code,old.request_key,old.kind,old.payment_code,old.content_hash,old.payload,old.character_count,old.amount_vnd,old.pricing_version,old.created_at,old.expires_at)
 then raise exception 'Book quote is immutable';end if;
 return new;
end;$$;
create trigger wsn_book_immutable before update on public.wsn_book_orders for each row execute function public.wsn_book_immutable();
revoke all on function public.wsn_book_immutable() from public,anon,authenticated;

-- Only the server can mutate payment, quota, or the job's immutable snapshot.
alter table public.wsn_book_devices enable row level security;
alter table public.wsn_book_orders enable row level security;
alter table public.wsn_book_receipts enable row level security;
revoke all on public.wsn_book_devices,public.wsn_book_orders,public.wsn_book_receipts from public,anon,authenticated;
grant select,insert,update on public.wsn_book_devices,public.wsn_book_orders,public.wsn_book_receipts to service_role;
revoke all on function public.wsn_book_price(integer),public.wsn_book_create(text,text,jsonb,text,text),public.wsn_book_confirm(text,text,text,text,integer,timestamptz),public.wsn_book_claim(uuid),public.wsn_book_audio(uuid,uuid,text,text) from public,anon,authenticated;
grant execute on function public.wsn_book_price(integer),public.wsn_book_create(text,text,jsonb,text,text),public.wsn_book_confirm(text,text,text,text,integer,timestamptz),public.wsn_book_claim(uuid),public.wsn_book_audio(uuid,uuid,text,text) to service_role;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types) values('wsn-book-audio','wsn-book-audio',false,52428800,array['audio/wav']) on conflict(id) do nothing;
create or replace function public.wsn_accept_payment(
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
  if exists(select 1 from public.wsn_book_receipts where bank_account=p_bank_account and transaction_id=p_transaction_id) then raise exception 'Receipt already used for a book';end if;
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

commit;
