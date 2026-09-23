#!/usr/bin/env python3
r"""
Spotify Taste Snapshot (spotify_taste.py)

Usage:
  python scripts/spotify_taste.py auth [--port 8080]
  python scripts/spotify_taste.py fetch
  python scripts/spotify_taste.py status

One-time Authorization Code + PKCE browser flow (public client: no client
secret is ever stored, sent, or printed), followed by read-only Spotify Web API
calls for the owner's top artists/tracks, playlists, and recently played
tracks. The result is written to a sanitized Markdown snapshot at
internal-docs/SPOTIFY_SNAPSHOT.md (UTF-8, LF) with no tokens, client IDs, or
account identifiers.

Subcommands:
  auth    Open the browser consent page, capture the code on
          127.0.0.1:<port>/callback, verify the OAuth state, exchange the code
          for tokens, and cache them at .secrets/spotify_token.json.
  fetch   Call the Spotify Web API and overwrite the snapshot.
  status  Report auth state (masked client-id hint only; never prints secrets).

Spotify 2026 API notes honored here:
  - No batch endpoints: each time range is fetched one call at a time.
  - Artist popularity/followers and track popularity are no longer returned.
  - Playlists expose playlist.items.total; entries live under items.
  - Playlist entries are only returned for playlists the user owns or
    collaborates on, so followed playlists may report 0 items.
  - Dev Mode apps require the app owner to have Spotify Premium; a 403 is
    reported with that hint instead of a raw error.

Exit codes: 0 = success, 1 = failure.
"""

import argparse
import base64
import errno
import hashlib
import html
import http.server
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn

# Windows console UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass

AUTHORIZE_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"
SCOPES = (
    "user-top-read user-read-recently-played "
    "playlist-read-private playlist-read-collaborative"
)

DEFAULT_PORT = 8080
AUTH_TIMEOUT_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 30
REFRESH_SKEW_SECONDS = 60
TOP_LIMIT = 20
PLAYLIST_LIMIT = 50
RECENT_LIMIT = 50
RECENT_UNIQUE_LIMIT = 20

TIME_RANGES = ("short_term", "medium_term", "long_term")
TIME_RANGE_LABELS = {
    "short_term": "Short term (~4 weeks)",
    "medium_term": "Medium term (~6 months)",
    "long_term": "Long term (years)",
}

SNAPSHOT_RELATIVE_PATH = Path("internal-docs") / "SPOTIFY_SNAPSHOT.md"
TOKEN_RELATIVE_PATH = Path(".secrets") / "spotify_token.json"


class TasteError(Exception):
    """Expected, user-facing failure: printed as a single line, never a traceback."""


