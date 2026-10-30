import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url));
const result=spawnSync(root+'.runtime/bin/python',[root+'commerce/books-admin.py',...process.argv.slice(2)],{cwd:root,stdio:'inherit',env:process.env});
process.exit(result.status??1);
