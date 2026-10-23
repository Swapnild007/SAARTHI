const {execFileSync}=require('node:child_process');const fs=require('node:fs');
for(const name of ['scripts/app.js','scripts/boot.js','scripts/workspace.js','scripts/utilities.js','scripts/native-config.js','scripts/native-runtime.js','scripts/voice.js','scripts/automation.js','appforge/app.js','sw.js'])execFileSync(process.execPath,['--check',name],{stdio:'inherit'});
execFileSync(process.env.PYTHON||'python',['-m','compileall','-q','backend','app.py'],{stdio:'inherit'});
for(const name of ['index.html','appforge/index.html','styles/app.css','styles/workspace.css','assets/icon-192.png','assets/icon-512.png'])if(!fs.statSync(name).size)throw Error('Missing release asset: '+name);
const manifest=JSON.parse(fs.readFileSync('manifest.webmanifest','utf8'));if(manifest.display!=='standalone')throw Error('Invalid manifest');
console.log('PASS: static production assets, manifest, all JS syntax and Python compilation. No bundler is required by this FastAPI/static application.');
