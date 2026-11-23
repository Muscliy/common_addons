import { build } from 'esbuild';
import { readFile, writeFile, mkdir, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const output = resolve(root, '../static/lib');
await mkdir(output, { recursive: true });
await build({
    absWorkingDir: root, entryPoints: ['src/index.jsx'],
    outfile: resolve(output, 'workflow_canvas.js'),
    bundle: true, format: 'iife', globalName: 'WorkflowCanvas',
    minify: true, target: ['es2020'], legalComments: 'eof',
    define: { 'process.env.NODE_ENV': '"production"' },
    banner: { js: '/* @odoo-module ignore */' },
});
const lock = JSON.parse(await readFile(resolve(root, 'package-lock.json'), 'utf8'));
const notices = [];
for (const [path, info] of Object.entries(lock.packages)) {
    if (!path || info.dev || info.optional) continue;
    const filename = (await readdir(resolve(root, path))).find((name) => /^licen[cs]e(\.|$)/i.test(name));
    // react-compiler-runtime's npm archive omits its repository-root MIT file.
    const licensePath = filename ? resolve(root, path, filename) :
        resolve(root, 'licenses', `${path.replace('node_modules/', '')}.LICENSE`);
    const license = await readFile(licensePath, 'utf8');
    notices.push(`${path.replace('node_modules/', '')}@${info.version}\n${license}`);
}
await writeFile(resolve(output, 'THIRD_PARTY_LICENSES.txt'), notices.join('\n\n-----\n\n'));
