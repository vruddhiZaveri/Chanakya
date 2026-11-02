import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const proxy = {'/api': {target:'http://127.0.0.1:8000',changeOrigin:true,timeout:180000,proxyTimeout:180000}};
export default defineConfig({ plugins:[react()],server:{host:'127.0.0.1',port:5174,strictPort:true,allowedHosts:['terminal.local'],proxy},preview:{host:'127.0.0.1',port:5174,strictPort:true,proxy} });
