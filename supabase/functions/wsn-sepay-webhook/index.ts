import { webhook } from '../_shared/wsn.ts';
Deno.serve(request => webhook(request, name => Deno.env.get(name)));
