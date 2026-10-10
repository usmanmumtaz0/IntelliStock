# Signup, approval and initial accounts

## Implemented flow

The sign-in page now includes **New user? Sign up**. Registration requests email,
username, password and confirmation; no role selector is offered. Passwords must
contain 12–128 characters. Usernames allow 3–64 letters, numbers, dots, underscores
and hyphens. Emails are normalized to lowercase.

`POST /api/v1/auth/signup` creates a row in the existing `users` table with
`role=staff`, `is_active=false`, `signup_pending=true` and an Argon2id password hash.
It never issues a token. Role, activation and other extra fields are rejected.
Duplicate email/username attempts return the same generic acknowledgement and do
not reset an existing password or account. Validation responses omit input values.

Admins review requests in **Settings → User access** and use **Approve signup**.
The authenticated endpoint `POST /api/v1/users/{id}/approve` activates the account
as Staff and writes an audit record. Managers and staff cannot approve accounts.
Generic role editing cannot activate a pending request. Any later promotion is a
separate administrator action. Pending users are rejected by login and token
verification, even if their active flag is accidentally set.

There is no email verification or approval email delivery yet. Administrators must
verify the requester's identity out of band before approving. Disabled accounts
remain distinct from pending signups. Account rejection/deletion and password
reset are not part of this change.

Signup permits five requests per IP and per normalized email per hour using Redis.
Redis failure falls back to per-process limiting; production needs Redis and
appropriate edge abuse protection. Pending records have no automatic expiry.

## Database and credentials

Do not create a plaintext `credentials` table. The existing `users` table holds
unique email/username, role, activation, approval state and `hashed_password`.
The API never returns hashes. New migration `0006_signup_approval` adds the pending
flag with false for existing accounts; it does not activate disabled accounts.

On PostgreSQL, the migration enables users-table RLS and revokes its privileges
from Supabase `anon` and `authenticated` roles if present. The current backend
requires its trusted database-owner connection; a future restricted database role
requires a reviewed grant/RLS policy. Never put owner credentials in the frontend.
Before deploying to Supabase, also disable unused Data API exposure or separately
review permissions/RLS for all other application tables. This migration protects
the users table, not every older table in the project.

From `backend`, using the project virtual environment, once DATABASE_URL connects
to the dedicated IntelliStock database:

```powershell
python -m alembic upgrade head
python -m scripts.create_admin --email admin@intellistock.com --username admin
```

The admin command prompts privately for a new password and confirmation. It does
not overwrite existing identities. Use a fresh password, not one shared in chat.
Then sign in and create Manager/Staff accounts from Settings, or approve staff
signups. The earlier short passwords were not stored and remain below the minimum.
The staff email spelling must be confirmed before manual provisioning; the supplied
address had an extra `l` in the domain. No accounts have been provisioned by this
initial signup implementation because the direct Supabase host could not be reached.

Update (Oct 11, 2026): the supplied Session pooler connected successfully. Migrations
through 0006 were applied to the previously empty public schema, and
`admin@intellistock.com` was created. Its generated password is saved privately as
`INITIAL_ADMIN_PASSWORD` in the ignored root `.env`. Current-code login and session
verification passed against Supabase. Users-table RLS was verified enabled, with
SELECT denied for `anon` and `authenticated`. Manager/staff accounts have not been
created. The previously running backend still requires a restart with these settings.

Restart the current backend after migration. An already-running older backend will
not acquire signup endpoints without restarting; likewise refresh the frontend.
SQLite tests do not prove Supabase authentication, PostgreSQL locking, RLS or live
browser operation. Never run test fixture seeds against the real database.
