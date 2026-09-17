# -*- coding: utf-8 -*-
"""Forum-Stand (Text + Bilder) speichern und mit dem letzten Zyklus vergleichen."""

import difflib
import hashlib
import io
import json
import os
import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag
from curl_cffi import requests
from PIL import Image

from config import SNAPSHOT_DIR

MAX_IMAGES = 80
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MIN_IMAGE_BYTES = 2500
REQUEST_TIMEOUT = 20
IMAGE_TIMEOUT = 6
HASH_SIZE = 8
HAMMING_SAME = 6
HAMMING_CHANGED = 18
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
SKIP_IMAGE_RE = re.compile(
    r"oasuserpic|1491014136\.png|1505731497\.png|1460357149\.gif|cdn-cgi",
    re.I,
)
EVENT_HEAD_RE = re.compile(r"-\s*(\d+)\s*-\s*(.+)")
NOISE_RE = re.compile(
    r"aktionszeitraum|nach der aktualisierung|23:59|"
    r"details zur aktion|aktionsdetails findest du|zeitlich begrenzter hit|"
    r"zuletzt von|gepostet am|mitglied seit|nur beiträge|"
    r"umgekehrte reihenfolge|^beiträge:?$|^antworten:?$|^moderator$|"
    r"^views:|^auf seite|liebe spieler|offizieller discord|"
    r"w[äa]hrend dieser zeit ist der login",
    re.I,
)
STOP_THREAD_RE = re.compile(
    r"zuletzt von|gepostet am|nur beiträge dieses|\d+\s*＃",
    re.I,
)
TIME_ONLY_RE = re.compile(r"^[\d\s.:：｜\-#＃/]+$")
GOLD_LINE_RE = re.compile(
    r"^(\d+)\s*Goldbarren(?:\s*/\s*Coupons)?:\s*(.+)$",
    re.I,
)

_session = requests.Session(impersonate="chrome")


def http_get(url, timeout=REQUEST_TIMEOUT):
    response = _session.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Referer": "https://forum-narutode.narutowebgame.com/",
        },
        allow_redirects=True,
    )
    return response


def assert_not_blocked(response):
    html = response.text if (response.headers.get("content-type") or "").startswith("text/") else ""
    blocked = response.status_code == 403 or "cf-error-details" in html or "Attention Required" in html
    if blocked or response.status_code >= 400:
        raise ValueError(
            "Cloudflare blockt den Abruf (HTTP %s). Docker/Python kommt da oft nicht durch. "
            "App auf dem PC mit `python app.py` starten (ohne Docker) und nochmal versuchen, "
            "oder den Foren-Post im Browser oeffnen, eingeloggt bleiben, dann erneut klicken."
            % response.status_code
        )


