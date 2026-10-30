-- Local preparation only; no live activation. Preserve all old quotes/payments.
begin;
create table public.wsn_launch_bundles (
 id uuid primary key default gen_random_uuid(),
 device_code text not null unique references public.wsn_book_devices,
 source_order_id uuid not null unique references public.wsn_book_orders,
 paid_at timestamptz not null,
 expires_at timestamptz not null check(expires_at='2026-11-02T00:00:00+07:00'::timestamptz)
);
create table public.wsn_launch_redemptions (
 bundle_id uuid not null references public.wsn_launch_bundles,
 slot integer not null check(slot between 1 and 5),
 order_id uuid not null unique references public.wsn_book_orders,
 created_at timestamptz not null default now(),
 primary key(bundle_id,slot)
);
alter table public.wsn_book_orders add column funding_bundle_id uuid references public.wsn_launch_bundles;
alter table public.wsn_book_orders drop constraint wsn_book_orders_kind_check;
alter table public.wsn_book_orders add constraint wsn_book_orders_kind_check check(kind in ('book','trial','bundle'));
alter table public.wsn_book_orders drop constraint wsn_book_orders_check;
alter table public.wsn_book_orders add constraint wsn_book_orders_check check(
 (kind='trial' and amount_vnd=0 and character_count<=4000 and funding_bundle_id is null)
 or (kind='book' and ((amount_vnd>=10000 and funding_bundle_id is null) or (amount_vnd=0 and funding_bundle_id is not null)))
 or (kind='bundle' and amount_vnd=50000 and character_count=1 and funding_bundle_id is null)
);
create index wsn_launch_book_queue on public.wsn_book_orders(device_code,funding_bundle_id,state) where funding_bundle_id is not null;
create function public.wsn_launch_active(p_at timestamptz default now()) returns boolean
language sql immutable security invoker set search_path=pg_catalog as $$
 select p_at>='2026-10-22T00:00:00+07:00'::timestamptz and p_at<'2026-11-02T00:00:00+07:00'::timestamptz;
$$;
create function public.wsn_launch_status(p_device text,p_secret text) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.wsn_book_devices; b public.wsn_launch_bundles; o public.wsn_book_orders; used integer=0;
begin
 if p_device is null or p_device!~'^SN[A-F0-9]{12}$' or p_secret is null or p_secret!~'^[a-f0-9]{64}$' then raise exception 'Invalid identity';end if;
 select * into d from public.wsn_book_devices where device_code=p_device;
 if found and d.secret_hash<>p_secret then raise exception 'Device key mismatch';end if;
 select * into b from public.wsn_launch_bundles where device_code=p_device;
 if found then select count(*) into used from public.wsn_launch_redemptions where bundle_id=b.id;end if;
 select * into o from public.wsn_book_orders where device_code=p_device and kind='bundle' order by created_at desc,id desc limit 1;
 return jsonb_build_object('offer',jsonb_build_object('id','launch-combo-v1','active',public.wsn_launch_active(now()),'amountVND',50000,'books',5,
 'endsAt','2026-11-01T17:00:00Z','serverTime',now()),
 'bundle',case when b.id is not null then jsonb_build_object('id',b.id,'used',used,'remaining',5-used,'expiresAt',b.expires_at) else null end,
 'order',case when o.id is not null then (to_jsonb(o)-'claim_token'-'payload'-'results')||jsonb_build_object('bank',o.payload->'bank') else null end);
