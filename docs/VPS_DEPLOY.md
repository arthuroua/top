# VPS Deployment

This guide is for a production VPS setup with:

- `web` on `https://example.com`
- `api` on `https://api.example.com`
- internal-only `postgres`, `redis`, `ingestion-worker`, `copart-csv-scheduler`
- `nginx` as reverse proxy

## 1. Recommended server

- Provider: Hetzner
- Plan: `CPX31` or higher
- OS: Ubuntu `24.04`

## 2. Install Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin gettext apache2-utils openssl
```

## 3. Prepare the project

```bash
git clone https://github.com/arthuroua/top.git
cd top
cp .env.production.example .env.production
```

Edit `.env.production`:

- set strong `POSTGRES_PASSWORD`
- set strong `ADMIN_TOKEN`
- set strong `BASIC_AUTH_PASSWORD`
- set real `PUBLIC_WEB_DOMAIN`
- set real `PUBLIC_API_DOMAIN`
- set `NEXT_PUBLIC_SITE_URL`
- set `NEXT_PUBLIC_API_BASE_URL`
- set `COPART_CSV_AUTH_KEY`

## 4. Render nginx config and admin password

```bash
chmod +x deploy/scripts/render-nginx-config.sh deploy/scripts/generate-htpasswd.sh
./deploy/scripts/render-nginx-config.sh
./deploy/scripts/generate-htpasswd.sh
```

## 5. Get SSL certificates

You can get certificates with Certbot before the full stack is started, or use your preferred ACME flow.

Basic example with standalone certbot:

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d example.com -d api.example.com
sudo mkdir -p deploy/certs/live
sudo cp -r /etc/letsencrypt/live deploy/certs/
sudo cp -r /etc/letsencrypt/archive deploy/certs/
sudo cp /etc/letsencrypt/renewal/*.conf deploy/certs/ || true
```

## 6. Start production stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## 7. Validate

```bash
docker compose -f docker-compose.prod.yml ps
curl -I https://example.com
curl https://api.example.com/health
```

## 8. Internal security model

- Only `nginx` exposes ports `80/443`
- `web` and `api` are internal services behind reverse proxy
- `postgres` and `redis` are never exposed publicly
- `/admin/` is behind Basic Auth
- dangerous ingestion routes are behind Basic Auth and app-level `X-Admin-Token`

## 9. Recommended next hardening

- Add daily Postgres backup cron
- Add fail2ban or provider firewall rules
- Restrict SSH to your IP
- Add log shipping and uptime monitoring
- Rotate `ADMIN_TOKEN` and database credentials
