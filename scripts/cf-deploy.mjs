#!/usr/bin/env node
/**
 * cf-deploy.mjs - config-only live `wrangler deploy` for the CF Worker+Container.
 *
 * The committed wrangler.jsonc keeps the container image ref with a
 * `<YOUR_ACCOUNT_ID>` placeholder (CF Containers pull only from
 * registry.cloudflare.com/<account>/...; the real account id is not committed).
 * wrangler deploy needs the real id, so this script substitutes it into a temp
 * config and deploys from that, leaving the committed file untouched.
 *
 * It ships the cost config that lives in wrangler.jsonc (instance_type,
 * max_instances) plus the current worker bundle (e.g. sleepAfter) and reuses the
 * already-pushed container image tag named in wrangler.jsonc - it does NOT build
 * or push an image. For a full build+push+deploy+canary+rollback flow use
 * scripts/deploy_cf.py instead.
 *
 * Required env:
 *   CLOUDFLARE_API_TOKEN    - CF API token (full-access dev token works)
 *   CLOUDFLARE_ACCOUNT_ID   - substituted for <YOUR_ACCOUNT_ID> in the image ref
 *   PUBLIC_URL              - substituted for <YOUR_PUBLIC_URL>; its host also
 *                             fills the <YOUR_WORKER_DOMAIN> custom-domain route
 *
 * Optional env:
 *   TELEGRAM_KV_NAMESPACE_ID - substituted for <telegram-kv-namespace-id>; if a
 *                              real KV id is already in wrangler.jsonc this is a
 *                              no-op. Required when the committed file still has
 *                              the placeholder (deploy fails otherwise).
 *
 * Usage:
 *   export CLOUDFLARE_API_TOKEN=...
 *   export CLOUDFLARE_ACCOUNT_ID=...
 *   npm run cf:deploy            # deploy
 *   npm run cf:deploy -- --dry-run   # render temp config + wrangler --dry-run only
 */

import { readFileSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const srcConfig = join(repoRoot, "wrangler.jsonc");
const dryRun = process.argv.includes("--dry-run");

const accountId = process.env.CLOUDFLARE_ACCOUNT_ID;
if (!process.env.CLOUDFLARE_API_TOKEN) {
    console.error("CLOUDFLARE_API_TOKEN is required (CF API token).");
    process.exit(1);
}
if (!accountId) {
    console.error(
        "CLOUDFLARE_ACCOUNT_ID is required (substituted for <YOUR_ACCOUNT_ID>)."
    );
    process.exit(1);
}

const publicUrl = process.env.PUBLIC_URL;
if (!publicUrl) {
    console.error("PUBLIC_URL is required (substituted for <YOUR_PUBLIC_URL>).");
    process.exit(1);
}
// The Worker custom-domain route is always the PUBLIC_URL host, so derive it
// instead of taking a second env var (keeps the route in sync with PUBLIC_URL).
let workerDomain;
try {
    workerDomain = new URL(publicUrl).host;
} catch {
    console.error(`PUBLIC_URL is not a valid URL: ${publicUrl}`);
    process.exit(1);
}

let config = readFileSync(srcConfig, "utf8");
config = config.replaceAll("<YOUR_ACCOUNT_ID>", accountId);
config = config.replaceAll("<YOUR_PUBLIC_URL>", publicUrl);
config = config.replaceAll("<YOUR_WORKER_DOMAIN>", workerDomain);

const kvId = process.env.TELEGRAM_KV_NAMESPACE_ID;
if (kvId) {
    config = config.replaceAll("<telegram-kv-namespace-id>", kvId);
}
if (config.includes("<telegram-kv-namespace-id>")) {
    console.error(
        "wrangler.jsonc still has <telegram-kv-namespace-id>; set " +
            "TELEGRAM_KV_NAMESPACE_ID to the real KV namespace id before deploying."
    );
    process.exit(1);
}

// Write the temp config in the repo root, not the OS temp dir: wrangler resolves
// `main` (src/worker.ts) and outdir relative to the --config file's directory, so
// the substituted config must sit next to src/. The name is gitignored.
const tmpConfig = join(repoRoot, "wrangler.cf-deploy.tmp.jsonc");
writeFileSync(tmpConfig, config);

const args = ["wrangler", "deploy", "--config", tmpConfig];
if (dryRun) {
    args.push("--dry-run", "--outdir", join(repoRoot, ".wrangler-dryrun"));
}
console.log(`Deploying with substituted config: ${tmpConfig}`);
console.log(`  $ npx ${args.join(" ")}`);

const res = spawnSync("npx", args, {
    cwd: repoRoot,
    stdio: "inherit",
    shell: process.platform === "win32",
});

try {
    rmSync(tmpConfig, { force: true });
} catch {
    // best-effort cleanup of the temp config
}

process.exit(res.status ?? 1);
