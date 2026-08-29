"""从 Gmail 等邮箱 IMAP 读取蜂巢/Zelto 登录验证码。"""

from __future__ import annotations

import email
import email.utils
import imaplib
import os
import re
import time
from email.header import decode_header
from typing import Any, Callable, Optional

OTP_PATTERNS = (
    re.compile(r"(?:验证码|verification code|code)[^\d]{0,20}(\d{4,8})", re.I),
    re.compile(r"验证码(\d{4,8})", re.I),
    re.compile(r"\b(\d{6})\b"),
)

HIVE_FROM_MARKERS = (
    "support@zelto.jp",
    "zelto.jp",
    "zelto",
    "蜂巢",
    "ihive",
)

DEFAULT_OTP_MAILBOX = "a16621325482@gmail.com"
DEFAULT_HIVE_IMAP_FOLDER = "蜂巢"
DEFAULT_POLL_INTERVAL = 5.0
DEFAULT_WAIT_PER_SEND = 60.0
DEFAULT_MAX_RESENDS = 1  # 首轮 + 1 次重发 = 共 2 轮


def otp_mailbox_email() -> str:
    return (os.environ.get("OTP_MAILBOX_EMAIL") or DEFAULT_OTP_MAILBOX).strip().lower()


def _imap_host_for_email(mailbox: str) -> str:
    domain = mailbox.split("@", 1)[-1].lower()
    if domain in {"gmail.com", "googlemail.com"}:
        return "imap.gmail.com"
    if domain in {"outlook.com", "hotmail.com", "live.com", "office365.com"}:
        return "outlook.office365.com"
    if domain == "163.com":
        return "imap.163.com"
    if domain == "126.com":
        return "imap.126.com"
    raise ValueError(f"unsupported mailbox domain for IMAP: {domain}")


def _decode_header_value(raw: str) -> str:
    parts: list[str] = []
    for chunk, enc in decode_header(raw or ""):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            parts.append(str(chunk))
    return "".join(parts)


def _extract_otp_from_text(text: str) -> Optional[str]:
    for pat in OTP_PATTERNS:
        m = pat.search(text or "")
        if m:
            code = m.group(1)
            if len(code) >= 4:
                return code
    return None


