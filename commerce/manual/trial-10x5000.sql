-- Local SQL draft, apply AFTER launch_combo_five_books; not applied live.
-- Preserves used trials, immutable historical orders and service-role-only grants.
begin;
alter table public.wsn_book_orders drop constraint wsn_book_orders_check;
alter table public.wsn_book_orders add constraint wsn_book_orders_check check(
 (kind='trial' and amount_vnd=0 and character_count<=5000 and funding_bundle_id is null)
 or (kind='book' and ((amount_vnd>=10000 and funding_bundle_id is null) or (amount_vnd=0 and funding_bundle_id is not null)))
 or (kind='bundle' and amount_vnd=50000 and character_count=1 and funding_bundle_id is null));
create or replace function public.wsn_book_create(p_device text,p_secret text,p_payload jsonb,p_kind text,p_request text)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.wsn_book_devices; o public.wsn_book_orders; s jsonb; items jsonb='[]';
 total integer=0; remaining integer=5000; snippet text; original_hash text; start_page integer; grant_row public.wsn_launch_bundles; slots integer; funded uuid;
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

commit;
