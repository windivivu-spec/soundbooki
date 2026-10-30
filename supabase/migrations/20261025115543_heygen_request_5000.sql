-- Change only validation for NEW explicitly packed HeyGen snapshots.
-- Keep immutable orders, trial accounting, payments, grants and dispatcher.
begin;
do $$
declare definition text; old_check text = 'length(s->>''text'') not between 1 and 2000';
 new_check text = 'length(s->>''text'') not between 1 and (case when p_payload->>''revision''=''pro-cloud-heygen-v1'' and p_payload->>''chunkingVersion''=''heygen-5000-v1'' then 5000 else 2000 end)';
begin
 select pg_get_functiondef('public.wsn_book_create(text,text,jsonb,text,text)'::regprocedure) into definition;
 if position(new_check in definition)>0 then return;end if;
 if position(old_check in definition)=0 or position('trials_used+debit' in definition)=0
 then raise exception 'Unexpected book creation contract; inspect before changing';end if;
 execute replace(definition,old_check,new_check);
end;$$;
commit;
