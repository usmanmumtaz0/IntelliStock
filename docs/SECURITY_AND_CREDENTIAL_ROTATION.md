# Security Operations and Credential Rotation

## Initial administrator

The API does not create users at startup and contains no fixed login account. After applying migrations, create the first administrator from the backend directory:

```bash
python -m scripts.create_admin --email you@example.com --username admin
```

The command prompts without echoing the password, requires at least 12 characters, stores an Argon2id hash, and never prints the password. For non-interactive provisioning, provide `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_USERNAME`, and `INITIAL_ADMIN_PASSWORD` through the deployment secret manager only for the duration of the command, then remove them.

## Rotate the PostgreSQL password

Credential rotation changes external state. Back up the database and coordinate a maintenance window before performing these steps.

For the Docker Compose deployment with an existing persistent volume:

1. Generate a new random password in an approved password manager. Do not put it in shell history or chat.
2. Open an interactive PostgreSQL session:

   ```bash
   docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
   ```

3. At the `psql` prompt, run `\password intellistock` (replace `intellistock` if `POSTGRES_USER` is different). Enter the new password twice. `\password` avoids placing it in SQL history.
4. URL-encode any reserved characters and update both `POSTGRES_PASSWORD` and `DATABASE_URL_DOCKER` in the untracked deployment `.env`. Update `DATABASE_URL` as well for host-based development.
5. Restart only the services that consume the connection string:

   ```bash
   docker compose up -d --force-recreate backend
   ```

6. Verify `/health`, an authenticated inventory query, and application logs. Do not print connection strings.
7. After successful verification, terminate obsolete database sessions if policy requires it:

   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE usename = 'intellistock' AND pid <> pg_backend_pid();
   ```

Changing `POSTGRES_PASSWORD` in Compose alone does not update a role inside an existing PostgreSQL volume; the `\password` step is required.

For a managed PostgreSQL service, rotate the application role through the provider's secret/role workflow, update the deployment secret and connection pool, roll the backend, verify, and revoke the previous credential according to provider guidance.

## Rotate the JWT signing secret

Generate at least 32 cryptographically random characters, update `JWT_SECRET` in the deployment secret manager, and restart every API worker together. Existing access tokens become invalid immediately, so schedule this as a forced sign-in event. Never use the placeholder from `.env.example`.

## Git history cleanup

The current source tree uses placeholders. A local all-revisions scan confirmed that earlier Git revisions contain credential-like values. Treat those credentials as exposed and rotate them before history cleanup because rewriting history does not invalidate a leaked secret.

If a private scan confirms a historical secret:

1. Rotate/revoke it first.
2. Coordinate with every contributor and protect a backup outside the rewritten repository.
3. Use `git filter-repo` with a reviewed replacement map or path filter.
4. Force-push the rewritten protected branches and tags only after team approval.
5. Require all contributors and deployments to fresh-clone; delete stale forks/caches where possible.
6. Re-run secret scanning across all refs.

Do not rewrite shared history as part of an ordinary application deployment.

## Public endpoint rationale

- `/health` and `/api/v1/health` are public for load balancers and container health checks and expose only component availability.
- `/api/v1/auth/login` is public because it issues credentials; it is protected by Redis-backed IP and normalized-account rate limits.
- OpenAPI documentation is public in the application process for development. Restrict `/docs`, `/redoc`, and `/openapi.json` at the production reverse proxy if required.
- All other REST endpoints and `/ws/inventory` require an active database user. Detailed audit and health endpoints additionally require the admin role.
