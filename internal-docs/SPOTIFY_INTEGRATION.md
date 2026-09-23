# Spotify Integration (SPOTIFY_INTEGRATION.md)

- Date: 2026-09-23
- Status: owner runbook; local-only PKCE flow, no hosted callback.
- Scope: setup, refresh, troubleshooting, and security rules for `scripts/spotify_taste.py`.
- Related: `internal-docs/TASTE_PROFILE.md` section 2; hub `.env.example`.

## 1. Purpose

Feeds `naquuuu-curator`'s ground truth with real listening data — top artists/tracks, playlists, recently played — via a local snapshot. The snapshot is generated, not hand-curated; curator reads it at task time.

## 2. Architecture

`scripts/spotify_taste.py` runs a local OAuth PKCE flow (no client secret) against the Spotify Web API.

- Reads `SPOTIFY_CLIENT_ID` from the hub `.env`.
- Stores the refresh token in `.secrets/spotify_token.json` (git-ignored, Tier 1; agents never read it).
- `fetch` writes a sanitized snapshot to `internal-docs/SPOTIFY_SNAPSHOT.md` (contains no secrets).
- `naquuuu-curator` reads the snapshot at task time.
- Subcommands: `auth`, `fetch`, `status`; no args prints help.
- Requested scopes: `user-top-read user-read-recently-played playlist-read-private playlist-read-collaborative`.

## 3. One-time setup

0. Confirm the account has an active Spotify Premium subscription. Since February 2026, Development Mode apps require the app owner to have active Premium; if it lapses, the app stops working until resubscribed.
1. Create an app at developer.spotify.com/dashboard. Add redirect URI exactly `http://127.0.0.1:8080/callback` and select Web API.
2. Add `SPOTIFY_CLIENT_ID` to the hub `.env` in your editor — never paste it into chat.
3. Run `python scripts/spotify_taste.py auth` and approve in the browser.
4. Run `python scripts/spotify_taste.py fetch` and confirm `internal-docs/SPOTIFY_SNAPSHOT.md` exists.

## 4. Refreshing

- Re-run `python scripts/spotify_taste.py fetch` any time; the snapshot is overwritten.
- `python scripts/spotify_taste.py status` shows auth state.

## 5. Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `redirect_uri` mismatch | registered URI differs from the one sent | register exactly `http://127.0.0.1:8080/callback`; include the port |
| 403 | Premium inactive, or Development Mode restriction | confirm the app owner's Premium subscription is active |
| token expired | cached token no longer valid | re-run `python scripts/spotify_taste.py auth` |
| port 8080 busy | local listener conflict | re-run `auth` with `--port <n>`, then re-register the redirect URI with the matching port — the registered URI must match exactly |

## 6. Security rules

- `.env` and `.secrets/` are Tier 1 and out of bounds for agent reads.
- Never paste secrets (client ID, tokens) into chat.
- The snapshot is secret-free by construction and safe for agent consumption.
- Run `python scripts/verify_sanitization.py` before any commit.
