#!/usr/bin/env node
/** Build the browser client and its local assets. */
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const root=path.resolve(import.meta.dirname,'..');
const result=spawnSync(process.execPath,[path.join(root,'node_modules/vite/bin/vite.js'),'build','--config','box/vite.config.ts'],{cwd:root,stdio:'inherit'});
if(result.status!==0)process.exit(result.status||1);
const web=path.join(root,'box/web');
for(const name of ['favicon.svg','manifest.webmanifest'])fs.copyFileSync(path.join(root,'public',name),path.join(web,name));
fs.cpSync(path.join(root,'public/brand'),path.join(web,'brand'),{recursive:true});
fs.mkdirSync(path.join(web,'downloads'),{recursive:true});
fs.copyFileSync(path.join(root,'LICENSE'),path.join(web,'downloads/LICENSE'));
for(const name of fs.readdirSync(root))if(name.endsWith('.md'))fs.copyFileSync(path.join(root,name),path.join(web,'downloads',name));
if(fs.existsSync(path.join(root,'guides')))fs.cpSync(path.join(root,'guides'),path.join(web,'downloads/guides'),{recursive:true});
fs.writeFileSync(path.join(web,'credits.html'),'<!doctype html><html lang="en"><meta charset="utf-8"><title>Blank Box credits</title><h1>Blank Box credits</h1><p>Third-party notices are included with this distribution.</p><a href="/downloads/THIRD-PARTY-NOTICES.md">Read notices</a></html>');
