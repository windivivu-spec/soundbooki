import {worker} from '../_shared/heygen-worker.ts';
Deno.serve(request=>worker(request,name=>Deno.env.get(name)));