class HttpError(TasteError):
    """HTTP response with a non-2xx status code."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Workspace paths and the .env client-id lookup
# ---------------------------------------------------------------------------


def workspace_root() -> Path:
    """Resolve the hub root from NAQUUUU_WORKSPACE, else two levels above this file."""
    override = os.environ.get("NAQUUUU_WORKSPACE", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parent.parent


def token_path() -> Path:
    return workspace_root() / TOKEN_RELATIVE_PATH


def snapshot_path() -> Path:
    return workspace_root() / SNAPSHOT_RELATIVE_PATH


def _read_env_client_id(env_path: Path) -> str | None:
    """Return ONLY the SPOTIFY_CLIENT_ID value from .env; never expose other keys."""
    try:
        with open(env_path, "r", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                line = raw.lstrip("\ufeff").strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if key.startswith("export "):
                    key = key[len("export "):].strip()
                if key == "SPOTIFY_CLIENT_ID":
                    return value.strip().strip('"').strip("'") or None
    except OSError:
        return None
    return None


def resolve_client_id() -> tuple[str | None, str]:
    """Return (client_id, source label). Environment first, then .env."""
    from_env = os.environ.get("SPOTIFY_CLIENT_ID", "").strip()
    if from_env:
        return from_env, "env SPOTIFY_CLIENT_ID"
    from_file = _read_env_client_id(workspace_root() / ".env")
    if from_file:
        return from_file, ".env SPOTIFY_CLIENT_ID"
    return None, "missing"


def require_client_id() -> str:
    client_id, _ = resolve_client_id()
    if not client_id:
        raise TasteError(
            "missing Spotify client ID: add `SPOTIFY_CLIENT_ID=<your app client id>` to "
            f"{workspace_root() / '.env'} (see .env.example), or set the "
            "SPOTIFY_CLIENT_ID environment variable."
        )
    return client_id


def mask(value: str) -> str:
    """Masked hint for stdout: at most the first four characters."""
    return f"{value[:4]}..." if len(value) > 8 else "(set)"


# ---------------------------------------------------------------------------
# Token cache
# ---------------------------------------------------------------------------


def load_token() -> dict[str, Any] | None:
    """Return the cached token dict, or None when missing/unreadable/incomplete."""
    path = token_path()
    if not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not data.get("access_token"):
        return None
    return data


def save_token(token: dict[str, Any]) -> None:
    path = token_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(token, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except OSError as exc:
        raise TasteError(f"could not write token cache {path}: {exc}") from None


def _is_expired(token: dict[str, Any]) -> bool:
    try:
        expires_at = float(token.get("expires_at", 0))
    except (TypeError, ValueError):
        return True
    return time.time() >= expires_at - REFRESH_SKEW_SECONDS


def ensure_token() -> dict[str, Any]:
    """Load the cached token, refreshing it when expired or nearly expired."""
    token = load_token()
    if token is None:
        raise TasteError(
            "not authenticated: no token cache found. Run "
            "`python scripts/spotify_taste.py auth` first."
        )
    if _is_expired(token):
        return refresh_access_token(token)
    return token


def refresh_access_token(token: dict[str, Any] | None = None) -> dict[str, Any]:
    """Exchange the refresh token for a new access token (client_id only, no secret)."""
    token = token or load_token()
    if not token or not token.get("refresh_token"):
        raise TasteError(
            "token cache has no refresh token available; run "
            "`python scripts/spotify_taste.py auth` again."
        )
    client_id = require_client_id()
    payload = _open_json(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
            "client_id": client_id,
        },
    )
    access_token = payload.get("access_token")
    if not access_token:
        raise TasteError("token refresh returned no access token; run `auth` again.")
    try:
        expires_in = int(payload.get("expires_in") or 3600)
    except (TypeError, ValueError):
        expires_in = 3600
    merged: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": payload.get("refresh_token") or token["refresh_token"],
        "expires_at": time.time() + expires_in,
        "scope": payload.get("scope") or token.get("scope", SCOPES),
    }
    save_token(merged)
    return merged


# ---------------------------------------------------------------------------
# HTTP plumbing (stdlib urllib only)
# ---------------------------------------------------------------------------


def _extract_error(raw: str) -> str:
    """Pull a short human message out of a Spotify error body."""
    try:
        payload = json.loads(raw)
    except ValueError:
        return ""
    if not isinstance(payload, dict):
        return ""
    detail: Any = payload.get("error_description") or payload.get("error") or ""
    if isinstance(detail, dict):
        detail = detail.get("message", "")
    return detail[:200] if isinstance(detail, str) else ""


def _open_json(
    url: str,
    *,
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """POST form data (when data is given) or GET, then parse a JSON object."""
    body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
    request_headers = dict(headers or {})
    if body is not None:
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=body, headers=request_headers)
    host = urllib.parse.urlparse(url).netloc
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = _extract_error(exc.read().decode("utf-8", "replace"))
        raise HttpError(exc.code, detail or f"HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TasteError(f"network error contacting {host}: {exc}") from None
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except ValueError:
        raise TasteError(f"unexpected non-JSON response from {host}") from None
    if not isinstance(payload, dict):
        raise TasteError(f"unexpected response shape from {host}") from None
    return payload


def _api_get(path: str, access_token: str) -> dict[str, Any]:
    return _open_json(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {access_token}"},
    )


def _raise_api_error(path: str, exc: HttpError, after_refresh: bool = False) -> NoReturn:
    if exc.code == 403:
        raise TasteError(
            f"Spotify returned 403 Forbidden for {path}. Dev Mode apps require the "
            "app owner to have Spotify Premium, and only users on the app allowlist "
            "can authorize it."
        ) from None
    if exc.code == 401:
        suffix = " even after refreshing the token" if after_refresh else ""
        raise TasteError(
            f"Spotify rejected the access token (401){suffix}. Run "
            "`python scripts/spotify_taste.py auth` again."
        ) from None
    if exc.code == 429:
        raise TasteError(
            "Spotify rate-limited the request (429); wait a minute and re-run `fetch`."
        ) from None
    raise TasteError(f"Spotify API error {exc.code} for {path}: {exc.message}") from None


def _fetch_endpoint(path: str) -> dict[str, Any]:
    """GET an API path, refreshing the token once and retrying on a 401."""
    token = ensure_token()
    try:
        return _api_get(path, token["access_token"])
    except HttpError as exc:
        if exc.code != 401:
            _raise_api_error(path, exc)
    refreshed = refresh_access_token(token)
    try:
        return _api_get(path, refreshed["access_token"])
    except HttpError as exc:
        _raise_api_error(path, exc, after_refresh=True)


def _fetch_list(path: str) -> list[dict[str, Any]]:
    payload = _fetch_endpoint(path)
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


# ---------------------------------------------------------------------------
# OAuth Authorization Code + PKCE
# ---------------------------------------------------------------------------


class _AuthServer(http.server.HTTPServer):
    """Loopback HTTPServer that records the single OAuth callback result."""

    allow_reuse_address = False  # Windows: SO_REUSEADDR would hide a busy port

    def __init__(self, address: tuple[str, int]) -> None:
        super().__init__(address, _CallbackHandler)
        self.timeout = 1  # let the caller poll for a deadline while accepting requests
        self.expected_state: str = ""
        self.auth_result: dict[str, str] | None = None

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Never dump a traceback for a stray or aborted browser connection."""
        return


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Serve the /callback redirect once, then let the server loop stop."""

    server: "_AuthServer"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self._send_page(
                404,
                "Not found",
                "Waiting for the Spotify callback at <code>/callback</code>.",
            )
            return
        params = urllib.parse.parse_qs(parsed.query)
        error = _first(params, "error")
        state = _first(params, "state")
        code = _first(params, "code")
        if error:
            self.server.auth_result = {"error": error}
            self._send_page(
                400,
                "Authorization failed",
                f"Spotify returned <code>{html.escape(error)}</code>. You can close "
                "this tab and re-run <code>auth</code>.",
            )
            return
        if state != self.server.expected_state:
            self.server.auth_result = {"error": "state_mismatch"}
            self._send_page(
                400,
                "Authorization failed",
                "State mismatch: this callback did not match the pending "
                "authorization. You can close this tab and re-run <code>auth</code>.",
            )
            return
        if not code:
            self.server.auth_result = {"error": "missing_code"}
            self._send_page(
                400,
                "Authorization failed",
                "No authorization code was returned. You can close this tab and "
                "re-run <code>auth</code>.",
            )
            return
        self.server.auth_result = {"code": code}
        self._send_page(
            200,
            "Authorization complete",
            "Authorization complete - you can close this tab and return to the terminal.",
        )

    def log_message(self, format_string: str, *args: Any) -> None:
        """Silence the default request logging (it would print callback query strings)."""
        return

    def _send_page(self, status: int, title: str, message: str) -> None:
        body = (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<title>{html.escape(title)}</title></head>"
            '<body style="font-family: system-ui, sans-serif; margin: 4rem auto; '
            'max-width: 36rem;">'
            f"<h1>{html.escape(title)}</h1><p>{message}</p></body></html>"
        )
        payload = body.encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except OSError:
            pass


def _first(params: dict[str, list[str]], key: str) -> str:
    values = params.get(key)
    return values[0] if values else ""


def _is_addr_in_use(exc: OSError) -> bool:
    if exc.errno == errno.EADDRINUSE:
        return True
    if getattr(exc, "winerror", None) == 10048:  # WSAEADDRINUSE
        return True
    text = str(exc).lower()
    return "address already in use" in text or "only one usage of each socket address" in text


def _bind_auth_server(port: int) -> _AuthServer:
    try:
        return _AuthServer(("127.0.0.1", port))
    except OSError as exc:
        if _is_addr_in_use(exc):
            suggested = port + 1 if port < 65535 else port - 1
            raise TasteError(
                f"port {port} is already in use. Re-run with a different port, e.g. "
                f"`python scripts/spotify_taste.py auth --port {suggested}`. The "
                "redirect URI must be registered exactly in the Spotify dashboard "
                f"(for example http://127.0.0.1:{suggested}/callback)."
            ) from None
        raise TasteError(f"could not bind 127.0.0.1:{port}: {exc}") from None


def run_auth(port: int) -> int:
    if not 1 <= port <= 65535:
        raise TasteError(f"invalid --port {port}: pick a value between 1 and 65535.")
    client_id, source = resolve_client_id()
    if not client_id:
        require_client_id()  # raises the friendly missing-client-id message

    redirect_uri = f"http://127.0.0.1:{port}/callback"
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    state = secrets.token_urlsafe(24)
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
            "state": state,
            "scope": SCOPES,
        }
    )
    authorize_url = f"{AUTHORIZE_URL}?{query}"

    server = _bind_auth_server(port)
    server.expected_state = state

    print("Spotify authorization (Authorization Code + PKCE, no client secret)")
    print(f"  client id:    {mask(client_id)} ({source})")
    print(f"  redirect URI: {redirect_uri}")
    print("  Register this exact redirect URI in the Spotify dashboard, or consent will fail.")
    print(
        f"Waiting for the callback on http://127.0.0.1:{port}/callback "
        f"(up to {AUTH_TIMEOUT_SECONDS // 60} minutes)..."
    )
    try:
        try:
            opened = webbrowser.open(authorize_url)
        except Exception:
            opened = False
        if not opened:
            print(
                "Could not open a browser automatically. Re-run `auth` on a desktop "
                "session, or set the BROWSER environment variable."
            )
        deadline = time.monotonic() + AUTH_TIMEOUT_SECONDS
        while server.auth_result is None and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()

    result = server.auth_result
    if result is None:
        raise TasteError("timed out waiting for the Spotify callback; re-run `auth`.")
    if "error" in result:
        reason = result["error"]
        if reason == "state_mismatch":
            raise TasteError(
                "callback state did not match this session (possible cross-site "
                "request); re-run `auth`."
            )
        if reason == "access_denied":
            raise TasteError(
                "authorization was denied (access_denied); re-run `auth` to try again."
            )
        raise TasteError(
            f"Spotify returned '{reason}' during authorization; re-run `auth` to try again."
        )

    code = result.get("code", "")
    try:
        payload = _open_json(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "code_verifier": verifier,
            },
        )
    except HttpError as exc:
        raise TasteError(f"token exchange failed: HTTP {exc.code}: {exc.message}") from None

    access_token = payload.get("access_token")
    if not access_token:
        raise TasteError("token exchange returned no access token; re-run `auth`.")
    try:
        expires_in = int(payload.get("expires_in") or 3600)
    except (TypeError, ValueError):
        expires_in = 3600
    token: dict[str, Any] = {
        "access_token": access_token,
        "refresh_token": payload.get("refresh_token", ""),
        "expires_at": time.time() + expires_in,
        "scope": payload.get("scope", SCOPES),
    }
    save_token(token)
    print(f"Authenticated. Token cached at {token_path()}")
    if not token["refresh_token"]:
        print(
            "Warning: Spotify did not return a refresh token; re-run `auth` if "
            "`fetch` asks for one."
        )
    print("Next: python scripts/spotify_taste.py fetch")
    return 0


# ---------------------------------------------------------------------------
# Snapshot rendering
# ---------------------------------------------------------------------------


def _artist_label(artists: Any) -> str:
    names = [
        artist.get("name", "Unknown artist")
        for artist in artists
        if isinstance(artist, dict) and artist.get("name")
    ] if isinstance(artists, list) else []
    return ", ".join(names) if names else "Unknown artist"


def _track_label(track: dict[str, Any]) -> str:
    return f"{_artist_label(track.get('artists'))} \u2014 {track.get('name', 'Unknown track')}"


def _playlist_item_count(playlist: dict[str, Any]) -> int:
    """Item count from playlist.items.total, defaulting to 0."""
    items = playlist.get("items")
    if isinstance(items, dict):
        try:
            return int(items.get("total") or 0)
        except (TypeError, ValueError):
            return 0
    if isinstance(items, list):
        return len(items)
    return 0


def _truncate(text: str, limit: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + "\u2026"


def _recent_entries(recent: dict[str, Any]) -> list[str]:
    """Last unique plays, most recent first, as 'artist - title (played date)'."""
    items = recent.get("items")
    if not isinstance(items, list):
        return []
    entries: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        track = item.get("track") if isinstance(item.get("track"), dict) else {}
        key = track.get("id") or f"{_artist_label(track.get('artists'))}|{track.get('name', '')}"
        if key in seen:
            continue
        seen.add(key)
        played_at = item.get("played_at")
        date = played_at[:10] if isinstance(played_at, str) and len(played_at) >= 10 else ""
        label = _track_label(track)
        entries.append(f"{label} ({date})" if date else label)
        if len(entries) >= RECENT_UNIQUE_LIMIT:
            break
    return entries


def render_snapshot(
    artists_by_range: dict[str, list[dict[str, Any]]],
    tracks_by_range: dict[str, list[dict[str, Any]]],
    playlists: list[dict[str, Any]],
    recent: dict[str, Any],
) -> str:
    """Render the sanitized Markdown snapshot (no tokens, client IDs, or emails)."""
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines: list[str] = [
        "# Spotify Taste Snapshot",
        "",
        f"Generated by `scripts/spotify_taste.py` on {generated}.",
        "",
        "Do not hand-edit this file: `python scripts/spotify_taste.py fetch` overwrites it.",
        "",
        "## Top Artists",
        "",
    ]
    for time_range in TIME_RANGES:
        lines.append(f"### {TIME_RANGE_LABELS[time_range]}")
        lines.append("")
        artists = artists_by_range.get(time_range, [])
        if not artists:
            lines.append("_No data returned._")
        else:
            for rank, artist in enumerate(artists, 1):
                lines.append(f"{rank}. {artist.get('name', 'Unknown artist')}")
        lines.append("")

    lines.append("## Top Tracks")
    lines.append("")
    for time_range in TIME_RANGES:
        lines.append(f"### {TIME_RANGE_LABELS[time_range]}")
        lines.append("")
        tracks = tracks_by_range.get(time_range, [])
        if not tracks:
            lines.append("_No data returned._")
        else:
            for rank, track in enumerate(tracks, 1):
                lines.append(f"{rank}. {_track_label(track)}")
        lines.append("")

    lines.append("## Playlists")
    lines.append("")
    if not playlists:
        lines.append("_No playlists returned._")
    else:
        for playlist in playlists:
            name = playlist.get("name", "Untitled playlist")
            count = _playlist_item_count(playlist)
            description = _truncate(playlist.get("description") or "", 80)
            suffix = f" \u2014 {description}" if description else ""
            lines.append(f"- **{name}** ({count} items){suffix}")
    lines.append("")

    lines.append("## Recently Played")
    lines.append("")
    entries = _recent_entries(recent)
    if not entries:
        lines.append("_No recent plays returned._")
    else:
        for entry in entries:
            lines.append(f"- {entry}")
    lines.append("")

    return "\n".join(lines)


def write_snapshot(markdown: str) -> Path:
    path = snapshot_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown)
    except OSError as exc:
        raise TasteError(f"could not write snapshot {path}: {exc}") from None
    return path


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def run_fetch() -> int:
    ensure_token()  # fail fast with the friendly "run auth first" message

    artists_by_range: dict[str, list[dict[str, Any]]] = {}
    tracks_by_range: dict[str, list[dict[str, Any]]] = {}
    for time_range in TIME_RANGES:
        artists_by_range[time_range] = _fetch_list(
            f"/me/top/artists?time_range={time_range}&limit={TOP_LIMIT}"
        )
        tracks_by_range[time_range] = _fetch_list(
            f"/me/top/tracks?time_range={time_range}&limit={TOP_LIMIT}"
        )
    playlists = _fetch_list(f"/me/playlists?limit={PLAYLIST_LIMIT}")
    recent = _fetch_endpoint(f"/me/player/recently-played?limit={RECENT_LIMIT}")

    markdown = render_snapshot(artists_by_range, tracks_by_range, playlists, recent)
    path = write_snapshot(markdown)

    print(f"Snapshot written: {path}")
    for time_range in TIME_RANGES:
        print(
            f"  top {TIME_RANGE_LABELS[time_range].lower()}: "
            f"{len(artists_by_range[time_range])} artists, "
            f"{len(tracks_by_range[time_range])} tracks"
        )
    print(f"  playlists: {len(playlists)}")
    print(f"  recently played (unique, capped at {RECENT_UNIQUE_LIMIT}): {len(_recent_entries(recent))}")
    return 0


def run_status() -> int:
    client_id, source = resolve_client_id()
    print("Spotify taste snapshot status")
    print(f"  workspace:  {workspace_root()}")
    if client_id:
        print(f"  client id:  {mask(client_id)} ({source})")
    else:
        print("  client id:  not configured - add SPOTIFY_CLIENT_ID to .env (see .env.example)")

    path = token_path()
    if not path.is_file():
        print("  auth:       not authenticated - run: python scripts/spotify_taste.py auth")
        print(f"  token file: {path} (not created yet)")
    else:
        token = load_token()
        if token is None:
            print(
                "  auth:       token cache unreadable or incomplete - run: "
                "python scripts/spotify_taste.py auth"
            )
        else:
            if _is_expired(token):
                if token.get("refresh_token"):
                    print("  auth:       token expired - `fetch` refreshes it automatically")
                else:
                    print(
                        "  auth:       token expired and no refresh token cached - run: "
                        "python scripts/spotify_taste.py auth"
                    )
            else:
                try:
                    remaining = int(float(token.get("expires_at", 0)) - time.time())
                except (TypeError, ValueError):
                    remaining = 0
                print(
                    "  auth:       authenticated "
                    f"(access token valid ~{max(remaining, 0) // 60} more min)"
                )
            if token.get("scope"):
                print(f"  scopes:     {token['scope']}")
        print(f"  token file: {path}")

    snapshot = snapshot_path()
    suffix = "" if snapshot.is_file() else " (not generated yet)"
    print(f"  snapshot:   {snapshot}{suffix}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spotify_taste.py",
        description=(
            "Fetch your Spotify top artists/tracks, playlists, and recent plays "
            "into a sanitized Markdown snapshot."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")
    auth_parser = subparsers.add_parser(
        "auth", help="Run the one-time Spotify Authorization Code + PKCE browser flow"
    )
    auth_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local callback port (default: {DEFAULT_PORT})",
    )
    subparsers.add_parser(
        "fetch", help="Write internal-docs/SPOTIFY_SNAPSHOT.md from the Spotify Web API"
    )
    subparsers.add_parser("status", help="Report auth state (never prints secrets)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = getattr(args, "command", None)
    if not command:
        parser.print_help()
        return 0
    try:
        if command == "auth":
            return run_auth(args.port)
        if command == "fetch":
            return run_fetch()
        if command == "status":
            return run_status()
    except TasteError as exc:
        print(f"error: {exc}")
        return 1
    except KeyboardInterrupt:
        print("aborted.")
        return 1
    except Exception as exc:  # no traceback dumps, ever
        print(f"error: unexpected {exc.__class__.__name__}: {exc}")
        return 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
