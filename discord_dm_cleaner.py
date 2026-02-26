"""
Discord DM Message Cleaner
Deletes only the authenticated user's messages in all DM conversations.
Automatically detects all DMs; uses human-like delays and 429 handling.
"""

import os
import random
import re
import time
import logging
from typing import List, Optional, Set, Tuple

import requests
from dotenv import load_dotenv
from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------
load_dotenv()

DRY_RUN = False  # Set to True to only list messages without deleting
DISCORD_API_BASE = "https://discord.com/api/v10"

# Rate limiting (seconds) — 2.5 seconds between each message deletion
MESSAGE_DELETE_DELAY_MIN = 2.5
MESSAGE_DELETE_DELAY_MAX = 2.5
THREAD_SWITCH_DELAY_MIN = 10
THREAD_SWITCH_DELAY_MAX = 20
RATE_LIMIT_BACKOFF_SECONDS = 120

# -----------------------------------------------------------------------------
# LOCALIZATION (TR / EN)
# -----------------------------------------------------------------------------
LANG = "en"

TEXTS = {
    "tr": {
        "token_not_set": "DISCORD_TOKEN ayarlı değil. .env dosyasında DISCORD_TOKEN=... ekleyin.",
        "rate_limit": "Rate limit (429). %s saniye bekleniyor, tekrar denenecek...",
        "dry_run_on": "DRY RUN açık. Hiçbir mesaj silinmeyecek.",
        "authenticated": "Giriş yapıldı, kullanıcı ID: %s",
        "no_dms": "DM bulunamadı.",
        "detected_dms": "Tespit edilen DM'ler (%d adet):",
        "starting": "İşlem başlıyor (her DM için önce mesaj sayısı tespit edilecek, sonra silinecek).",
        "thread_switch": "Thread geçişi: %s–%s saniye bekleniyor...",
        "connecting": "Bağlanan / işlenen: %s",
        "dm_done": "DM %s tamamlandı: %d mesaj %s.",
        "done": "Bitti. DRY_RUN=%s",
        "messages_to_delete": "DM: %s — silinecek mesaj sayısı: %d",
        "action_will_delete": "Silinecek",
        "action_deleted": "Silindi",
        "message_progress": "%s mesaj (id=%s) | Kalan: %d mesaj",
        "dry_run_suffix": "silinecekti (dry run)",
        "deleted_suffix": "silindi",
        "exclude_title": "Hariç tutulacak DM'ler",
        "exclude_prompt": "Silmek istemediğiniz DM kullanıcı adlarını yazın (virgülle ayırın, boş bırakırsanız hepsi işlenir):",
        "exclude_example": "Örnek: murrez,aslanakbey",
        "excluded_label": "(hariç tutuldu)",
        "skip_forbidden": "Atlandı (silinemiyor, 403/404): %s",
    },
    "en": {
        "token_not_set": "DISCORD_TOKEN not set. Create a .env file with DISCORD_TOKEN=your_token",
        "rate_limit": "Rate limit hit (429). Sleeping for %s seconds before retry...",
        "dry_run_on": "DRY RUN mode is ON. No messages will be deleted.",
        "authenticated": "Authenticated as user ID: %s",
        "no_dms": "No DM channels found.",
        "detected_dms": "Detected DMs (%d total):",
        "starting": "Starting (for each DM: count messages, then delete).",
        "thread_switch": "Thread switch: waiting %s–%s seconds...",
        "connecting": "Connecting / processing: %s",
        "dm_done": "DM %s done: %d message(s) %s.",
        "done": "Done. DRY_RUN=%s",
        "messages_to_delete": "DM: %s — messages to delete: %d",
        "action_will_delete": "Would delete",
        "action_deleted": "Deleted",
        "message_progress": "%s message (id=%s) | Remaining: %d",
        "dry_run_suffix": "would be deleted (dry run)",
        "deleted_suffix": "deleted",
        "exclude_title": "Exclude DMs",
        "exclude_prompt": "Enter usernames to EXCLUDE from deletion (comma-separated, or leave empty for none):",
        "exclude_example": "Example: murrez,aslanakbey",
        "excluded_label": "(excluded)",
        "skip_forbidden": "Skipped (cannot delete, 403/404): %s",
    },
}


def t(key: str) -> str:
    """Return localized string for current LANG."""
    return TEXTS.get(LANG, TEXTS["en"]).get(key, TEXTS["en"].get(key, key))

# -----------------------------------------------------------------------------
# LOGGING (message text already contains ANSI colors when needed)
# -----------------------------------------------------------------------------
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger = logging.getLogger(__name__)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
logger.propagate = False



def get_token() -> str:
    """Load Discord token from environment."""
    token = os.getenv("DISCORD_TOKEN")
    if not token or not token.strip():
        raise SystemExit(t("token_not_set"))
    return token.strip()


def session_headers(token: str) -> dict:
    """Request headers for Discord API (user token)."""
    return {
        "Authorization": token,
        "Content-Type": "application/json",
    }


