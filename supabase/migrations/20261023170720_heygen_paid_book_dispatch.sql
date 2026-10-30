-- Authorized Mac SePay -> immutable book quote -> fair HeyGen dispatch.
-- Additive: preserve all orders, receipts, trial counters and legacy Modal jobs.
begin;
alter table public.wsn_book_orders add column receiving_bank jsonb;
alter table public.wsn_heygen_control add column dispatch_turn integer not null default 0;
alter table public.wsn_heygen_control add column last_paid_device text;
alter table public.wsn_heygen_control add column last_trial_device text;
alter table public.wsn_heygen_control add column max_pending_segments integer not null default 6000 check(max_pending_segments between 1 and 100000);
create table public.wsn_heygen_dispatches (
 id bigint generated always as identity primary key,
 dispatched_at timestamptz not null,
 order_id uuid not null references public.wsn_book_orders,
 segment_id text not null,
 device_code text not null,
 kind text not null check(kind in ('trial','book'))
);
create index wsn_heygen_dispatch_time on public.wsn_heygen_dispatches(dispatched_at);
alter table public.wsn_heygen_dispatches enable row level security;
revoke all on public.wsn_heygen_dispatches from public,anon,authenticated;
grant select,insert,delete on public.wsn_heygen_dispatches to service_role;
grant usage,select on sequence public.wsn_heygen_dispatches_id_seq to service_role;

create function public.wsn_heygen_pending_segments(p_exclude uuid default null) returns bigint
language sql stable security invoker set search_path=pg_catalog,public as $$
 select coalesce(sum(greatest(0,jsonb_array_length(payload->'segments')-jsonb_array_length(results))),0)::bigint
 from public.wsn_book_orders where id is distinct from p_exclude and payload->>'revision'='pro-cloud-heygen-v1'
 and (state in ('queued','processing') or (kind='book' and state='awaiting_payment' and expires_at>now()) or (kind='book' and paid_at is not null and state='failed'));
