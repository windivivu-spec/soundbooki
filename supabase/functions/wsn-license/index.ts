import { license } from '../_shared/wsn.ts';
Deno.serve(request => license(request, name => Deno.env.get(name)));
