#!/usr/bin/env bash
# One-command deploy of the Bote sa Bote tracker to YOUR Cloudflare account.
# Needs CLOUDFLARE_API_TOKEN with: Account > Cloudflare Pages: Edit, Account > D1: Edit.
# Safe to re-run: it reuses the existing D1 database and Pages project.
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="${CF_PROJECT:-bote-sa-bote}"
DB="${CF_DB:-bote-sa-bote-production}"
W="npx --yes wrangler"

[ -n "${CLOUDFLARE_API_TOKEN:-}" ] || { echo "Set CLOUDFLARE_API_TOKEN first"; exit 1; }
$W whoami | grep -iE "account|email" | head -3

ID=$($W d1 list --json 2>/dev/null | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const l=JSON.parse(s);const x=l.find(d=>d.name===process.argv[1]);process.stdout.write(x?x.uuid:"")})' "$DB")
if [ -z "$ID" ]; then
  echo "Creating D1 database $DB"
  $W d1 create "$DB" >/dev/null
  ID=$($W d1 list --json | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const l=JSON.parse(s);process.stdout.write(l.find(d=>d.name===process.argv[1]).uuid)})' "$DB")
fi
echo "D1 $DB = $ID"
node -e '
const fs=require("fs");let s=fs.readFileSync("wrangler.jsonc","utf8");
s=s.replace(/"database_id":\s*"[^"]*"/,`"database_id": "${process.argv[1]}"`).replace(/"database_name":\s*"[^"]*"/,`"database_name": "${process.argv[2]}"`).replace(/"name":\s*"[^"]*"/,`"name": "${process.argv[3]}"`);
fs.writeFileSync("wrangler.jsonc",s)' "$ID" "$DB" "$PROJECT"

$W d1 migrations apply "$DB" --remote
$W pages project create "$PROJECT" --production-branch main >/dev/null 2>&1 || echo "Pages project $PROJECT already exists"
npm run build
$W pages deploy dist --project-name "$PROJECT" --branch main --commit-dirty=true
URL="https://$PROJECT.pages.dev"
echo "Checking $URL"
for i in 1 2 3 4 5 6; do code=$(curl -s -o /dev/null -w "%{http_code}" "$URL/" || true); [ "$code" = 200 ] && break; sleep 10; done
echo "Home: $code"
echo
echo "Live at: $URL"
echo "Heisenbot: put this address in the dashboard > Capstone bottle > Site, then Test and Post link to chat."