def _message_text(msg: email.message.Message) -> str:
    chunks: list[str] = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype not in ("text/plain", "text/html"):
                continue
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            charset = part.get_content_charset() or "utf-8"
            chunks.append(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            chunks.append(payload.decode(charset, errors="replace"))
    return "\n".join(chunks)


def _message_timestamp(msg: email.message.Message) -> float | None:
    date_tuple = email.utils.parsedate_tz(msg.get("Date") or "")
    if not date_tuple:
        return None
    return email.utils.mktime_tz(date_tuple)


def _is_hive_sender(msg: email.message.Message) -> bool:
    from_hdr = _decode_header_value(msg.get("From") or "").lower()
    subject = _decode_header_value(msg.get("Subject") or "").lower()
    blob = f"{from_hdr} {subject}"
    return any(marker in blob for marker in HIVE_FROM_MARKERS)


def _select_imap_folder(mail: imaplib.IMAP4_SSL, folder: str) -> bool:
    for name in (folder, f'"{folder}"'):
        try:
            status, _ = mail.select(name)
            if status == "OK":
                return True
        except imaplib.IMAP4.error:
            continue
    return False


def _imap_search_folders() -> tuple[str, ...]:
    """普通 Gmail 等邮箱：全量扫描常见文件夹。"""
    return (
        "INBOX",
        "[Gmail]/Important",  # 蜂巢验证码常落在此标签，不在 INBOX
        "[Gmail]/Promotions",
        "[Gmail]/Updates",
        "Junk",
        "Spam",
        "[Gmail]/Spam",
    )


def _hive_proxy_imap_folder() -> str:
    return (os.environ.get("OTP_HIVE_IMAP_FOLDER") or DEFAULT_HIVE_IMAP_FOLDER).strip()


def _imap_search_folders_for_mailbox(mailbox_email: str, recipient_email: str = "") -> tuple[str, ...]:
    """Outlook 代收（mailbox≠recipient）时只扫蜂巢标签；本号登录及其他邮箱全量扫。"""
    mailbox = (mailbox_email or "").strip().lower()
    recipient = (recipient_email or "").strip().lower()
    if mailbox == otp_mailbox_email() and recipient and recipient != mailbox:
        return (_hive_proxy_imap_folder(),)
    return _imap_search_folders()


def _imap_since_date(sent_after: float, clock_skew_s: float = 5.0) -> str:
    return time.strftime("%d-%b-%Y", time.localtime(sent_after - clock_skew_s))


def _recipient_matches(msg: email.message.Message, recipient_email: str, *, mailbox_email: str = "") -> bool:
    target = (recipient_email or "").strip().lower()
    if not target:
        return False
    # 读本账号邮箱时，只要发件人是蜂巢即可（避免 Gmail 头字段差异）
    if mailbox_email and mailbox_email.strip().lower() == target:
        return True
    header_names = (
        "To",
        "Delivered-To",
        "X-Original-To",
        "Envelope-To",
        "X-Received",
        "Cc",
    )
    for name in header_names:
        raw = _decode_header_value(msg.get(name) or "").lower()
        if target in raw:
            return True
    return False


def _scan_mailbox_for_otp(
    mail: imaplib.IMAP4_SSL,
    *,
    recipient_email: str,
    mailbox_email: str = "",
    sent_after: float,
    clock_skew_s: float = 5.0,
) -> tuple[str, float] | None:
    """返回 (otp, msg_ts) 中最新一封符合条件的验证码，否则 None。"""
    best: tuple[str, float] | None = None
    debug = os.environ.get("OTP_DEBUG", "").strip() in ("1", "true")
    since = _imap_since_date(sent_after, clock_skew_s)
    folders = _imap_search_folders_for_mailbox(mailbox_email, recipient_email)
    if debug and len(folders) == 1:
        print(
            f"[OTP-DEBUG] proxy scan mailbox={mailbox_email} recipient={recipient_email} "
            f"folder={folders[0]}",
            flush=True,
        )
    for folder in folders:
        if not _select_imap_folder(mail, folder):
            if debug:
                print(f"[OTP-DEBUG] skip folder={folder} (select failed)", flush=True)
            continue

        status, data = mail.search(None, f"(SINCE {since})")
        if status != "OK" or not data or not data[0]:
            status, data = mail.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            continue

        ids = data[0].split()
        if debug:
            print(f"[OTP-DEBUG] scan folder={folder} messages={len(ids)} since={since}", flush=True)
        for msg_id in reversed(ids[-30:]):
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            if not _is_hive_sender(msg):
                continue
            if not _recipient_matches(msg, recipient_email, mailbox_email=mailbox_email):
                continue
            msg_ts = _message_timestamp(msg)
            if msg_ts is None or msg_ts < sent_after - clock_skew_s:
                continue
            subject = _decode_header_value(msg.get("Subject") or "")
            body = _message_text(msg)
            otp = _extract_otp_from_text(subject) or _extract_otp_from_text(body)
            if not otp:
                continue
            if best is None or msg_ts > best[1]:
                best = (otp, msg_ts)
                if os.environ.get("OTP_DEBUG", "").strip() in ("1", "true"):
                    print(f"[OTP-DEBUG] hit folder={folder} ts={msg_ts} subj={subject[:50]}", flush=True)
    return best


def try_fetch_latest_otp(
    *,
    mailbox_email: str,
    mailbox_password: str,
    recipient_email: str,
    sent_after: float,
) -> str | None:
    """单次 IMAP 扫描，取发送时间之后、收件人匹配的最新蜂巢验证码。"""
    mailbox_email = (mailbox_email or "").strip()
    mailbox_password = (mailbox_password or "").strip()
    recipient_email = (recipient_email or "").strip()
    if not mailbox_email or not mailbox_password:
        raise ValueError("mailbox_email 与 mailbox_password 不能为空")

    host = _imap_host_for_email(mailbox_email)
    mail = imaplib.IMAP4_SSL(host, timeout=20)
    try:
        mail.login(mailbox_email, mailbox_password)
        found = _scan_mailbox_for_otp(
            mail,
            recipient_email=recipient_email,
            mailbox_email=mailbox_email,
            sent_after=sent_after,
        )
        return found[0] if found else None
    finally:
        try:
            mail.logout()
        except Exception:  # noqa: BLE001
            pass


def fetch_otp_with_resend(
    *,
    mailbox_email: str,
    mailbox_password: str,
    recipient_email: str,
    sent_after: float,
    resend_code: Callable[[], float],
    poll_interval: float | None = None,
    wait_per_send: float | None = None,
    max_resends: int | None = None,
) -> str:
    """
    轮询 OTP 邮箱：每 poll_interval 秒查一次，wait_per_send 内未收到则 resend_code() 重发。

    resend_code 应触发 iHive 发验证码并返回新的 sent_after 时间戳。
    """
    poll_interval = float(
        poll_interval if poll_interval is not None else os.environ.get("OTP_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)
    )
    wait_per_send = float(
        wait_per_send if wait_per_send is not None else os.environ.get("OTP_WAIT_PER_SEND", DEFAULT_WAIT_PER_SEND)
    )
    max_resends = int(
        max_resends if max_resends is not None else os.environ.get("OTP_MAX_RESENDS", DEFAULT_MAX_RESENDS)
    )

    send_round = 0
    current_sent_after = sent_after
    last_error = ""

    while send_round <= max_resends:
        send_round += 1
        deadline = time.time() + wait_per_send
        attempt = 0
        print(
            f"[OTP] 第{send_round}轮等待验证码 recipient={recipient_email} "
            f"mailbox={mailbox_email} sent_after={time.strftime('%H:%M:%S', time.localtime(current_sent_after))}",
            flush=True,
        )
        while time.time() < deadline:
            attempt += 1
            print(
                f"[OTP] 第{attempt}次连接 {mailbox_email} 扫描验证码…",
                flush=True,
            )
            try:
                otp = try_fetch_latest_otp(
                    mailbox_email=mailbox_email,
                    mailbox_password=mailbox_password,
                    recipient_email=recipient_email,
                    sent_after=current_sent_after,
                )
                if otp:
                    print(f"[OTP] 第{attempt}次查询命中验证码", flush=True)
                    return otp
                print(
                    f"[OTP] 第{attempt}次未找到蜂巢验证码（收件人={recipient_email}），"
                    f"{poll_interval}s 后刷新",
                    flush=True,
                )
            except imaplib.IMAP4.error as exc:
                last_error = str(exc)
                _raise_if_imap_auth_blocked(last_error, mailbox_email)
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                _raise_if_imap_auth_blocked(last_error, mailbox_email)
            time.sleep(poll_interval)

        if send_round > max_resends:
            break
        print(f"[OTP] {wait_per_send:.0f}s 内未收到验证码，触发第{send_round + 1}次发码", flush=True)
        current_sent_after = resend_code()

    hint = f"; last_error={last_error}" if last_error else ""
    raise TimeoutError(
        f"在 {max_resends + 1} 轮发码后仍未从 {mailbox_email} 找到收件人为 {recipient_email} 的蜂巢验证码{hint}。"
        f" 可改用 OTP_CODE=验证码"
    )


def fetch_otp_from_email(
    *,
    mailbox_email: str,
    mailbox_password: str,
    recipient_email: str = "",
    from_address: str = "support@zelto.jp",
    timeout: float = 120.0,
    poll_interval: float = 5.0,
    sent_after: float | None = None,
) -> str:
    """兼容旧接口：单次轮询直到 timeout。"""
    _ = from_address
    if sent_after is None:
        sent_after = time.time() - 30
    recipient = recipient_email or mailbox_email
    deadline = time.time() + timeout
    while time.time() < deadline:
        otp = try_fetch_latest_otp(
            mailbox_email=mailbox_email,
            mailbox_password=mailbox_password,
            recipient_email=recipient,
            sent_after=sent_after,
        )
        if otp:
            return otp
        time.sleep(poll_interval)
    raise TimeoutError(
        f"在 {timeout}s 内未从 {mailbox_email} 找到收件人为 {recipient} 的蜂巢验证码"
    )


def _raise_if_imap_auth_blocked(message: str, mailbox_email: str) -> None:
    lower = (message or "").lower()
    auth_markers = (
        "authentication",
        "invalid credentials",
        "basic authentication is disabled",
        "application-specific password required",
        "authenticate failed",
        "login failed",
    )
    if any(m in lower for m in auth_markers):
        domain = mailbox_email.split("@")[-1].lower()
        tips = "请设置 OTP_CODE=验证码，或检查 Gmail 应用专用密码。"
        if domain in {"outlook.com", "hotmail.com", "live.com"}:
            tips = "Outlook 不支持 IMAP 密码登录；请用 OTP_MAILBOX_EMAIL 指定的 Gmail 代收。"
        raise RuntimeError(f"IMAP 登录失败 ({mailbox_email}): {message}. {tips}") from None


OUTLOOK_DOMAINS = frozenset({"outlook.com", "hotmail.com", "live.com", "office365.com"})


def is_outlook_login_email(email: str) -> bool:
    domain = (email or "").split("@", 1)[-1].lower()
    return domain in OUTLOOK_DOMAINS


def resolve_otp_mailbox_for_account(
    account: Any,
    *,
    xlsx_path: str | None = None,
    sheet_name: str = "pre_data",
) -> tuple[str, str, str]:
    """
    解析读验证码用的 IMAP 邮箱。

    - Gmail 等：登录账号自己的邮箱 + Password
    - Outlook：登录 a16621325482@gmail.com 代收（仅扫「蜂巢」标签），按收件人=Outlook 地址过滤
    - 本号登录 a16621325482@gmail.com：全量扫 Important 等文件夹
    """
    recipient = (account.login_account or account.user_email or "").strip()
    if is_outlook_login_email(recipient):
        mailbox, pwd = resolve_otp_mailbox_credentials(xlsx_path=xlsx_path, sheet_name=sheet_name)
        return mailbox, pwd, recipient

    mailbox = recipient
    pwd = (account.password or "").strip()
    if not pwd:
        raise ValueError(
            f"Gmail 账号 {account.user_name!r} ({mailbox}) 需在 pre_data 填写 Password（应用专用密码）"
        )
    return mailbox, pwd, recipient


def resolve_otp_mailbox_credentials(
    *,
    xlsx_path: str | None = None,
    sheet_name: str = "pre_data",
) -> tuple[str, str]:
    """从 pre_data 读取 OTP 代收邮箱（默认 a16621325482@gmail.com）的凭据。"""
    from excel_tool import get_accounts, DATA_XLSX_PATH

    target = otp_mailbox_email()
    path = xlsx_path or DATA_XLSX_PATH
    for account in get_accounts(path, sheet_name=sheet_name):
        if account.user_email.lower() == target:
            if not account.password:
                raise ValueError(f"OTP 代收邮箱 {target} 缺少 Password（应用专用密码）")
            return account.user_email, account.password
    raise ValueError(f"pre_data 中未找到 OTP 代收邮箱 {target!r}")
