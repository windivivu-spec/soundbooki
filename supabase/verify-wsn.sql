-- All synthetic receipts below disappear at ROLLBACK.
begin;
set local role service_role;
do $$
declare result jsonb; expiry timestamptz; count_before bigint;
begin
  select count(*) into count_before from public.wsn_payments;
  result := public.wsn_accept_payment('qa-wsn-first', '0000000000', 'SNEEEEEEEEEEEE', 189000, now());
  if result->>'status' <> 'paid' then raise exception 'First payment failed'; end if;
  select expires_at into expiry from public.wsn_licenses where device_code='SNEEEEEEEEEEEE';
  result := public.wsn_accept_payment('qa-wsn-first', '0000000000', 'SNEEEEEEEEEEEE', 189000, now());
  if result->>'status' <> 'duplicate' then raise exception 'Duplicate failed'; end if;
  if (select expires_at from public.wsn_licenses where device_code='SNEEEEEEEEEEEE') <> expiry then raise exception 'Duplicate extended license'; end if;
  result := public.wsn_accept_payment('qa-wsn-second', '0000000000', 'SNEEEEEEEEEEEE', 189000, now());
  if (select expires_at from public.wsn_licenses where device_code='SNEEEEEEEEEEEE') <> expiry + interval '1 year' then raise exception 'Renewal failed'; end if;
  if (select count(*) from public.wsn_payments) <> count_before + 2 then raise exception 'Receipt count failed'; end if;
  begin
    perform public.wsn_accept_payment('qa-wrong-price', '0000000000', 'SNEEEEEEEEEEEE', 1, now());
    raise exception 'Expected invalid amount' using errcode='P0002';
  exception when invalid_parameter_value then null; end;
  begin
    perform public.wsn_accept_payment('qa-wsn-first', '0000000000', 'SNDDDDDDDDDDDD', 189000, now());
    raise exception 'Expected receipt conflict' using errcode='P0002';
  exception when invalid_parameter_value then null; end;
end;
$$;
rollback;
select 'passed' as receipt_duplicate_renewal_validation,
  (select count(*) from public.wsn_payments where bank_account='0000000000') as remaining_qa_receipts;
