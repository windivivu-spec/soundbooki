begin;
do $$
declare payload jsonb; o jsonb; other jsonb; trial jsonb; claim jsonb; rejected boolean; n integer;
begin
 if public.wsn_book_price(500)<>10000 or public.wsn_book_price(27000)<>10000 or public.wsn_book_price(27001)<>25000
 or public.wsn_book_price(54000)<>25000 or public.wsn_book_price(54001)<>40000 or public.wsn_book_price(108001)<>50000
 or public.wsn_book_price(216000)<>60000 then raise exception 'Price boundary failure';end if;
 select jsonb_build_object('title','QA book','voice','voice-003','language','vi','revision','pro-cloud-modal-v1','openingPage',0,
  'segments',jsonb_agg(jsonb_build_object('id',md5('segment'||i),'index',i,'page',0,'text',repeat('á',1000)) order by i))
 into payload from generate_series(1,40) i;
 o=public.wsn_book_create('SNFAFAFAFAFAFA',repeat('a',64),payload,'book',repeat('a',32));
 if (o->>'amount_vnd')::integer<>25000 or o->>'state'<>'awaiting_payment' then raise exception 'Quote failure';end if;
 if public.wsn_book_create('SNFAFAFAFAFAFA',repeat('a',64),payload,'book',repeat('b',32))->>'id'<>o->>'id' then raise exception 'Duplicate order';end if;
 rejected=false;begin
  perform public.wsn_book_create('SNFAFAFAFAFAFA',repeat('b',64),payload,'book',repeat('a',32));
 exception when others then rejected=true;end;if not rejected then raise exception 'Device hijack';end if;
 rejected=false;begin update public.wsn_book_orders set character_count=216000 where id=(o->>'id')::uuid;
 exception when others then rejected=true;end;if not rejected then raise exception 'Mutable quote';end if;
 if public.wsn_book_claim((o->>'id')::uuid) is not null then raise exception 'Unpaid job claimed';end if;
 rejected=false;begin perform public.wsn_book_confirm(o->>'payment_code','qa-book-tx','0000000000','0000000000',10000,now());
 exception when others then rejected=true;end;if not rejected then raise exception 'Underpayment accepted';end if;
 perform public.wsn_book_confirm(o->>'payment_code','qa-book-tx','0000000000','0000000000',25000,now());
 if public.wsn_book_confirm(o->>'payment_code','qa-book-tx','0000000000','0000000000',25000,now())->>'status'<>'duplicate' then raise exception 'Receipt replay';end if;
 claim=public.wsn_book_claim((o->>'id')::uuid);
 if claim->>'state'<>'processing' then raise exception 'Paid claim failure';end if;
 if public.wsn_book_claim((o->>'id')::uuid) is not null then raise exception 'Double claim';end if;
 rejected=false;begin perform public.wsn_book_audio((o->>'id')::uuid,gen_random_uuid(),md5('segment1'),repeat('c',64));
 exception when others then rejected=true;end;if not rejected then raise exception 'Audio without claim accepted';end if;
 perform public.wsn_book_audio((o->>'id')::uuid,(claim->>'claim_token')::uuid,md5('segment1'),repeat('c',64));
 if (public.wsn_book_audio((o->>'id')::uuid,(claim->>'claim_token')::uuid,md5('segment1'),repeat('c',64))->>'done')::integer<>1 then raise exception 'Audio recorded twice';end if;
 rejected=false;begin perform public.wsn_book_audio((o->>'id')::uuid,(claim->>'claim_token')::uuid,md5('segment1'),repeat('d',64));
 exception when others then rejected=true;end;if not rejected then raise exception 'Audio content conflict';end if;
 rejected=false;begin perform public.wsn_accept_payment('qa-book-tx','0000000000','SNFAFAFAFAFAFA',189000,now());
 exception when others then rejected=true;end;if not rejected then raise exception 'Receipt reused for annual license';end if;

 for n in 1..10 loop
  trial=public.wsn_book_create('SNFAFAFAFAFAFA',repeat('a',64),payload,'trial',md5('trial'||n));
  if (trial->>'character_count')::integer<>4000 then raise exception 'Trial size';end if;
 end loop;
 rejected=false;begin perform public.wsn_book_create('SNFAFAFAFAFAFA',repeat('a',64),payload,'trial',md5('trial11'));
 exception when others then rejected=true;end;if not rejected then raise exception 'Unlimited trials';end if;
 if public.wsn_book_create('SNFAFAFAFAFAFA',repeat('a',64),payload,'trial',md5('trial10'))->>'id'<>trial->>'id' then raise exception 'Trial retry';end if;
 other=public.wsn_book_create('SNFBFBFBFBFBFB',repeat('b',64),payload,'book',repeat('a',32));
 if other->>'id'=o->>'id' or other->>'payment_code'=o->>'payment_code' then raise exception 'Cross-device collision';end if;
 rejected=false;begin perform public.wsn_book_confirm(other->>'payment_code','qa-book-tx','0000000000','0000000000',25000,now());
 exception when others then rejected=true;end;if not rejected then raise exception 'Receipt reused on another Mac';end if;
 -- Actual 4-hour input is stored and charged independently of a 25k order.
 select jsonb_build_object('title','QA long','voice','voice-003','language','vi','revision','pro-cloud-modal-v1','openingPage',0,
 'segments',jsonb_agg(jsonb_build_object('id',md5('long'||i),'index',i,'page',0,'text',repeat('a',1000)) order by i)) into payload from generate_series(1,216) i;
 other=public.wsn_book_create('SNFAFAFAFAFAFA',repeat('a',64),payload,'book',md5('long'));
 if (other->>'amount_vnd')::integer<>60000 then raise exception 'Long book underpriced';end if;
 rejected=false;begin perform public.wsn_book_confirm(other->>'payment_code','qa-long-tx','0000000000','0000000000',25000,now());
 exception when others then rejected=true;end;if not rejected then raise exception '25k unlocked 4-hour book';end if;
end;$$;
select 'PASS: price boundaries, snapshot immutability, paid claims, exact receipts, replay, cross-device isolation and 10x4000 trial quota' as result;
rollback;
