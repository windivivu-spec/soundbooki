import { books } from '../_shared/books.ts';
Deno.serve(request=>books(request,name=>Deno.env.get(name)));