end;$$;
create function public.wsn_launch_quote(p_device text,p_secret text,p_request text,p_bank jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.wsn_book_devices; o public.wsn_book_orders; data jsonb='{"title":"Combo ra mắt · 5 cuốn","revision":"launch-combo-v1","segments":[]}';
begin
 if p_device is null or p_device!~'^SN[A-F0-9]{12}$' or p_secret is null or p_secret!~'^[a-f0-9]{64}$'
 or p_request is null or p_request!~'^[a-f0-9]{32}$' then raise exception 'Invalid identity';end if;
 if p_bank is null or jsonb_typeof(p_bank) is distinct from 'object' or coalesce(p_bank->>'account','')!~'^[0-9]{6,32}$'
 or coalesce(p_bank->>'bin','')!~'^[0-9]{6}$' or length(coalesce(p_bank->>'holder','')) not between 1 and 200
 or length(coalesce(p_bank->>'name','')) not between 1 and 100 then raise exception 'Invalid receiving bank';end if;
 data=data||jsonb_build_object('bank',jsonb_build_object('account',p_bank->>'account','bin',p_bank->>'bin','holder',p_bank->>'holder','name',p_bank->>'name'));
 perform pg_advisory_xact_lock(hashtextextended('wsn/books/device/'||p_device,0));
 insert into public.wsn_book_devices(device_code,secret_hash) values(p_device,p_secret) on conflict do nothing;
 select * into d from public.wsn_book_devices where device_code=p_device for update;
 if d.secret_hash<>p_secret then raise exception 'Device key mismatch';end if;
 select * into o from public.wsn_book_orders where device_code=p_device and request_key=p_request;
 if found then
  if o.kind<>'bundle' then raise exception 'Request conflict';end if;
  return to_jsonb(o)-'claim_token';
 end if;
 if not public.wsn_launch_active(now()) then raise exception 'Ưu đãi đã kết thúc.';end if;
 if exists(select 1 from public.wsn_launch_bundles where device_code=p_device) then raise exception 'Mỗi Mac chỉ mua một combo.';end if;
 select * into o from public.wsn_book_orders where device_code=p_device and kind='bundle' and state='awaiting_payment' and expires_at>now() order by created_at desc limit 1;
 if found then return to_jsonb(o)-'claim_token';end if;
 insert into public.wsn_book_orders(device_code,request_key,kind,content_hash,payload,character_count,amount_vnd,state,pricing_version,expires_at)
 values(p_device,p_request,'bundle',encode(sha256(convert_to(data::text,'UTF8')),'hex'),data,1,50000,'awaiting_payment','launch-combo-v1',
 least(now()+interval '10 minutes','2026-11-02T00:00:00+07:00'::timestamptz)) returning * into o;
 return to_jsonb(o)-'claim_token';
end;$$;
create or replace function public.wsn_book_immutable() returns trigger language plpgsql security invoker set search_path=pg_catalog as $$
begin
 if (new.device_code,new.request_key,new.kind,new.payment_code,new.content_hash,new.payload,new.character_count,new.amount_vnd,new.pricing_version,new.created_at,new.expires_at,new.funding_bundle_id)
 is distinct from (old.device_code,old.request_key,old.kind,old.payment_code,old.content_hash,old.payload,old.character_count,old.amount_vnd,old.pricing_version,old.created_at,old.expires_at,old.funding_bundle_id)
 then raise exception 'Book quote is immutable';end if;
 return new;
end;$$;
create or replace function public.wsn_book_create(p_device text,p_secret text,p_payload jsonb,p_kind text,p_request text)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.wsn_book_devices; o public.wsn_book_orders; s jsonb; items jsonb='[]';
 total integer=0; remaining integer=4000; snippet text; original_hash text; start_page integer; grant_row public.wsn_launch_bundles; slots integer; funded uuid;
begin
 if p_device is null or p_device !~ '^SN[A-F0-9]{12}$' or p_secret is null or p_secret !~ '^[a-f0-9]{64}$'
 or p_request is null or p_request !~ '^[a-f0-9]{32}$' or p_kind is null or p_kind not in ('book','trial','bundle_book') then raise exception 'Invalid identity';end if;
 if p_payload is null or jsonb_typeof(p_payload) is distinct from 'object'
 or jsonb_typeof(p_payload->'segments') is distinct from 'array' then raise exception 'Invalid book';end if;
 if p_payload->>'language' is distinct from 'vi' or coalesce(p_payload->>'revision','') not in ('pro-cloud-modal-v1','pro-cloud-heygen-v1') or not (
 (p_payload->>'revision'='pro-cloud-modal-v1' and coalesce(p_payload->>'voice','') in ('voice-002','voice-003','voice-004','voice-006','voice-007','voice-008'))
 or (p_payload->>'revision'='pro-cloud-heygen-v1' and coalesce(p_payload->>'voice','') in ('3414fd7fdaa64e619fb8b021534ce368','3ab886ca76924521bbed407e45762540','eff592346cac4febbba5d5fef4621ff0','b241299543834cd8994186e600280e25','60dce6af562449f294ceeddb4130a9ee','6a92e2ed9d3843f2b059ef8e6809366c','5ee4ba10bd0446ba85421ab177462aba')))
 or jsonb_array_length(p_payload->'segments') not between 1 and 20000
 or length(coalesce(p_payload->>'title','')) not between 1 and 500
 or coalesce(p_payload->>'openingPage','') !~ '^\d{1,6}$' then raise exception 'Invalid book settings';end if;
 start_page=(p_payload->>'openingPage')::integer;
 for s in select value from jsonb_array_elements(p_payload->'segments') loop
  if jsonb_typeof(s->'text') is distinct from 'string' or length(s->>'text') not between 1 and 2000
  or coalesce(s->>'id','') !~ '^[a-f0-9]{32}$' or coalesce(s->>'page','') !~ '^\d{1,6}$'
  or coalesce(s->>'index','') !~ '^\d{1,6}$' then raise exception 'Invalid segment';end if;
  total=total+length(s->>'text');
  if p_kind<>'trial' then items=items||jsonb_build_array(s);
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
  'revision',p_payload->>'revision','audioRevision',case when p_payload->>'revision'='pro-cloud-heygen-v1' then 'pro-cloud-heygen-v1-audio-v1' else 'pro-cloud-modal-v1-quality-v1' end,'segments',items);
 total=(select sum(length(value->>'text')) from jsonb_array_elements(items));
 perform pg_advisory_xact_lock(hashtextextended('wsn/books/device/'||p_device,0));
 insert into public.wsn_book_devices(device_code,secret_hash) values(p_device,p_secret) on conflict do nothing;
 select * into d from public.wsn_book_devices where device_code=p_device for update;
 if d.secret_hash<>p_secret then raise exception 'Device key mismatch';end if;
 select * into o from public.wsn_book_orders where device_code=p_device and request_key=p_request;
 if found then
  if o.content_hash<>original_hash or o.kind<>(case when p_kind='bundle_book' then 'book' else p_kind end) or (p_kind='bundle_book' and o.funding_bundle_id is null) then raise exception 'Request conflict';end if;
  return to_jsonb(o)-'claim_token';
 end if;
 -- An identical full-book purchase is reusable, including after an app restart.
 if p_kind<>'trial' then
  select * into o from public.wsn_book_orders where device_code=p_device and kind='book'
   and content_hash=original_hash and (p_kind<>'bundle_book' or paid_at is not null) and (state in ('queued','processing','ready','failed') or (state='awaiting_payment' and expires_at>now()))
   order by created_at desc limit 1;
  if found then return to_jsonb(o)-'claim_token';end if;
 else
  if d.trials_used>=10 then raise exception 'Trial limit reached';end if;
  update public.wsn_book_devices set trials_used=trials_used+1 where device_code=p_device;
 end if;
 if p_kind='bundle_book' then
  if not public.wsn_launch_active(now()) then raise exception 'Combo đã hết hạn sử dụng lúc 23:59 ngày 01/11/2026.';end if;
  select * into grant_row from public.wsn_launch_bundles where device_code=p_device for update;
  if not found then raise exception 'Mac này chưa có combo đã thanh toán.';end if;
  if grant_row.expires_at<=now() then raise exception 'Combo đã hết hạn sử dụng.';end if;
  select count(*) into slots from public.wsn_launch_redemptions where bundle_id=grant_row.id;
  if slots>=5 then raise exception 'Mac này đã dùng đủ 5 cuốn của combo.';end if;
  funded=grant_row.id;
 end if;
 insert into public.wsn_book_orders(device_code,request_key,kind,content_hash,payload,character_count,amount_vnd,state,pricing_version,funding_bundle_id,paid_at)
 values(p_device,p_request,case when p_kind='bundle_book' then 'book' else p_kind end,original_hash,p_payload,total,
 case when p_kind in ('trial','bundle_book') then 0 else public.wsn_book_price(total) end,
 case when p_kind in ('trial','bundle_book') then 'queued' else 'awaiting_payment' end,
 case when p_kind='bundle_book' then 'launch-combo-v1' else 'book-v1' end,funded,
 case when p_kind='bundle_book' then grant_row.paid_at else null end) returning * into o;
 if funded is not null then
  insert into public.wsn_launch_redemptions(bundle_id,slot,order_id) values(funded,slots+1,o.id);
 end if;
 return to_jsonb(o)-'claim_token';