def get_own_user_id(token: str) -> Optional[str]:
    """Get the authenticated user's ID."""
    r = requests.get(
        f"{DISCORD_API_BASE}/users/@me",
        headers=session_headers(token),
        timeout=30,
    )
    if r.status_code == 429:
        return None  # Caller should handle 429
    r.raise_for_status()
    return r.json().get("id")


def get_dm_channels(token: str) -> Optional[list]:
    """Fetch all DM channels (1:1 and group). Returns None on 429."""
    r = requests.get(
        f"{DISCORD_API_BASE}/users/@me/channels",
        headers=session_headers(token),
        timeout=30,
    )
    if r.status_code == 429:
        return None
    r.raise_for_status()
    return r.json()


def get_channel_display_name(channel: dict) -> str:
    """Human-readable name for logging."""
    if channel.get("type") == 1 and channel.get("recipients"):
        return (channel["recipients"][0].get("username") or "Unknown")
    return channel.get("name") or "Group DM"


def channel_is_excluded(channel: dict, excluded: Set[str]) -> bool:
    """Return True if this DM should be skipped (username in excluded list)."""
    if not excluded:
        return False
    display_name = get_channel_display_name(channel).strip().lower()
    if display_name in excluded:
        return True
    # Group DM: check each recipient username
    for r in (channel.get("recipients") or []):
        uname = (r.get("username") or "").strip().lower()
        if uname in excluded:
            return True
    return False


def fetch_messages(
    token: str, channel_id: str, before: Optional[str] = None
) -> Tuple[List, bool]:
    """
    Fetch up to 100 messages in a channel.
    Returns (messages, hit_429). If hit_429 is True, messages is empty.
    """
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages?limit=100"
    if before:
        url += f"&before={before}"
    r = requests.get(url, headers=session_headers(token), timeout=30)
    if r.status_code == 429:
        return [], True
    r.raise_for_status()
    return r.json(), False


def delete_message(
    token: str, channel_id: str, message_id: str, dry_run: bool
) -> bool:
    """
    Delete a single message. Returns True on success, dry run, or skip (403/404); False on 429.
    """
    if dry_run:
        return True
    r = requests.delete(
        f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}",
        headers=session_headers(token),
        timeout=30,
    )
    if r.status_code == 429:
        return False
    if r.status_code in (200, 204):
        return True
    if r.status_code in (403, 404):
        # Forbidden or Not Found: message may be too old, already deleted, or no permission — skip
        short_id = message_id[:18] + "..." if len(message_id) > 18 else message_id
        logger.warning("%s", Fore.YELLOW + (t("skip_forbidden") % short_id) + Style.RESET_ALL)
        return True
    r.raise_for_status()
    return True


def handle_rate_limit() -> None:
    """Sleep for the required backoff period on 429."""
    msg = Fore.RED + (t("rate_limit") % RATE_LIMIT_BACKOFF_SECONDS) + Style.RESET_ALL
    logger.warning("%s", msg)
    time.sleep(RATE_LIMIT_BACKOFF_SECONDS)