def normalize_text(text):
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def average_hash(image, size=HASH_SIZE):
    gray = image.convert("L").resize((size, size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    avg = sum(pixels) / float(len(pixels))
    value = 0
    for pixel in pixels:
        value = (value << 1) | (1 if pixel >= avg else 0)
    return format(value, "016x")


def hamming_hex(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def hash_image_bytes(data):
    image = Image.open(io.BytesIO(data))
    image.load()
    return average_hash(image)


def extract_from_html(html, base_url=""):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    body_text = normalize_text(soup.get_text("\n", strip=True))
    events = extract_events(soup, base_url)
    urls = []
    seen = set()
    for event in events:
        for img in event.get("images") or []:
            url = img.get("orig_url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            urls.append(url)
    if not urls:
        for img in soup.find_all("img"):
            full = resolve_img_url(img, base_url)
            if not full or full in seen:
                continue
            seen.add(full)
            urls.append(full)
            if len(urls) >= MAX_IMAGES:
                break
    return body_text, urls, events


def resolve_img_url(img, base_url):
    src = img.get("src") or img.get("data-src") or img.get("data-original")
    if not src or src.startswith("data:"):
        return None
    full = urljoin(base_url, src)
    if SKIP_IMAGE_RE.search(full):
        return None
    return full


def extract_events(soup, base_url):
    events = []
    current = {"order": 0, "name": "Kopf / Allgemein", "text": "", "images": []}
    seen_img = set()

    in_replies = False

    def push():
        if current["order"] or current["images"] or current["text"].strip():
            events.append(current)

    root = soup.body or soup
    for node in root.descendants:
        if isinstance(node, Tag) and node.name == "img":
            if in_replies:
                continue
            full = resolve_img_url(node, base_url)
            if not full or full in seen_img:
                continue
            seen_img.add(full)
            current["images"].append(
                {"filename": "", "phash": url_phash(full), "orig_url": full}
            )
            continue
        if not isinstance(node, NavigableString):
            continue
        if node.parent and node.parent.name in ("script", "style"):
            continue
        text = str(node).strip()
        if not text:
            continue
        match = EVENT_HEAD_RE.search(text)
        if match:
            in_replies = False
            push()
            rest = text[match.end():].strip()
            current = {
                "order": int(match.group(1)),
                "name": match.group(2).strip().strip('"').strip(),
                "text": (rest + "\n") if rest and not is_noise_line(rest) else "",
                "images": [],
            }
        else:
            if STOP_THREAD_RE.search(text):
                in_replies = True
                continue
            if in_replies or is_noise_line(text):
                continue
            current["text"] += text + "\n"
    push()
    numbered = [ev for ev in events if ev["order"]]
    return numbered or events


def image_key(url):
    try:
        query = parse_qs(urlparse(url).query)
        name = (query.get("img_name") or [None])[0]
        if name:
            return unquote(unquote(name))
    except Exception:
        pass
    path = urlparse(url).path
    return path.rsplit("/", 1)[-1] or url


def url_phash(url):
    return hashlib.sha256(image_key(url).encode("utf-8")).hexdigest()[:16]


def capture_forum_url(url):
    body_text, image_urls, events = fetch_url(url)
    return body_text, collect_images_from_urls(image_urls), events


def fetch_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Nur http/https URLs sind erlaubt.")
    response = http_get(url)
    assert_not_blocked(response)
    return extract_from_html(response.text, str(response.url))


def download_image(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return None
    try:
        response = http_get(url, timeout=IMAGE_TIMEOUT)
    except Exception:
        return None
    if response.status_code >= 400:
        return None
    data = response.content
    if len(data) < MIN_IMAGE_BYTES or len(data) > MAX_IMAGE_BYTES:
        return None
    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception:
        return None
    return data


def ext_for_bytes(data, fallback=".jpg"):
    try:
        fmt = (Image.open(io.BytesIO(data)).format or "").lower()
    except Exception:
        return fallback
    mapping = {"jpeg": ".jpg", "png": ".png", "gif": ".gif", "webp": ".webp"}
    return mapping.get(fmt, fallback)


def store_image_bytes(data, orig_url=""):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    phash = hash_image_bytes(data)
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}{ext_for_bytes(data)}"
    path = os.path.join(SNAPSHOT_DIR, filename)
    if not os.path.isfile(path):
        with open(path, "wb") as handle:
            handle.write(data)
    return {"filename": filename, "phash": phash, "orig_url": orig_url}


def collect_images_from_urls(urls):
    """Nur URLs merken — Download im Worker wuerde Gunicorn sprengen (30+ Bilder)."""
    stored = []
    seen = set()
    for url in urls:
        key = image_key(url)
        if key in seen:
            continue
        seen.add(key)
        stored.append({"filename": "", "phash": url_phash(url), "orig_url": url})
        if len(stored) >= MAX_IMAGES:
            break
    return stored


def collect_images_from_uploads(files):
    stored = []
    for upload in files:
        if not upload or not getattr(upload, "filename", None):
            continue
        data = upload.read()
        if len(data) < MIN_IMAGE_BYTES or len(data) > MAX_IMAGE_BYTES:
            continue
        try:
            stored.append(store_image_bytes(data, upload.filename))
        except Exception:
            continue
        if len(stored) >= MAX_IMAGES:
            break
    return stored


def text_diff_lines(old_text, new_text):
    old_lines = normalize_text(old_text).splitlines()
    new_lines = normalize_text(new_text).splitlines()
    diff = list(
        difflib.unified_diff(old_lines, new_lines, fromfile="letzter Zyklus", tofile="aktuell", lineterm="")
    )
    return diff


def compare_images(prev_images, curr_images):
    unused_prev = list(prev_images)
    unchanged, changed, added = [], [], []
    for current in curr_images:
        current_key = image_key(current.get("orig_url") or "")
        key_match = next(
            (
                index
                for index, previous in enumerate(unused_prev)
                if image_key(previous.get("orig_url") or "") == current_key and current_key
            ),
            None,
        )
        if key_match is not None:
            previous = unused_prev.pop(key_match)
            unchanged.append({"previous": previous, "current": current, "distance": 0})
            continue
        best_i = None
        best_d = 10**9
        for index, previous in enumerate(unused_prev):
            try:
                distance = hamming_hex(previous["phash"], current["phash"])
            except Exception:
                continue
            if distance < best_d:
                best_d = distance
                best_i = index
        if best_i is None or best_d > HAMMING_CHANGED:
            added.append(current)
            continue
        previous = unused_prev.pop(best_i)
        pair = {"previous": previous, "current": current, "distance": best_d}
        if best_d <= HAMMING_SAME:
            unchanged.append(pair)
        else:
            changed.append(pair)
    removed = unused_prev
    return {
        "unchanged": unchanged,
        "changed": changed,
        "added": added,
        "removed": removed,
    }


def is_noise_line(line):
    line = (line or "").strip()
    if not line or line in ("｜", "|", "＃", "#"):
        return True
    if TIME_ONLY_RE.match(line):
        return True
    return bool(NOISE_RE.search(line))


def clean_event_lines(text):
    lines = []
    for line in normalize_text(text or "").splitlines():
        line = line.strip().strip('"').strip()
        if not line or is_noise_line(line):
            continue
        lines.append(line)
    return lines


def token_diff_parts(old_line, new_line):
    token_re = re.compile(r"\s+|20\d{2}|[IVXLCDM]{2,}|\w+|[^\w\s]", re.UNICODE)
    old_tokens = token_re.findall(old_line) or [old_line]
    new_tokens = token_re.findall(new_line) or [new_line]
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)
    parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = "".join(old_tokens[i1:i2])
        new_chunk = "".join(new_tokens[j1:j2])
        if tag == "equal":
            if old_chunk:
                parts.append({"kind": "same", "text": old_chunk})
        elif tag == "replace":
            if old_chunk:
                parts.append({"kind": "del", "text": old_chunk})
            parts.append({"kind": "same", "text": " → "})
            if new_chunk:
                parts.append({"kind": "add", "text": new_chunk})
        elif tag == "delete":
            if old_chunk:
                parts.append({"kind": "del", "text": old_chunk})
        elif tag == "insert":
            if new_chunk:
                parts.append({"kind": "add", "text": new_chunk})
    return parts or [{"kind": "same", "text": new_line}]
    matcher = difflib.SequenceMatcher(None, old_line, new_line, autojunk=False)
    parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            if old_line[i1:i2]:
                parts.append({"kind": "same", "text": old_line[i1:i2]})
        elif tag == "replace":
            if old_line[i1:i2]:
                parts.append({"kind": "del", "text": old_line[i1:i2]})
            parts.append({"kind": "same", "text": " → "})
            if new_line[j1:j2]:
                parts.append({"kind": "add", "text": new_line[j1:j2]})
        elif tag == "delete":
            if old_line[i1:i2]:
                parts.append({"kind": "del", "text": old_line[i1:i2]})
        elif tag == "insert":
            if new_line[j1:j2]:
                parts.append({"kind": "add", "text": new_line[j1:j2]})
    return parts or [{"kind": "same", "text": new_line}]


def split_reward_items(blob):
    return [part.strip() for part in re.split(r"[,，]", blob or "") if part.strip()]


def item_stem(item):
    text = (item or "").lower()
    text = re.sub(r"\*\d+", "", text)
    text = re.sub(r"\b20\d{2}\b", "", text)
    text = re.sub(r"\b[ivx]+\b", "", text)
    text = re.sub(r"[\s*（）()]+", " ", text)
    return text.strip()


def parse_gold_line(line):
    match = GOLD_LINE_RE.match((line or "").strip())
    if not match:
        return None
    return int(match.group(1)), match.group(2).strip()


def split_gold_and_other(lines):
    gold = {}
    other = []
    for line in lines:
        parsed = parse_gold_line(line)
        if parsed:
            gold[parsed[0]] = parsed[1]
        else:
            other.append(line)
    return gold, other


def diff_reward_items(old_blob, new_blob):
    old_items = split_reward_items(old_blob)
    new_items = list(split_reward_items(new_blob))
    rows = []
    for old_item in old_items:
        best = None
        best_score = 0.0
        for new_item in new_items:
            score = difflib.SequenceMatcher(None, item_stem(old_item), item_stem(new_item)).ratio()
            if score > best_score:
                best_score = score
                best = new_item
        if best is not None and best_score >= 0.55:
            new_items.remove(best)
            if old_item != best:
                char_ratio = difflib.SequenceMatcher(None, old_item, best).ratio()
                if char_ratio >= 0.72:
                    rows.append(token_diff_parts(old_item, best))
                else:
                    rows.append(
                        [
                            {"kind": "del", "text": old_item},
                            {"kind": "same", "text": " → "},
                            {"kind": "add", "text": best},
                        ]
                    )
        else:
            rows.append([{"kind": "del", "text": "− " + old_item}])
    for new_item in new_items:
        rows.append([{"kind": "add", "text": "+ " + new_item}])
    return rows


def gold_tier_changes(old_gold, new_gold):
    changes = []
    for amount in sorted(set(old_gold) | set(new_gold)):
        prefix = [{"kind": "same", "text": f"{amount} Goldbarren: "}]
        if amount not in new_gold:
            changes.append(
                {"parts": prefix + [{"kind": "del", "text": "Stufe entfernt"}]}
            )
            continue
        if amount not in old_gold:
            changes.append(
                {"parts": prefix + [{"kind": "add", "text": "neue Stufe — " + new_gold[amount]}]}
            )
            continue
        item_rows = diff_reward_items(old_gold[amount], new_gold[amount])
        if not item_rows:
            continue
        if len(item_rows) == 1:
            changes.append({"parts": prefix + item_rows[0]})
        else:
            changes.append({"parts": prefix + [{"kind": "same", "text": ""}]})
            for row in item_rows:
                changes.append({"parts": row})
    return changes


def event_changes(old, new, old_imgs, new_imgs):
    changes = []
    old_name = (old or {}).get("name") or ""
    new_name = (new or {}).get("name") or ""
    if old_name and new_name and old_name != new_name:
        changes.append({"parts": token_diff_parts(old_name, new_name)})

    old_lines = clean_event_lines((old or {}).get("text"))
    new_lines = clean_event_lines((new or {}).get("text"))
    old_gold, old_other = split_gold_and_other(old_lines)
    new_gold, new_other = split_gold_and_other(new_lines)
    changes.extend(gold_tier_changes(old_gold, new_gold))

    matcher = difflib.SequenceMatcher(None, old_other, new_other, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace" and (i2 - i1) == 1 and (j2 - j1) == 1:
            if parse_gold_line(old_other[i1]) or parse_gold_line(new_other[j1]):
                continue
            changes.append({"parts": token_diff_parts(old_other[i1], new_other[j1])})
            continue
        if tag in ("delete", "replace"):
            for line in old_other[i1:i2]:
                if not parse_gold_line(line):
                    changes.append({"parts": [{"kind": "del", "text": "− " + line}]})
        if tag in ("insert", "replace"):
            for line in new_other[j1:j2]:
                if not parse_gold_line(line):
                    changes.append({"parts": [{"kind": "add", "text": "+ " + line}]})

    old_keys = [image_key(img.get("orig_url") or "") for img in old_imgs]
    new_keys = [image_key(img.get("orig_url") or "") for img in new_imgs]
    if old_keys != new_keys:
        slot = max(len(old_keys), len(new_keys))
        swapped = sum(
            1
            for index in range(min(len(old_keys), len(new_keys)))
            if old_keys[index] != new_keys[index]
        )
        extra = abs(len(new_keys) - len(old_keys))
        note = f"Paket-Bilder: {swapped} ausgetauscht"
        if extra:
            note += f", {extra} {'mehr' if len(new_keys) > len(old_keys) else 'weniger'}"
        note += " (Inhalt oft nur im Screenshot)."
        changes.append({"parts": [{"kind": "same", "text": note}]})

    if not old:
        changes = [{"parts": [{"kind": "add", "text": "Event neu in dieser Woche."}]}]
    elif not new:
        changes = [{"parts": [{"kind": "del", "text": "Event fehlt in dieser Woche."}]}]
    elif not changes:
        changes = [{"parts": [{"kind": "same", "text": "kein Textunterschied"}]}]
    return changes


def event_rows(prev_events, curr_events):
    prev_map = {int(ev["order"]): ev for ev in prev_events if ev.get("order")}
    curr_map = {int(ev["order"]): ev for ev in curr_events if ev.get("order")}
    if not prev_map and not curr_map:
        return []
    rows = []
    for order in sorted(set(prev_map) | set(curr_map)):
        old = prev_map.get(order)
        new = curr_map.get(order)
        old_imgs = (old or {}).get("images") or []
        new_imgs = (new or {}).get("images") or []
        old_keys = {image_key(img.get("orig_url") or "") for img in old_imgs}
        new_keys = {image_key(img.get("orig_url") or "") for img in new_imgs}
        old_name = (old or {}).get("name") or ""
        new_name = (new or {}).get("name") or ""
        if not old:
            status = "nur aktuell"
        elif not new:
            status = "nur letzter Zyklus"
        elif old_name != new_name:
            status = "Name geaendert"
        elif old_keys == new_keys and clean_event_lines((old or {}).get("text")) == clean_event_lines((new or {}).get("text")):
            status = "gleich"
        else:
            status = "geaendert"
        rows.append(
            {
                "order": order,
                "name": new_name or old_name,
                "old_name": old_name,
                "new_name": new_name,
                "status": status,
                "old_images": old_imgs,
                "new_images": new_imgs,
                "changes": event_changes(old, new, old_imgs, new_imgs),
            }
        )
    return rows


def load_events(snap):
    if not snap:
        return []
    raw = snap.get("events_json") or "[]"
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def analyze(previous, current, prev_images, curr_images):
    prev_events = load_events(previous)
    curr_events = load_events(current)
    rows = event_rows(prev_events, curr_events)
    if not previous:
        return {
            "has_previous": False,
            "diff_lines": [],
            "text_changed": False,
            "event_rows": rows,
            "images": {
                "unchanged": [],
                "changed": [],
                "added": list(curr_images),
                "removed": [],
            },
        }
    diff_lines = text_diff_lines(previous.get("body_text"), current.get("body_text"))
    changed_lines = [
        line
        for line in diff_lines
        if (line.startswith("+") and not line.startswith("+++"))
        or (line.startswith("-") and not line.startswith("---"))
    ]
    image_result = compare_images(prev_images, curr_images)
    return {
        "has_previous": True,
        "previous": previous,
        "diff_lines": diff_lines,
        "text_changed": bool(changed_lines),
        "event_rows": rows,
        "images": image_result,
    }