end;$$;
create or replace function public.wsn_book_confirm(p_code text,p_transaction text,p_account text,p_expected_account text,p_amount integer,p_paid_at timestamptz)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare o public.wsn_book_orders; r public.wsn_book_receipts;
begin
 if p_transaction is null or p_transaction !~ '^[A-Za-z0-9_-]{1,128}$' or p_account is null
 or p_account !~ '^[0-9]{6,32}$' or p_account is distinct from p_expected_account
 or p_paid_at is null or not isfinite(p_paid_at) or p_paid_at>now()+interval '5 minutes' then raise exception 'Invalid receipt';end if;
 perform pg_advisory_xact_lock(hashtextextended('wsn/receipt/'||p_account||'/'||p_transaction,0));
 select * into o from public.wsn_book_orders where payment_code=p_code;
 if found and o.kind='bundle' then perform pg_advisory_xact_lock(hashtextextended('wsn/books/device/'||o.device_code,0));end if;
 select * into o from public.wsn_book_orders where payment_code=p_code for update;
 if not found or o.kind not in ('book','bundle') or o.funding_bundle_id is not null then raise exception 'Unknown book order';end if;
 if p_amount is distinct from o.amount_vnd or p_paid_at<o.created_at-interval '1 minute' or p_paid_at>o.expires_at then raise exception 'Receipt does not match quote';end if;
 select * into r from public.wsn_book_receipts where bank_account=p_account and transaction_id=p_transaction;
 if found then
  if r.order_id<>o.id or r.amount_vnd<>p_amount or r.paid_at<>p_paid_at then raise exception 'Receipt conflict';end if;
  return jsonb_build_object('status','duplicate','orderId',o.id);
 end if;
 if exists(select 1 from public.wsn_payments where bank_account=p_account and provider_transaction_id=p_transaction)
 or o.paid_at is not null then raise exception 'Receipt already used';end if;
 if o.kind='bundle' then
  if o.payload->'bank'->>'account' is distinct from p_account then raise exception 'Receipt bank does not match quote';end if;
  -- Same device lock order as create/redeem. Claiming the bank receipt stays first.
  perform pg_advisory_xact_lock(hashtextextended('wsn/books/device/'||o.device_code,0));
  if exists(select 1 from public.wsn_launch_bundles where device_code=o.device_code) then raise exception 'Mac đã mua combo; cần đối soát khoản chuyển thêm.';end if;
 end if;
 insert into public.wsn_book_receipts values(p_account,p_transaction,o.id,p_amount,p_paid_at);
 update public.wsn_book_orders set paid_at=p_paid_at,state=case when o.kind='bundle' then 'ready' else 'queued' end,updated_at=now() where id=o.id;
 if o.kind='bundle' then
  insert into public.wsn_launch_bundles(device_code,source_order_id,paid_at,expires_at)
  values(o.device_code,o.id,p_paid_at,'2026-11-02T00:00:00+07:00');
 end if;
 return jsonb_build_object('status','paid','orderId',o.id);