def random_delay(min_sec: float, max_sec: float) -> None:
    """Human-like random delay."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


def collect_own_message_ids(
    token: str, channel_id: str, own_user_id: str
) -> Tuple[List[str], bool]:
    """
    Paginate through channel and return list of message IDs that belong to the user.
    Returns (list_of_ids, hit_429).
    """
    own_ids: List[str] = []
    before: Optional[str] = None

    while True:
        messages, hit_429 = fetch_messages(token, channel_id, before=before)
        if hit_429:
            return own_ids, True
        if not messages:
            break
        for msg in messages:
            if msg.get("author", {}).get("id") == own_user_id:
                mid = msg.get("id")
                if mid:
                    own_ids.append(mid)
        if len(messages) < 100:
            break
        before = messages[-1]["id"]

    return own_ids, False


def process_channel(
    token: str,
    own_user_id: str,
    channel: dict,
    dry_run: bool,
) -> int:
    """
    Delete all of the authenticated user's messages in one channel.
    First collects all own message IDs, then deletes one by one with remaining count.
    Returns count of messages deleted (or that would be deleted in dry run).
    """
    channel_id = channel["id"]
    display_name = get_channel_display_name(channel)

    # Collect all our message IDs (with 429 retry)
    message_ids: List[str] = []
    while True:
        message_ids, hit_429 = collect_own_message_ids(
            token, channel_id, own_user_id
        )
        if hit_429:
            handle_rate_limit()
            continue
        break

    total = len(message_ids)
    if total == 0:
        return 0

    # "DM: X — silinecek mesaj sayısı: N" / "DM: X — messages to delete: N"
    mid_tr, mid_en = " — silinecek mesaj sayısı: ", " — messages to delete: "
    mid = mid_tr if LANG == "tr" else mid_en
    msg = Fore.CYAN + "DM: " + Fore.WHITE + display_name + Fore.CYAN + mid + Fore.YELLOW + str(total) + Style.RESET_ALL
    logger.info("%s", msg)

    deleted = 0
    for i, msg_id in enumerate(message_ids):
        while True:
            ok = delete_message(token, channel_id, msg_id, dry_run)
            if ok:
                remaining = total - (i + 1)
                action = t("action_will_delete") if dry_run else t("action_deleted")
                short_id = msg_id[:18] + "..." if len(msg_id) > 18 else msg_id
                word = " mesaj " if LANG == "tr" else " message "
                kalan = "Kalan:" if LANG == "tr" else "Remaining:"
                msg = Fore.GREEN + action + Fore.WHITE + word + "(id=" + short_id + ") | " + Fore.YELLOW + kalan + " " + str(remaining) + Style.RESET_ALL
                logger.info("%s", msg)
                deleted += 1
                if not dry_run:
                    random_delay(
                        MESSAGE_DELETE_DELAY_MIN, MESSAGE_DELETE_DELAY_MAX
                    )
                break
            handle_rate_limit()

    return deleted


def ask_language() -> str:
    """Prompt for TR or ENG at startup. Returns 'tr' or 'en'."""
    print()
    print(Fore.CYAN + "  ═══ Language / Dil ═══" + Style.RESET_ALL)
    print(Fore.WHITE + "  [1] TR - Türkçe")
    print("  [2] ENG - English" + Style.RESET_ALL)
    print()
    while True:
        choice = input(Fore.YELLOW + "  Select / Seçin (1 or 2): " + Style.RESET_ALL).strip()
        if choice in ("1", "tr", "TR"):
            return "tr"
        if choice in ("2", "eng", "ENG", "en"):
            return "en"
        print(Fore.RED + "  Invalid. Enter 1 for TR or 2 for ENG. / Geçersiz. TR için 1, ENG için 2 girin." + Style.RESET_ALL)


def ask_exclude() -> Set[str]:
    """Ask for usernames to exclude from deletion (comma-separated). Returns set of lowercased names."""
    print()
    print(Fore.MAGENTA + "  ═══ " + t("exclude_title") + " ═══" + Style.RESET_ALL)
    print(Fore.WHITE + "  " + t("exclude_prompt") + Style.RESET_ALL)
    print(Fore.CYAN + "  " + t("exclude_example") + Style.RESET_ALL)
    print()
    raw = input(Fore.YELLOW + "  > " + Style.RESET_ALL).strip()
    if not raw:
        return set()
    # Split by comma, strip, lower, drop empty
    names = {n.strip().lower() for n in re.split(r"[,،\s]+", raw) if n.strip()}
    return names


def main() -> None:
    global LANG
    LANG = ask_language()
    excluded = ask_exclude()
    print()

    token = get_token()
    dry_run = DRY_RUN
    if dry_run:
        logger.info("%s", Fore.YELLOW + t("dry_run_on") + Style.RESET_ALL)

    # Resolve own user ID (with 429 handling)
    own_user_id = get_own_user_id(token)
    while own_user_id is None:
        handle_rate_limit()
        own_user_id = get_own_user_id(token)
    short_id = own_user_id[:18] + "..."
    logger.info("%s", Fore.GREEN + (t("authenticated") % short_id) + Style.RESET_ALL)

    # Fetch DM channels (with 429 handling)
    channels = get_dm_channels(token)
    while channels is None:
        handle_rate_limit()
        channels = get_dm_channels(token)
    if not channels:
        logger.info("%s", Fore.RED + t("no_dms") + Style.RESET_ALL)
        return

    # Filter out excluded DMs; keep only channels we will process
    channels_to_process = [c for c in channels if not channel_is_excluded(c, excluded)]

    logger.info("%s", Fore.CYAN + (t("detected_dms") % len(channels)) + Style.RESET_ALL)
    for i, ch in enumerate(channels, 1):
        name = get_channel_display_name(ch)
        if channel_is_excluded(ch, excluded):
            logger.info("%s", "  " + Fore.YELLOW + str(i) + ". " + Fore.WHITE + name + " " + Fore.MAGENTA + t("excluded_label") + Style.RESET_ALL)
        else:
            logger.info("%s", "  " + Fore.YELLOW + str(i) + ". " + Fore.WHITE + name + Style.RESET_ALL)

    logger.info("")
    logger.info("%s", Fore.CYAN + t("starting") + Style.RESET_ALL)
    logger.info("")

    for i, channel in enumerate(channels_to_process):
        display_name = get_channel_display_name(channel)
        if i > 0:
            thread_msg = t("thread_switch") % (THREAD_SWITCH_DELAY_MIN, THREAD_SWITCH_DELAY_MAX)
            logger.info("%s", Fore.MAGENTA + thread_msg + Style.RESET_ALL)
            random_delay(THREAD_SWITCH_DELAY_MIN, THREAD_SWITCH_DELAY_MAX)

        logger.info("%s", Fore.CYAN + (t("connecting") % display_name) + Style.RESET_ALL)
        count = process_channel(token, own_user_id, channel, dry_run)
        suffix = t("dry_run_suffix") if dry_run else t("deleted_suffix")
        dm_done_msg = t("dm_done") % (display_name, count, suffix)
        logger.info("%s", Fore.GREEN + dm_done_msg + Style.RESET_ALL)

    logger.info("%s", Fore.GREEN + (t("done") % dry_run) + Style.RESET_ALL)


if __name__ == "__main__":
    main()
