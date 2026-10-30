// Optional vendor rebuild. The normal macOS build uses the checked-in bundle.
// Usage: node scripts/build_flipbook.cjs /absolute/path/to/esbuild
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const esbuild=require(process.argv[2]||'esbuild');
const root=path.resolve(__dirname,'../ui/vendor/gul-flipbook');
const output=esbuild.buildSync({entryPoints:[path.join(root,'source/index.ts')],bundle:true,format:'iife',globalName:'GulFlipbook',target:'safari18',minify:true,write:false,legalComments:'none'}).outputFiles[0].text;
const notice='/* @gullabs/flipbook-core 3.2.2, MPL-2.0. Source: ./source/. Notices: ../../../licenses/GulLabs-Flipbook/. */\n';
fs.writeFileSync(path.join(root,'flipbook.js'),notice+output);
const context={};vm.runInNewContext(output,context);
fs.writeFileSync(path.join(root,'flipbook.css'),notice+context.GulFlipbook.FLIPBOOK_CSS+'\n');