end;$$;

-- Legacy operator is Modal-only; HeyGen queue activation remains separate.
create or replace function public.wsn_book_claim(p_order uuid default null) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare o public.wsn_book_orders;
begin
 select * into o from public.wsn_book_orders where state='queued' and payload->>'revision'='pro-cloud-modal-v1' and (p_order is null or id=p_order)
 order by created_at for update skip locked limit 1;
 if not found then return null;end if;
 if o.kind='book' and o.paid_at is null then raise exception 'Unpaid book';end if;
 update public.wsn_book_orders set state='processing',claim_token=gen_random_uuid(),updated_at=now()
 where id=o.id returning * into o;
 return to_jsonb(o);
end;$$;

alter table public.wsn_launch_bundles enable row level security;
alter table public.wsn_launch_redemptions enable row level security;
revoke all on public.wsn_launch_bundles,public.wsn_launch_redemptions from public,anon,authenticated;
grant select,insert on public.wsn_launch_bundles,public.wsn_launch_redemptions to service_role;
revoke all on function public.wsn_launch_active(timestamptz),public.wsn_launch_status(text,text),public.wsn_launch_quote(text,text,text,jsonb) from public,anon,authenticated;
grant execute on function public.wsn_launch_active(timestamptz),public.wsn_launch_status(text,text),public.wsn_launch_quote(text,text,text,jsonb) to service_role;
commit;
