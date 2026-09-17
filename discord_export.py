# -*- coding: utf-8 -*-
"""Discord-Text fuer eine komplette Eventwoche, in Channel-taugliche Stuecke."""

DISCORD_LIMIT = 4000
# Puffer fuer Teil-Header, Nitro-Limit ist 4000 Zeichen.
MAX_BODY = 3700


def event_block(ev):
    feedback = (ev.get("feedback") or "").strip()
    if not feedback:
        feedback = "(kein Feedback vorhanden)"
    return f"**{ev['event_order']} - {ev['name']}**\n{feedback}"


def _split_oversized(block, max_len):
    if len(block) <= max_len:
        return [block]
    pieces = []
    rest = block
    while rest:
        if len(rest) <= max_len:
            pieces.append(rest)
            break
        cut = rest.rfind("\n", 0, max_len)
        if cut < max_len // 2:
            cut = max_len
        pieces.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    return pieces


def _event_groups(events):
    groups = []
    current = []
    current_len = 0
    for ev in events:
        for piece in _split_oversized(event_block(ev), MAX_BODY):
            sep = 2 if current else 0
            if current and current_len + sep + len(piece) > MAX_BODY:
                groups.append(current)
                current = [piece]
                current_len = len(piece)
            else:
                current.append(piece)
                current_len += sep + len(piece)
    if current:
        groups.append(current)
    return groups


def build_discord_parts(week_label, week_start, week_end, events):
    """
    Gibt eine Liste von Strings zurueck, jeder unter DISCORD_LIMIT Zeichen.
    Eine Eventwoche = kompletter Inhalt, ggf. Teil 1/n ... n/n.
    """
    groups = _event_groups(events)
    if not groups:
        text = (
            f"**{week_label} - Feedback-Report**\n"
            f"Zeitraum: {week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}\n\n"
            "(keine Events)"
        )
        return [text]

    total = len(groups)
    parts = []
    date_range = f"{week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}"
    for index, blocks in enumerate(groups, start=1):
        body = "\n\n".join(blocks)
        if total == 1:
            header = (
                f"**{week_label} - Feedback-Report**\n"
                f"Zeitraum: {date_range}\n"
            )
        elif index == 1:
            header = (
                f"**{week_label} - Feedback-Report** (Teil {index}/{total})\n"
                f"Zeitraum: {date_range}\n"
            )
        else:
            header = f"**{week_label}** (Teil {index}/{total})\n"
        part = f"{header}\n{body}"
        if len(part) > DISCORD_LIMIT:
            raise ValueError(f"Discord-Teil {index} ist {len(part)} Zeichen lang")
        parts.append(part)
    return parts
