-- Owner-authorized cloud trial activation. Apply after trial-five-unit-policy.sql.
-- No paid activation, no local runtime changes, no rewriting old order snapshots.
begin;
create table public.wsn_heygen_control (
 id boolean primary key default true check(id),next_at timestamptz not null default now(),blocked_until timestamptz not null default now(),last_device text
);
insert into public.wsn_heygen_control(id) values(true);
create table public.wsn_heygen_tasks (
 order_id uuid not null references public.wsn_book_orders(id),segment_id text not null,
 token uuid not null default gen_random_uuid(),state text not null check(state in ('sending','audio','retry','done','uncertain','failed')),
 attempt integer not null default 1,started_at timestamptz not null default now(),available_at timestamptz not null default now(),
 audio_url text,diagnostic text,primary key(order_id,segment_id)
);
alter table public.wsn_heygen_control enable row level security;
alter table public.wsn_heygen_tasks enable row level security;
revoke all on public.wsn_heygen_control,public.wsn_heygen_tasks from public,anon,authenticated;
grant select,insert,update on public.wsn_heygen_control,public.wsn_heygen_tasks to service_role;
create function public.wsn_heygen_next() returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare c public.wsn_heygen_control;o public.wsn_book_orders;t public.wsn_heygen_tasks;s jsonb;
begin
 select * into c from public.wsn_heygen_control where id for update;
 -- Never automatically duplicate a POST whose outcome became unknown.
 update public.wsn_heygen_tasks set state='uncertain',diagnostic='Worker interrupted after dispatch; reconcile before retry' where state='sending' and started_at<now()-interval '150 seconds';
 update public.wsn_book_orders b set state='failed',updated_at=now() where b.state='processing' and exists(select 1 from public.wsn_heygen_tasks q where q.order_id=b.id and q.state in ('uncertain','failed'));
 -- Download/commit retries reuse the saved provider URL without another TTS POST.
 select * into t from public.wsn_heygen_tasks where state='audio' and available_at<=now() order by available_at for update skip locked limit 1;
 if found then
  update public.wsn_heygen_tasks set available_at=now()+interval '120 seconds' where order_id=t.order_id and segment_id=t.segment_id;
  select * into o from public.wsn_book_orders where id=t.order_id;
  select value into s from jsonb_array_elements(o.payload->'segments') where value->>'id'=t.segment_id;
  return jsonb_build_object('orderId',o.id,'claim',o.claim_token,'segment',s,'voice',o.payload->>'voice','token',t.token,'audioURL',t.audio_url);
 end if;
 if c.next_at>now() or c.blocked_until>now() or (select count(*) from public.wsn_heygen_tasks where state='sending')>=3 then return null;end if;
 -- Round robin between devices, then oldest eligible order. Only explicit trials.
 select b.* into o from public.wsn_book_orders b where b.kind='trial' and b.state in ('queued','processing') and b.payload->>'revision'='pro-cloud-heygen-v1'
 and exists(select 1 from jsonb_array_elements(b.payload->'segments') p where not exists(select 1 from public.wsn_heygen_tasks q where q.order_id=b.id and q.segment_id=p->>'id' and (q.state<>'retry' or q.available_at>now())))
 order by (b.device_code is not distinct from c.last_device),b.updated_at,b.created_at for update skip locked limit 1;
 if not found then return null;end if;
 select p into s from jsonb_array_elements(o.payload->'segments') p where not exists(select 1 from public.wsn_heygen_tasks q where q.order_id=o.id and q.segment_id=p->>'id' and (q.state<>'retry' or q.available_at>now())) order by (p->>'index')::int limit 1;
 if o.state='queued' then update public.wsn_book_orders set state='processing',claim_token=gen_random_uuid(),updated_at=now() where id=o.id returning * into o;end if;
 insert into public.wsn_heygen_tasks(order_id,segment_id,state) values(o.id,s->>'id','sending') on conflict(order_id,segment_id) do update set state='sending',token=gen_random_uuid(),attempt=wsn_heygen_tasks.attempt+1,started_at=now() returning * into t;
 update public.wsn_heygen_control set next_at=now()+interval '2.5 seconds',last_device=o.device_code where id;
 update public.wsn_book_orders set updated_at=now() where id=o.id;
 return jsonb_build_object('orderId',o.id,'claim',o.claim_token,'segment',s,'voice',o.payload->>'voice','token',t.token);
end;$$;
create function public.wsn_heygen_result(p_order uuid,p_segment text,p_token uuid,p_state text,p_url text default null,p_retry integer default 30,p_diagnostic text default null) returns void language plpgsql security invoker set search_path=pg_catalog,public as $$
declare t public.wsn_heygen_tasks;
begin
 select * into t from public.wsn_heygen_tasks where order_id=p_order and segment_id=p_segment for update;
 if not found or t.token<>p_token or t.state not in ('sending','audio') then raise exception 'Invalid dispatcher claim';end if;
 if p_state not in ('audio','done','retry','uncertain','failed') then raise exception 'Invalid dispatcher state';end if;
 if p_state='audio' and (p_url is null or p_url !~ '^https://') then raise exception 'Invalid audio URL';end if;
 if p_state='done' and not exists(select 1 from wsn_book_orders b,jsonb_array_elements(b.results) r where b.id=p_order and r->>'id'=p_segment) then raise exception 'Audio not committed';end if;
 if p_state='retry' and t.attempt>=4 then p_state='failed';end if;
 update public.wsn_heygen_tasks set state=p_state,audio_url=coalesce(p_url,audio_url),available_at=now()+make_interval(secs=>greatest(3,least(p_retry,600))),diagnostic=left(p_diagnostic,200) where order_id=p_order and segment_id=p_segment;
 if p_state='retry' then update public.wsn_heygen_control set blocked_until=greatest(blocked_until,now()+make_interval(secs=>greatest(3,least(p_retry,600)))) where id;end if;
 if p_state in ('failed','uncertain') then update public.wsn_book_orders set state='failed',updated_at=now() where id=p_order;end if;
end;$$;
revoke all on function public.wsn_heygen_next(),public.wsn_heygen_result(uuid,text,uuid,text,text,integer,text) from public,anon,authenticated;
grant execute on function public.wsn_heygen_next(),public.wsn_heygen_result(uuid,text,uuid,text,text,integer,text) to service_role;
-- Existing Modal workers must never claim a new HeyGen snapshot.
create or replace function public.wsn_book_claim(p_order uuid default null) returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare o public.wsn_book_orders;
begin
 select * into o from public.wsn_book_orders where state='queued' and payload->>'revision'='pro-cloud-modal-v1' and (p_order is null or id=p_order) order by created_at for update skip locked limit 1;
 if not found then return null;end if;
 if o.kind='book' and o.paid_at is null then raise exception 'Unpaid book';end if;
 update public.wsn_book_orders set state='processing',claim_token=gen_random_uuid(),updated_at=now() where id=o.id returning * into o;
 return to_jsonb(o);
end;$$;
commit;