$$;
create function public.wsn_heygen_is_funded(p_order uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
 select exists(select 1 from public.wsn_book_orders b where b.id=p_order and b.kind='book' and b.paid_at is not null and (
  exists(select 1 from public.wsn_book_receipts r where r.order_id=b.id and r.amount_vnd=b.amount_vnd and r.paid_at=b.paid_at and (b.receiving_bank is null or r.bank_account=b.receiving_bank->>'account'))
  or exists(select 1 from public.wsn_launch_redemptions x join public.wsn_launch_bundles g on g.id=x.bundle_id
   join public.wsn_book_orders src on src.id=g.source_order_id join public.wsn_book_receipts r on r.order_id=src.id
   where x.order_id=b.id and b.funding_bundle_id=g.id and g.device_code=b.device_code and g.paid_at=b.paid_at and src.paid_at=g.paid_at and r.amount_vnd=50000)));
$$;

create or replace function public.wsn_book_immutable() returns trigger language plpgsql security invoker set search_path=pg_catalog as $$
begin
 if (new.device_code,new.request_key,new.kind,new.payment_code,new.content_hash,new.payload,new.character_count,new.amount_vnd,new.pricing_version,new.created_at,new.expires_at,new.funding_bundle_id,new.trial_units)
 is distinct from (old.device_code,old.request_key,old.kind,old.payment_code,old.content_hash,old.payload,old.character_count,old.amount_vnd,old.pricing_version,old.created_at,old.expires_at,old.funding_bundle_id,old.trial_units)
 then raise exception 'Book quote is immutable';end if;
 if new.receiving_bank is distinct from old.receiving_bank and (old.receiving_bank is not null or old.kind<>'book' or old.state<>'awaiting_payment' or old.paid_at is not null) then raise exception 'Receiving bank is immutable';end if;
 return new;
end;$$;

create function public.wsn_book_quote(p_device text,p_secret text,p_payload jsonb,p_request text,p_bank jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare c public.wsn_heygen_control;o public.wsn_book_orders;v jsonb;
begin
 if p_bank is null or jsonb_typeof(p_bank) is distinct from 'object' or coalesce(p_bank->>'account','')!~'^[0-9]{6,32}$'
 or coalesce(p_bank->>'bin','')!~'^[0-9]{6}$' or length(coalesce(p_bank->>'holder','')) not between 1 and 200
 or length(coalesce(p_bank->>'name','')) not between 1 and 100 then raise exception 'Invalid receiving bank';end if;
 -- One admission lock shared with dispatch and new trial requests.
 select * into c from public.wsn_heygen_control where id for update;
 v=public.wsn_book_create(p_device,p_secret,p_payload,'book',p_request);
 select * into o from public.wsn_book_orders where id=(v->>'id')::uuid for update;
 if o.receiving_bank is not null or o.state<>'awaiting_payment' then return (to_jsonb(o)-'claim_token')||jsonb_build_object('bank',o.receiving_bank);end if;
 if o.payload->>'revision'='pro-cloud-heygen-v1' then
  if c.blocked_until>now()+interval '5 minutes' or public.wsn_heygen_pending_segments(o.id)+jsonb_array_length(o.payload->'segments')>c.max_pending_segments
  then raise exception 'Hàng đợi Pro đang đầy. Vui lòng thử lại sau; chưa cần chuyển khoản.';end if;
  if (select count(*) from public.wsn_book_orders where device_code=p_device and kind='book' and state='awaiting_payment' and expires_at>now() and id<>o.id)>=2
  then raise exception 'Mac này đang có hai đơn chờ thanh toán. Kiểm tra đơn đã có trước.';end if;
 end if;
 update public.wsn_book_orders set receiving_bank=jsonb_build_object('bin',p_bank->>'bin','name',p_bank->>'name','account',p_bank->>'account','holder',p_bank->>'holder') where id=o.id returning * into o;
 return (to_jsonb(o)-'claim_token')||jsonb_build_object('bank',o.receiving_bank);
end;$$;

create or replace function public.wsn_book_create_trial_v2(p_device text,p_secret text,p_payload jsonb,p_kind text,p_request text) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare c public.wsn_heygen_control;v jsonb;
begin
 if p_kind is distinct from 'trial' then raise exception 'Invalid trial';end if;
 select * into c from public.wsn_heygen_control where id for update;
 v=public.wsn_book_create(p_device,p_secret,p_payload,p_kind,p_request);
 if v->>'state' in ('queued','processing') and v->'payload'->>'revision'='pro-cloud-heygen-v1'
 and public.wsn_heygen_pending_segments((v->>'id')::uuid)+jsonb_array_length(v->'payload'->'segments')>c.max_pending_segments
 then raise exception 'Hàng đợi Pro đang đầy. Vui lòng thử lại sau; lượt chưa được trừ.';end if;
 return v;
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
 if o.receiving_bank is not null and o.receiving_bank->>'account' is distinct from p_account then raise exception 'Receipt bank does not match quote';end if;
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

create function public.wsn_heygen_next_v2(p_paid_enabled boolean default false) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare c public.wsn_heygen_control;o public.wsn_book_orders;t public.wsn_heygen_tasks;s jsonb;preferred text;stamp timestamptz;
begin
 select * into c from public.wsn_heygen_control where id for update;
 stamp=clock_timestamp();
 update public.wsn_heygen_tasks set state='uncertain',diagnostic='Worker interrupted after dispatch; reconcile before retry' where state='sending' and started_at<stamp-interval '150 seconds';
 update public.wsn_book_orders b set state='failed',updated_at=stamp where b.state='processing' and exists(select 1 from public.wsn_heygen_tasks q where q.order_id=b.id and q.state in ('uncertain','failed'));
 -- Recovery has no provider POST; paid audio remains tied to a verified receipt.
 select q.* into t from public.wsn_heygen_tasks q join public.wsn_book_orders b on b.id=q.order_id
 where q.state='audio' and q.available_at<=stamp and b.state in ('processing','ready')
 and (b.kind='trial' or (p_paid_enabled and public.wsn_heygen_is_funded(b.id))) order by q.available_at for update of q skip locked limit 1;
 if found then
  update public.wsn_heygen_tasks set available_at=stamp+interval '120 seconds' where order_id=t.order_id and segment_id=t.segment_id;
  select * into o from public.wsn_book_orders where id=t.order_id;
  select value into s from jsonb_array_elements(o.payload->'segments') where value->>'id'=t.segment_id;
  return jsonb_build_object('orderId',o.id,'claim',o.claim_token,'kind',o.kind,'paid',o.paid_at is not null,'segment',s,'voice',o.payload->>'voice','token',t.token,'audioURL',t.audio_url);
 end if;
 if c.next_at>stamp or c.blocked_until>stamp or (select count(*) from public.wsn_heygen_tasks where state='sending')>=3 then return null;end if;
 -- Sliding 60-second window includes every safe provider retry, across all workers.
 delete from public.wsn_heygen_dispatches where dispatched_at<stamp-interval '10 minutes';
 if (select count(*) from public.wsn_heygen_dispatches where dispatched_at>stamp-interval '60 seconds')>=25 then return null;end if;
 -- Four paid turns then one trial turn. Either class borrows unused capacity.
 preferred=case when c.dispatch_turn%5=4 then 'trial' else 'book' end;
 select b.* into o from public.wsn_book_orders b where b.state in ('queued','processing') and b.payload->>'revision'='pro-cloud-heygen-v1'
 and (b.kind='trial' or (p_paid_enabled and b.kind='book' and public.wsn_heygen_is_funded(b.id)))
 and exists(select 1 from jsonb_array_elements(b.payload->'segments') p where not exists(select 1 from public.wsn_heygen_tasks q where q.order_id=b.id and q.segment_id=p->>'id' and (q.state<>'retry' or q.available_at>stamp)))
 order by (b.kind<>preferred),(b.device_code is not distinct from case when b.kind='book' then c.last_paid_device else c.last_trial_device end),b.updated_at,b.created_at,b.id for update skip locked limit 1;
 if not found then return null;end if;
 select p into s from jsonb_array_elements(o.payload->'segments') p where not exists(select 1 from public.wsn_heygen_tasks q where q.order_id=o.id and q.segment_id=p->>'id' and (q.state<>'retry' or q.available_at>stamp)) order by (p->>'index')::int limit 1;
 if o.state='queued' then update public.wsn_book_orders set state='processing',claim_token=gen_random_uuid(),updated_at=stamp where id=o.id returning * into o;end if;
 insert into public.wsn_heygen_tasks(order_id,segment_id,state) values(o.id,s->>'id','sending') on conflict(order_id,segment_id) do update set state='sending',token=gen_random_uuid(),attempt=wsn_heygen_tasks.attempt+1,started_at=stamp returning * into t;
 insert into public.wsn_heygen_dispatches(dispatched_at,order_id,segment_id,device_code,kind) values(stamp,o.id,s->>'id',o.device_code,o.kind);
 update public.wsn_heygen_control set next_at=stamp+interval '2.5 seconds',last_device=o.device_code,dispatch_turn=(dispatch_turn+1)%5,
 last_paid_device=case when o.kind='book' then o.device_code else last_paid_device end,last_trial_device=case when o.kind='trial' then o.device_code else last_trial_device end where id;
 update public.wsn_book_orders set updated_at=stamp where id=o.id;
 return jsonb_build_object('orderId',o.id,'claim',o.claim_token,'kind',o.kind,'paid',o.paid_at is not null,'segment',s,'voice',o.payload->>'voice','token',t.token);
end;$$;
create or replace function public.wsn_heygen_next() returns jsonb language sql security invoker set search_path=pg_catalog,public as $$
 select public.wsn_heygen_next_v2(false);
$$;

create or replace function public.wsn_book_audio(p_order uuid,p_claim uuid,p_segment text,p_sha text)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare o public.wsn_book_orders; item jsonb;
begin
 select * into o from public.wsn_book_orders where id=p_order for update;
 if not found or o.claim_token is distinct from p_claim or o.state not in ('processing','ready')
 or p_sha is null or p_sha !~ '^[a-f0-9]{64}$'
 or not exists(select 1 from jsonb_array_elements(o.payload->'segments') where value->>'id'=p_segment) then raise exception 'Invalid audio claim';end if;
 if o.kind='book' and o.payload->>'revision'='pro-cloud-heygen-v1' and not public.wsn_heygen_is_funded(o.id) then raise exception 'Unpaid book';end if;
 select value into item from jsonb_array_elements(o.results) where value->>'id'=p_segment;
 if found then
  if item->>'sha256'<>p_sha then raise exception 'Audio conflict';end if;
 else
  o.results=o.results||jsonb_build_array(jsonb_build_object('id',p_segment,'sha256',p_sha,'path',o.id::text||'/'||p_segment||'.wav'));
 end if;
 update public.wsn_book_orders set results=o.results,state=case when jsonb_array_length(o.results)=jsonb_array_length(o.payload->'segments') then 'ready' else 'processing' end,updated_at=now() where id=o.id;
 return jsonb_build_object('done',jsonb_array_length(o.results),'total',jsonb_array_length(o.payload->'segments'));
end;$$;

revoke all on function public.wsn_heygen_pending_segments(uuid),public.wsn_heygen_is_funded(uuid),public.wsn_book_quote(text,text,jsonb,text,jsonb),public.wsn_heygen_next_v2(boolean) from public,anon,authenticated;
grant execute on function public.wsn_heygen_pending_segments(uuid),public.wsn_heygen_is_funded(uuid),public.wsn_book_quote(text,text,jsonb,text,jsonb),public.wsn_heygen_next_v2(boolean) to service_role;
notify pgrst, 'reload schema';
commit;
