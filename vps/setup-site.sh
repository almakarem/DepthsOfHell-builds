#!/usr/bin/env bash
# Sets up Apache on the VPS for the Depths of Hell domain: the website at
# the root, game updates under /updates/, HTTPS from Let's Encrypt.
#   sudo bash setup-site.sh depthsofhell.com
# Run it after the domain's DNS A records (@, www, play) point at this VPS.
# Only adds its own site (depthsofhell.conf); the other sites are untouched.
set -euo pipefail
DOMAIN="${1:?usage: sudo bash setup-site.sh <domain>}"
ROOT=/var/www/depthsofhell
mkdir -p "$ROOT/site" "$ROOT/updates"
[ -f "$ROOT/site/index.html" ] || printf '<!doctype html><meta charset="utf-8"><title>Depths of Hell</title><h1>Depths of Hell</h1><p>Coming soon.</p>\n' > "$ROOT/site/index.html"
chmod -R a+rX "$ROOT"
cat > /etc/apache2/sites-available/depthsofhell.conf <<CONF
<VirtualHost *:80>
    ServerName $DOMAIN
    ServerAlias www.$DOMAIN
    DocumentRoot $ROOT/site
    <Directory $ROOT/site>
        Options -Indexes +FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    # Game updates: latest.json is never cached; half-uploaded files are hidden.
    Alias /updates/ $ROOT/updates/
    <Directory $ROOT/updates>
        Options -Indexes
        AllowOverride None
        Require all granted
        <FilesMatch "\.part\$">
            Require all denied
        </FilesMatch>
        <Files "latest.json">
            Header set Cache-Control "no-cache"
        </Files>
    </Directory>
    AddType application/octet-stream .pck .patch
    AddType application/json .json

    ErrorLog \${APACHE_LOG_DIR}/depthsofhell-error.log
    CustomLog \${APACHE_LOG_DIR}/depthsofhell-access.log combined
</VirtualHost>
CONF
a2enmod headers >/dev/null
a2ensite depthsofhell >/dev/null
apache2ctl configtest
systemctl reload apache2
WWW=""
getent hosts "www.$DOMAIN" >/dev/null && WWW="-d www.$DOMAIN"
certbot --apache --non-interactive --agree-tos --register-unsafely-without-email --redirect -d "$DOMAIN" $WWW
echo
echo "Done: https://$DOMAIN/ (site) and https://$DOMAIN/updates/latest.json (updates)."
