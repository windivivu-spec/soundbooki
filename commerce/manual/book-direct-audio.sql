-- Additive delivery metadata; immutable snapshots, receipts and old audio stay intact.
begin;
create or replace function public.wsn_book_audio_direct(p_order uuid,p_claim uuid,p_segment text,p_sha text)
returns jsonb language plpgsql security invoker set search_path=pg_catalog,public as $$
declare progress jsonb;
begin
 if not exists(select 1 from public.wsn_heygen_tasks where order_id=p_order and segment_id=p_segment and state='audio' and audio_url like 'https://%') then raise exception 'Missing provider audio';end if;
 progress=public.wsn_book_audio(p_order,p_claim,p_segment,p_sha);
 update public.wsn_book_orders set results=(select jsonb_agg(case when item->>'id'=p_segment then (item-'path')||jsonb_build_object('delivery','provider') else item end order by ordinal) from jsonb_array_elements(results) with ordinality as r(item,ordinal)) where id=p_order;
 return progress;
end;$$;
revoke all on function public.wsn_book_audio_direct(uuid,uuid,text,text) from public,anon,authenticated;
grant execute on function public.wsn_book_audio_direct(uuid,uuid,text,text) to service_role;
notify pgrst, 'reload schema';
commit;
