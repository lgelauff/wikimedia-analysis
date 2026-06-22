"""
spn2.py — SavePageNow v2 (Internet Archive) submit + poll.

Credentials are resolved in this order (the value is read here, never passed as
an arg or logged — a caller/agent that invokes this never sees it):
  1. explicit access_key/secret_key args
  2. environment variables IA_ACCESS_KEY / IA_SECRET_KEY
  3. the central user-global secrets file: $AGENT_SECRETS_FILE, else
     ~/.config/agent-secrets/.env  (so the same keys work from any cwd/session)

Authenticating raises SPN2 limits substantially vs anonymous (12 vs 6 concurrent,
100k vs 4k captures/day) and counts captures against the account, not the IP.

Auth header format: Authorization: LOW {access_key}:{secret_key}
SPN2 API reference: https://docs.google.com/document/d/1Nsv52MvSjbLb2PCpHlat0gkzw0EvtSgpKHu4mk0MnrA
"""

import json
import os
import pathlib
import ssl
import time
import urllib.parse
import urllib.request

import certifi


def _secret(name: str) -> str:
    """env var first, then the central agent-secrets dotenv. Never logs the value.

    Self-contained on purpose (no cross-repo import) so this package stays
    independently installable.
    """
    val = os.environ.get(name)
    if val:
        return val
    path = pathlib.Path(os.environ.get(
        "AGENT_SECRETS_FILE", str(pathlib.Path.home() / ".config" / "agent-secrets" / ".env")))
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = s.partition("=")
            if k.strip().removeprefix("export ").strip() == name:
                return v.strip().strip('"').strip("'")
    except OSError:
        pass
    return ""

SPN2_BASE    = "https://web.archive.org/save"
POLL_DELAY   = 8.0    # seconds between status polls
POLL_TIMEOUT = 180    # seconds before giving up on a single capture

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_UA = "WikimediaAnalysis/1.0 (personal research; lodewijk@stanford.edu; https://github.com/lgelauff/wikimedia-analysis)"


class SPN2Client:
    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
    ):
        """
        Load credentials from env vars if not provided explicitly.
        Raises EnvironmentError if credentials cannot be found.
        """
        self.access_key = access_key or _secret("IA_ACCESS_KEY")
        self.secret_key = secret_key or _secret("IA_SECRET_KEY")
        if not self.access_key or not self.secret_key:
            raise EnvironmentError(
                "Internet Archive credentials not found. Set IA_ACCESS_KEY and "
                "IA_SECRET_KEY (env), or add them to the central secrets file "
                "($AGENT_SECRETS_FILE, else ~/.config/agent-secrets/.env)."
            )
        self._auth = f"LOW {self.access_key}:{self.secret_key}"

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    def user_status(self) -> dict:
        """Return {available, processing, daily_captures, daily_captures_limit}."""
        return self._get(f"{SPN2_BASE}/status/user")

    def submit(self, url: str, if_not_archived_within: str | None = None) -> str:
        """
        Submit a capture request. Returns job_id string.

        if_not_archived_within: e.g. "14d", "30d", "365d" — SPN2 skips the
        capture if a snapshot already exists within this window.

        Waits for an available slot before submitting.
        """
        self._wait_for_slot()
        data: dict[str, str] = {"url": url, "capture_outlinks": "0"}
        if if_not_archived_within:
            data["if_not_archived_within"] = if_not_archived_within
        result = self._post(SPN2_BASE, data)
        job_id = result.get("job_id")
        if not job_id:
            raise RuntimeError(f"SPN2 submit returned no job_id: {result}")
        return job_id

    def poll(self, job_id: str) -> dict:
        """Return the current status dict for a job."""
        return self._get(f"{SPN2_BASE}/status/{job_id}")

    def capture(
        self,
        url: str,
        if_not_archived_within: str | None = None,
    ) -> dict:
        """
        Submit and poll until the capture succeeds, errors, or times out.

        Returns a dict with at minimum: status, timestamp, original_url.
        Raises RuntimeError on error status or timeout.
        """
        job_id = self.submit(url, if_not_archived_within)
        deadline = time.time() + POLL_TIMEOUT

        while True:
            status = self.poll(job_id)
            s = status.get("status", "")
            elapsed = int(time.time() - (deadline - POLL_TIMEOUT))
            print(f"[spn2 {s} {elapsed}s]", end=" ", flush=True)
            if s == "success":
                return status
            if s not in ("pending", "running"):
                raise RuntimeError(f"SPN2 capture failed — job {job_id}: {status}")
            if time.time() > deadline:
                raise RuntimeError(
                    f"SPN2 capture timed out after {POLL_TIMEOUT}s — job {job_id}"
                )
            time.sleep(POLL_DELAY)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _wait_for_slot(self, timeout: float = 120.0) -> None:
        """Block until at least one concurrent slot is available, or timeout."""
        deadline = time.time() + timeout
        while True:
            st = self.user_status()
            if st.get("available", 0) > 0:
                return
            if time.time() > deadline:
                raise RuntimeError(
                    f"No SPN2 slot available after {timeout:.0f}s "
                    f"(processing={st.get('processing')}, available={st.get('available')})"
                )
            time.sleep(POLL_DELAY)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._auth, "User-Agent": _UA}

    def _get(self, url: str) -> dict:
        req = urllib.request.Request(url, headers={**self._headers(), "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            body = e.read()
            raise RuntimeError(f"SPN2 GET {url} → HTTP {e.code}: {body[:200]}")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise RuntimeError(f"SPN2 GET {url} → non-JSON response: {body[:200]}")

    def _post(self, url: str, data: dict[str, str]) -> dict:
        payload = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={**self._headers(), "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                raise RuntimeError("SPN2 rate-limited (HTTP 429) — try again later")
            body = e.read()
            raise RuntimeError(f"SPN2 POST {url} → HTTP {e.code}: {body[:200]}")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            raise RuntimeError(f"SPN2 POST {url} → non-JSON response: {body[:200]}")
