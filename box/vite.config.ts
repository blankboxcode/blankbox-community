import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';
export default defineConfig({root:fileURLToPath(new URL('.',import.meta.url)),plugins:[react()],define:{__BLANKBOX_COMMUNITY_BUILD__:'true'},resolve:{alias:{'@':fileURLToPath(new URL('..',import.meta.url))}},publicDir:false,build:{outDir:'web',emptyOutDir:true},css:{postcss:fileURLToPath(new URL('..',import.meta.url))}});
