-- LOCAL PREPARATION ONLY. Apply together with the updated books gateway.
-- Does not activate HeyGen, paid services, or reset previously consumed trials.
begin;
alter table public.wsn_book_devices drop constraint wsn_book_devices_trials_used_check;
alter table public.wsn_book_devices add constraint wsn_book_devices_trials_used_check
 check(trials_used between 0 and 10);
alter table public.wsn_book_orders drop constraint wsn_book_orders_check;
alter table public.wsn_book_orders add constraint wsn_book_orders_check
 check((kind='trial' and amount_vnd=0 and character_count<=4000)
    or (kind='book' and amount_vnd>=10000));
create or replace function public.wsn_book_create(p_device text,p_secret text,p_payload jsonb,p_kind text,p_request text)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.wsn_book_devices; o public.wsn_book_orders; s jsonb; items jsonb='[]';
 total integer=0; remaining integer=4000; snippet text; original_hash text; start_page integer;
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
  if d.trials_used>=10 then raise exception 'Trial limit reached';end if;
  update public.wsn_book_devices set trials_used=trials_used+1 where device_code=p_device;
 end if;
 insert into public.wsn_book_orders(device_code,request_key,kind,content_hash,payload,character_count,amount_vnd,state)
 values(p_device,p_request,p_kind,original_hash,p_payload,total,case when p_kind='trial' then 0 else public.wsn_book_price(total) end,
 case when p_kind='trial' then 'queued' else 'awaiting_payment' end) returning * into o;
 return to_jsonb(o)-'claim_token';
end;$$;
-- CREATE OR REPLACE preserves the existing service-role-only grants.
commit;
