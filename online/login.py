import json
import os
import re
import subprocess
import sys
import time
import unittest
import uuid
from typing import Any, Dict, List, Optional, Tuple

from excel_tool import DATA_XLSX_PATH, Account, get_accounts, get_account_from_data_csv
from env_config import get_profile, saas_api_url
from email_otp import (
    DEFAULT_WAIT_PER_SEND,
    fetch_otp_with_resend,
    is_outlook_login_email,
    resolve_otp_mailbox_for_account,
)


ORG_BASE_URL = saas_api_url("test")
im_BASE_URL = "https://test-im-api.oa-test.org"

# ====== 这部分 header / body 来自你贴的 curl（尽量保持一致）======
CLIENT_VERSION = "1.0.162"
DEVICE_ID = "91686C55-2F7F-4910-B8F5-810F566071C79"
DEVICE_NAME = "Anna%E7%9A%84MacBook%20Pro%20(MacBook%20Pro)"
DEVICE_OS = "iOS 26.5"
TIMEZONE = "9"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "iHive/1.0.162 Chrome/146.0.7680.80 Electron/41.0.3 Safari/537.36"
)

COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN",
    "content-type": "application/json",
    "client-version": CLIENT_VERSION,
    "device-id": DEVICE_ID,
    "device-name": DEVICE_NAME,
    "device-os": DEVICE_OS,
    "timezone": TIMEZONE,
    "user-agent": USER_AGENT,
    "x-device-arch": "arm64",
    "sec-ch-ua": '"Not-A.Brand";v="24", "Chromium";v="146"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    # 你给的 curl 里有 priority；有些服务端可能不强依赖，这里仍保留
    "priority": "u=1, i",
}


ORG_COMMON_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN",
    "client-version": "1.0.15",
    "content-type": "application/json",
    "device-id": "0E9E2411-5573-57C0-A375-2C3F8D24F7B3",
    "device-name": "Anna%E7%9A%84MacBook%20Air",
    "device-os": "macOS 26.0.1",
    "priority": "u=1, i",
    "sec-ch-ua": '"Not=A?Brand";v="24", "Chromium";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "timezone": "8",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "oa-saas-desktop/1.0.15 Chrome/140.0.7339.240 Electron/38.4.0 Safari/537.36",
    "x-device-arch": "arm64",
}


def _uuid() -> str:
    return str(uuid.uuid4())


def _to_json_str(payload: Dict[str, Any]) -> str:
    # 确保是 compact JSON，避免 curl/服务端解析问题
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _extract_first_jwt(obj: Any) -> Optional[str]:
    """
    尝试从响应体中找第一个形如 JWT 的字符串，避免你在 curl 里手工拼 token。
    """
    if isinstance(obj, str) and re.match(r"^eyJ[A-Za-z0-9_-]*\.", obj):
        return obj
    if isinstance(obj, dict):
        for v in obj.values():
            found = _extract_first_jwt(v)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _extract_first_jwt(item)
            if found:
                return found
    return None


def _extract_access_token_from_login_resp(resp: Any) -> Optional[str]:
    """
    从 login_resp 中提取 access_token：
    - 优先读取字段: access_token / accessToken / token
    - 如果是 authorization: "Bearer xxx" 则解析 xxx
    - 若仍提取不到，才回退到 JWT 提取（兼容老返回结构）
    """
    def _clean_bearer(v: str) -> str:
        v = v.strip()
        if v.lower().startswith("bearer "):
            return v.split(" ", 1)[1].strip()
        return v

    if isinstance(resp, str):
        # 有些接口直接返回 token/JWT
        if re.match(r"^eyJ[A-Za-z0-9_-]*\.", resp.strip()):
            return resp.strip()
        return _clean_bearer(resp)

    if not isinstance(resp, dict):
        return _extract_first_jwt(resp)

    # 1) 直接字段命中
    direct_keys = ["access_token", "accessToken", "token", "Token", "authorization", "Authorization"]
    for k in direct_keys:
        v = resp.get(k)
        if isinstance(v, str) and v.strip():
            return _clean_bearer(v)

    # 2) 常见嵌套 data/result
    for nested_key in ("data", "result", "Result"):
        nested = resp.get(nested_key)
        if nested is None:
            continue
        nested_token = _extract_access_token_from_login_resp(nested)
        if nested_token:
            return nested_token

    # 3) 兜底：递归查找常见字段名
    keys_to_find = {"access_token", "accessToken", "token", "authorization", "Authorization"}
    stack: List[Any] = [resp]
    steps = 0
    while stack and steps < 2000:
        cur = stack.pop()
        steps += 1
        if isinstance(cur, dict):
            for k, v in cur.items():
                lk = str(k)
                if lk in keys_to_find and isinstance(v, str) and v.strip():
                    return _clean_bearer(v)
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            for v in cur:
                if isinstance(v, (dict, list)):
                    stack.append(v)

    return _extract_first_jwt(resp)


def _api_ok(resp_json: Dict[str, Any]) -> Tuple[bool, str]:
    """
    通用断言：兼容 code/success/status 等常见字段。
    """
    if not isinstance(resp_json, dict):
        return False, "response is not a dict"

    # 常见：{"code":0,"message":"..."}
    if "code" in resp_json:
        code = resp_json.get("code")
        if isinstance(code, int) and code != 0:
            return False, f"code != 0: {code}, message={resp_json.get('message')}"
        if isinstance(code, str):
            try:
                code_i = int(code)
                if code_i != 0:
                    return False, f"code != 0: {code_i}, message={resp_json.get('message')}"
            except ValueError:
                # 不是数字时不强断言
                pass

    # 常见：{"success":true}
    if "success" in resp_json and isinstance(resp_json["success"], bool):
        if not resp_json["success"]:
            return False, f"success is false, message={resp_json.get('message')}"

    # 兜底：若有 message 且 code/status 不存在，不强判定
    if "data" in resp_json or resp_json:
        return True, ""

    return False, "empty response"


def _post_json_curl(
    url: str, payload: Dict[str, Any], *, headers: Dict[str, str], timeout_s: int = 30
) -> Dict[str, Any]:
    cmd: List[str] = ["curl", "-sS", "--fail-with-body", "-X", "POST", url]
    for k, v in headers.items():
        cmd.extend(["-H", f"{k}: {v}"])
    cmd.extend(["--data-raw", _to_json_str(payload)])

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    stdout = proc.stdout.strip() if proc.stdout else ""
    stderr = proc.stderr.strip() if proc.stderr else ""

    if not stdout:
        raise RuntimeError(f"empty response: returncode={proc.returncode}, stderr={stderr}")

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"response is not valid json: {stdout[:500]}, stderr={stderr}")


def _extract_first_str_field(d: Any, keys: List[str]) -> Optional[str]:
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_org_tokens_and_userid(
    org_login_resp: Dict[str, Any]
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    从公司登录（org/login）接口返回中提取：
    - token_api.access_token（业务 API token）
    - token_im.access_token（兼容 tokenIm）
    - user_id（兼容 userid / userId / user_id 等）
    """
    token_api_access: Optional[str] = None
    token_im_access: Optional[str] = None
    user_id: Optional[str] = None

    # 优先按你提供的稳定结构提取：
    # {
    #   "code": 0,
    #   "data": {
    #     "token_im": {"access_token": "..."},
    #     "user_id": "..."
    #   }
    # }
    data = org_login_resp.get("data") if isinstance(org_login_resp, dict) else None
    if isinstance(data, dict):
        token_api = data.get("token_api") or data.get("tokenApi")
        if isinstance(token_api, dict):
            token_api_access = _extract_first_str_field(token_api, ["access_token", "accessToken"])
        token_im = data.get("token_im") or data.get("tokenIm")
        if isinstance(token_im, dict):
            token_im_access = _extract_first_str_field(token_im, ["access_token", "accessToken"])
        user_id = _extract_first_str_field(data, ["user_id", "userid", "userId", "UserId", "UserID"])

    # 如果取不到，再走兼容兜底（更宽松字段名）
    if token_api_access and token_im_access and user_id:
        return token_api_access, token_im_access, user_id

    def _token_api_from(obj: Any) -> Optional[str]:
        if not isinstance(obj, dict):
            return None
        for key in ("token_api", "tokenApi"):
            ta = obj.get(key)
            if isinstance(ta, dict):
                t = _extract_first_str_field(ta, ["access_token", "accessToken"])
                if t:
                    return t
        return None

    def _token_im_from(obj: Any) -> Optional[str]:
        if not isinstance(obj, dict):
            return None
        for key in ("token_im", "tokenIm"):
            ti = obj.get(key)
            if isinstance(ti, dict):
                t = _extract_first_str_field(ti, ["access_token", "accessToken"])
                if t:
                    return t
        return None

    def _userid_from(obj: Any) -> Optional[str]:
        if not isinstance(obj, dict):
            return None
        return _extract_first_str_field(
            obj,
            ["userid", "userId", "user_id", "UserId", "UserID"],
        )

    # 优先：根 / data 下直接字段
    for root in (org_login_resp, org_login_resp.get("data") if isinstance(org_login_resp.get("data"), dict) else None):
        if root is None:
            continue
        if not token_api_access:
            token_api_access = _token_api_from(root)
        if not token_im_access:
            token_im_access = _token_im_from(root)
        if not user_id:
            user_id = _userid_from(root)

    # 兜底：递归查找 token_api/token_im 与 user_id
    if not token_api_access or not token_im_access or not user_id:
        stack: List[Any] = [org_login_resp]
        steps = 0
        while stack and steps < 3000:
            cur = stack.pop()
            steps += 1
            if isinstance(cur, dict):
                if not token_api_access:
                    token_api_access = _token_api_from(cur)
                if not token_im_access:
                    token_im_access = _token_im_from(cur)
                if not user_id:
                    user_id = _userid_from(cur)
                if token_api_access and token_im_access and user_id:
                    break
                for v in cur.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(cur, list):
                for v in cur:
                    if isinstance(v, (dict, list)):
                        stack.append(v)

    return token_api_access, token_im_access, user_id


def org_login(access_token: str, tenant_id: str, company_id: str, platform: int = 1) -> Dict[str, Any]:
    """
    对应你提供的 curl：POST /api/oa/v1/idp/org/login
    """
    url = f"{ORG_BASE_URL}/api/oa/v1/idp/org/login"
    operationid = _uuid()
    headers = dict(ORG_COMMON_HEADERS)
    headers["authorization"] = f"Bearer {access_token}"
    headers["x-request-id"] = operationid

    payload = {
        "tenant_id": tenant_id,
        "company_id": company_id,
        "platform": platform,
    }

    resp_json = _post_json_curl(url, payload, headers=headers)
    ok, msg = _api_ok(resp_json)
    assert ok, f"org_login failed: {msg}. resp={resp_json}"
    return resp_json


class SaasApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def _build_headers(self, operationid: str, x_request_id: str) -> Dict[str, str]:
        h = dict(COMMON_HEADERS)
        h["operationid"] = operationid
        h["x-request-id"] = x_request_id
        return h

    def _post_json(
        self, path: str, payload: Dict[str, Any], *, headers: Dict[str, str], timeout_s: int = 30
    ) -> Tuple[int, Dict[str, Any], str]:
        url = f"{self.base_url}{path}"
        cmd: List[str] = ["curl", "-sS", "--fail-with-body", "-X", "POST", url]
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
        cmd.extend(["--data-raw", _to_json_str(payload)])

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        stdout = proc.stdout.strip() if proc.stdout else ""
        stderr = proc.stderr.strip() if proc.stderr else ""

        # curl 非 2xx 且 --fail-with-body 会直接返回 non-zero 并把 body 写到 stdout
        # 我们这里尽量把 stdout 当作 json 解析
        status_code = proc.returncode
        if proc.returncode != 0 and stderr:
            # 注意：这里 returncode 不是 http_code，所以我们只用它来做兜底提示
            pass

        if not stdout:
            raise RuntimeError(f"empty response, returncode={proc.returncode}, stderr={stderr}")

        try:
            resp_json = json.loads(stdout)
        except json.JSONDecodeError:
            # 仍返回原文，便于定位服务端返回了什么
            raise RuntimeError(
                f"response is not valid json: {stdout[:500]}, returncode={proc.returncode}, stderr={stderr}"
            )
        return status_code, resp_json, stdout

    def send_code(self, login_account: str, *, phone_area_code: str, platform: int = 4) -> Dict[str, Any]:
        operationid = _uuid()
        x_request_id = operationid
        headers = self._build_headers(operationid, x_request_id)
        payload = {
            "used_for": 1,
            "type": 1,
            "login_account": login_account,
            "phone_area_code": phone_area_code,
            "platform": platform,
        }
        _, resp_json, _ = self._post_json("/api/oa/v1/idp/code/send", payload, headers=headers)
        return resp_json

    def login_by_code(
        self,
        login_account: str,
        *,
        phone_area_code: str,
        code: str,
        platform: int = 1,
        keep_login: int = 1,
    ) -> Dict[str, Any]:
        operationid = _uuid()
        x_request_id = operationid
        headers = self._build_headers(operationid, x_request_id)
        payload = {
            "type": 1,
            "login_account": login_account,
            "phone_area_code": phone_area_code,
            "platform": platform,
            "code": code,
            "password": "",
            "keep_login": keep_login,
        }
        _, resp_json, _ = self._post_json("/api/oa/v1/idp/user/login", payload, headers=headers)
        return resp_json

    def get_joined_company_list(
        self,
        *,
        bearer_token: str,
        token_header: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        operationid = _uuid()
        x_request_id = operationid
        headers = self._build_headers(operationid, x_request_id)
        headers["authorization"] = f"Bearer {bearer_token}"
        headers["token"] = token_header
        payload = {"page": page, "page_size": page_size}
        _, resp_json, _ = self._post_json(
            "/api/oa/v1/idp/company/joined/list",
            payload,
            headers=headers,
        )
        return resp_json

def _send_code_too_frequent(resp: Dict[str, Any]) -> bool:
    codes = {
        str(resp.get("code") or ""),
        str(resp.get("businessCode") or ""),
    }
    if "3012003" in codes:
        return True
    for key in ("message", "msg", "businessMsg"):
        text = str(resp.get(key) or "")
        if "过于频繁" in text or "请稍后" in text:
            return True
    return False


def _parse_retry_wait_seconds(message: str, default: int = 60) -> int:
    m = re.search(r"(?:等待|wait)\s*(\d+)\s*秒", message, re.I)
    if m:
        return max(int(m.group(1)), 1)
    m = re.search(r"(\d+)\s*秒(?:后|以内)?(?:重试|再试|发送)", message)
    if m:
        return max(int(m.group(1)), 1)
    return default


def _send_verification_code(
    client: SaasApiClient,
    login_account: str,
    *,
    phone_area_code: str,
    log: Any,
    resp_summary: Any,
) -> tuple[Dict[str, Any], float]:
    max_attempts = int(os.environ.get("SEND_CODE_MAX_ATTEMPTS", "8"))
    default_wait_s = int(os.environ.get("SEND_CODE_RETRY_WAIT_SECONDS", "60"))
    last_resp: Dict[str, Any] = {}
    for attempt in range(1, max_attempts + 1):
        last_resp = client.send_code(login_account, phone_area_code=phone_area_code)
        ok, msg = _api_ok(last_resp)
        if ok:
            sent_at = time.time()
            log(f"发送验证码响应: {resp_summary(last_resp)}")
            return last_resp, sent_at
        message = str(
            last_resp.get("message")
            or last_resp.get("msg")
            or last_resp.get("businessMsg")
            or ""
        )
        if _send_code_too_frequent(last_resp) and attempt < max_attempts:
            retry_wait_s = _parse_retry_wait_seconds(message, default_wait_s)
            log(f"发送验证码过于频繁，等待{retry_wait_s}秒后重试 ({attempt}/{max_attempts})")
            time.sleep(retry_wait_s)
            log(f"等待{retry_wait_s}秒结束，重新发送验证码 ({attempt + 1}/{max_attempts})")
            continue
        raise AssertionError(f"send_code failed: {msg}. resp={last_resp}")
    raise AssertionError(f"send_code failed after {max_attempts} attempts: resp={last_resp}")


def _resolve_otp_code(
    account: Account,
    *,
    client: SaasApiClient | None = None,
    phone_area_code: str = "",
    after_send: bool = False,
    sent_after: float | None = None,
) -> str:
    env_otp = (os.environ.get("OTP_CODE") or "").strip()
    if env_otp:
        return env_otp

    profile = get_profile()
    if profile.otp_mode == "fixed":
        return profile.default_otp or "123456"

    if not after_send:
        return ""

    if client is None:
        raise ValueError("pre 环境读取验证码需要 SaasApiClient 实例")

    mailbox, mailbox_pwd, recipient = resolve_otp_mailbox_for_account(account)
    sent_after_ts = float(os.environ.get("OTP_SENT_AFTER", "0") or "0") or sent_after or time.time()
    wait_s = float(os.environ.get("SEND_CODE_WAIT_SECONDS", "2"))

    via = "Outlook 代收" if is_outlook_login_email(account.login_account) else "本邮箱"
    print(
        f"[LOGIN] {via} {mailbox} 读取蜂巢验证码，收件人={recipient}，发码时间之后且最新一封",
        flush=True,
    )

    wait_per_send = float(os.environ.get("OTP_WAIT_PER_SEND", DEFAULT_WAIT_PER_SEND))

    def _resend() -> float:
        print(f"[LOGIN] {wait_per_send:.0f}s 内未收到匹配验证码，重新发送 iHive 验证码", flush=True)
        _, sent_at = _send_verification_code(
            client,
            recipient,
            phone_area_code=phone_area_code,
            log=lambda m: print(f"[LOGIN] {time.strftime('%Y-%m-%d %H:%M:%S')} {m}"),
            resp_summary=lambda r: str(r.get("code")),
        )
        time.sleep(wait_s)
        return sent_at

    try:
        return fetch_otp_with_resend(
            mailbox_email=mailbox,
            mailbox_password=mailbox_pwd,
            recipient_email=recipient,
            sent_after=sent_after_ts,
            resend_code=_resend,
        )
    except (TimeoutError, RuntimeError) as exc:
        prompt = os.environ.get("OTP_CODE_PROMPT", "1").strip().lower() not in ("0", "false", "no")
        if prompt and sys.stdin.isatty():
            manual = input(f"[LOGIN] IMAP 未取到验证码 ({exc}); 请粘贴验证码: ").strip()
            if manual:
                return manual
        raise


def login_flow_for_account(
    client: SaasApiClient,
    *,
    account: Account,
    otp_code: str = "",
    phone_area_code: str,
    run_send_code: bool = True,
) -> Dict[str, Any]:
    """
    登录并拉取租户列表：只依赖已选定的 account。

    返回：
    - `send_code_resp`: 发送验证码接口返回（run_send_code=False 时为 None）
    - `login_resp`: 登录接口返回
    - `joined_resp`: 获取租户列表接口返回
    """
    def _log(message: str) -> None:
        # unittest/stdout 场景下直接 print 即可
        print(f"[LOGIN] {time.strftime('%Y-%m-%d %H:%M:%S')} {message}")

    def _resp_summary(resp: Optional[Dict[str, Any]]) -> str:
        if not resp:
            return "None"
        if not isinstance(resp, dict):
            return str(resp)
        code = resp.get("code")
        message = resp.get("message") or resp.get("msg")
        success = resp.get("success")
        parts: List[str] = []
        if code is not None:
            parts.append(f"code={code}")
        if success is not None:
            parts.append(f"success={success}")
        if message:
            parts.append(f"message={message}")
        if not parts:
            return f"keys={list(resp.keys())}"
        return " ".join(parts)

    _log(f"登录邮箱{account.login_account}")

    send_started_at: float | None = None
    send_resp: Optional[Dict[str, Any]] = None
    if run_send_code:
        _log("发送验证码")
        send_resp, send_started_at = _send_verification_code(
            client,
            account.login_account,
            phone_area_code=phone_area_code,
            log=_log,
            resp_summary=_resp_summary,
        )
        wait_s = float(os.environ.get("SEND_CODE_WAIT_SECONDS", "2"))
        time.sleep(wait_s)

    code = (otp_code or "").strip()
    if not code:
        code = _resolve_otp_code(
            account,
            client=client,
            phone_area_code=phone_area_code,
            after_send=run_send_code,
            sent_after=send_started_at,
        )
    if not code:
        code = _resolve_otp_code(account, after_send=False) or "123456"

    login_resp = client.login_by_code(
        account.login_account,
        phone_area_code=phone_area_code,
        code=code,
    )
    ok, msg = _api_ok(login_resp)
    assert ok, f"login failed: {msg}. resp={login_resp}"
    _log(f"用户{account.user_name}登录成功; 登录响应: {_resp_summary(login_resp)}")

    first_jwt = _extract_first_jwt(login_resp)
    assert first_jwt is not None, f"cannot extract jwt from login response: {login_resp}"

    # 有的服务端 authorization 与 token 可能是同一个 jwt
    joined_resp = client.get_joined_company_list(
        bearer_token=first_jwt,
        token_header=first_jwt,
        page=1,
        page_size=50,
    )
    ok, msg = _api_ok(joined_resp)
    assert ok, f"get_joined_company_list failed: {msg}. resp={joined_resp}"
    _log(f"获取租户列表成功; 租户响应: {_resp_summary(joined_resp)}")
    return {"send_code_resp": send_resp, "login_resp": login_resp, "joined_resp": joined_resp}


def _extract_company_from_joined_resp(joined_resp: Dict[str, Any], company_name: str) -> Optional[Dict[str, Any]]:
    """
    兼容 joined/list 接口返回结构不稳定的情况：
    尝试在返回 JSON 中查找“CompanyName/公司名称/name”等字段等于 company_name 的对象。
    """

    def _get_field(d: Dict[str, Any], keys: List[str]) -> Optional[str]:
        for k in keys:
            v = d.get(k)
            if isinstance(v, str) and v.strip():
                return v
        return None

    def _matches(d: Dict[str, Any]) -> bool:
        candidate = _get_field(
            d,
            keys=[
                "CompanyName",
                "companyName",
                "company_name",
                "Company",
                "name",
            ],
        )
        return isinstance(candidate, str) and candidate.strip() == company_name.strip()

    # 优先检查常见路径 data/list
    data = joined_resp.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and _matches(item):
                return item
    if isinstance(data, dict):
        for k in ("list", "rows", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict) and _matches(item):
                        return item

    # 兜底：在小范围内递归查找列表中的 dict
    stack: List[Any] = [joined_resp]
    steps = 0
    while stack and steps < 5000:
        cur = stack.pop()
        steps += 1
        if isinstance(cur, dict):
            if _matches(cur):
                return cur
            for v in cur.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            for v in cur:
                if isinstance(v, (dict, list)):
                    stack.append(v)
    return None


def _joined_company_names(joined_resp: Dict[str, Any]) -> List[str]:
    names: List[str] = []
    seen = set()
    stack: List[Any] = [joined_resp]
    steps = 0
    while stack and steps < 5000:
        cur = stack.pop()
        steps += 1
        if isinstance(cur, dict):
            for key in ("CompanyName", "companyName", "company_name"):
                value = cur.get(key)
                if isinstance(value, str) and value.strip() and value.strip() not in seen:
                    seen.add(value.strip())
                    names.append(value.strip())
                    break
            for value in cur.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(cur, list):
            stack.extend(item for item in cur if isinstance(item, (dict, list)))
    return names


def switch_company(
    *,
    access_token: str,
    company_name: str,
    joined_resp: Optional[Dict[str, Any]] = None,
    platform: int = 1,
) -> Dict[str, Any]:
    """同一登录态下切租户：复用 idp access_token，再调 org/login。"""
    if not access_token:
        raise ValueError("switch_company 需要登录阶段的 access_token")
    if joined_resp is None:
        client = SaasApiClient(ORG_BASE_URL)
        joined_resp = client.get_joined_company_list(
            bearer_token=access_token,
            token_header=access_token,
            page=1,
            page_size=50,
        )
        ok, msg = _api_ok(joined_resp)
        assert ok, f"get_joined_company_list failed: {msg}. resp={joined_resp}"

    matched_company = _extract_company_from_joined_resp(joined_resp, company_name)
    if matched_company is None:
        available = _joined_company_names(joined_resp)
        raise ValueError(
            f"cannot find company_name={company_name} in joined list; available={available}"
        )

    tenant_id = _extract_first_str_field(
        matched_company,
        keys=["tenant_id", "TenantId", "tenantId"],
    )
    company_id = _extract_first_str_field(
        matched_company,
        keys=["company_id", "CompanyId", "companyId", "CompanyID", "companyID"],
    )
    if not tenant_id or not company_id:
        raise ValueError(
            f"matched_company missing tenant_id/company_id; tenant_id={tenant_id}, "
            f"company_id={company_id}, keys={list(matched_company.keys())}"
        )

    org_login_resp = org_login(
        access_token=access_token,
        tenant_id=tenant_id,
        company_id=company_id,
        platform=platform,
    )
    token_api_access_token, token_im_access_token, org_userid = _extract_org_tokens_and_userid(
        org_login_resp
    )
    org_code = org_login_resp.get("code")
    org_message = org_login_resp.get("message") or org_login_resp.get("msg")
    print(
        f"[LOGIN] 切租户到 {company_name}; tenant_id={tenant_id} company_id={company_id} "
        f"user_id={org_userid} code={org_code} message={org_message}"
    )
    return {
        "api_token": token_api_access_token,
        "im_token": token_im_access_token,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "user_id": org_userid,
        "company_name": company_name,
        "access_token": access_token,
        "joined_resp": joined_resp,
    }


def login(company_name: str, user_name: str) -> Dict[str, Any]:
    """
    对外可调用的登录方法。

    入参：
    - user_name：data.xlsx 当前环境 sheet 的 `UserName`
    - company_name：你希望找到/断言的 CompanyName

    返回：
    - send_code_resp
    - login_resp
    - joined_resp
    - matched_company：在 joined_resp 中匹配到的公司对象（找不到则为 None）
    - org_login_resp
    - tenant_id
    - company_id
    - token_im_access_token：从 org_login_resp 中 token_im.access_token 提取（无则为 None）
    - userid：从 org_login_resp 中提取（无则为 None）
    """

    phone_area_code = os.environ.get("PHONE_AREA_CODE", "+81")
    run_send_code = os.environ.get("RUN_SEND_CODE", "1") == "1"

    account = get_account_from_data_csv(DATA_XLSX_PATH, user_name=user_name, company_name=company_name)
    if company_name and account.company_name and account.company_name != company_name:
        raise ValueError(
            f"account.company_name mismatch: account={account.company_name}, expected={company_name}"
        )

    client = SaasApiClient(ORG_BASE_URL)
    resp = login_flow_for_account(
        client,
        account=account,
        phone_area_code=phone_area_code,
        run_send_code=run_send_code,
    )

    matched_company = _extract_company_from_joined_resp(resp["joined_resp"], company_name)
    if matched_company is not None:
        print(f"[LOGIN] 找到公司 {company_name}")
    else:
        print(f"[LOGIN] 未找到公司 {company_name}（返回结构可能不同）")

    if matched_company is None:
        raise ValueError(f"cannot find matched company_name={company_name} in joined_resp")

    tenant_id = _extract_first_str_field(
        matched_company,
        keys=["tenant_id", "TenantId", "tenantId"],
    )
    company_id = _extract_first_str_field(
        matched_company,
        keys=["company_id", "CompanyId", "companyId", "CompanyID", "companyID"],
    )
    if not tenant_id or not company_id:
        raise ValueError(
            f"matched_company missing tenant_id/company_id; tenant_id={tenant_id}, company_id={company_id}, matched_company_keys={list(matched_company.keys())}"
        )

    access_token = _extract_access_token_from_login_resp(resp["login_resp"])
    if not access_token:
        raise ValueError(f"cannot extract access_token from login_resp: {resp['login_resp']}")

    org_login_resp = org_login(
        access_token=access_token,
        tenant_id=tenant_id,
        company_id=company_id,
        platform=1,
    )
    org_code = org_login_resp.get("code")
    org_message = org_login_resp.get("message") or org_login_resp.get("msg")
    token_api_access_token, token_im_access_token, org_userid = _extract_org_tokens_and_userid(org_login_resp)
    print(
        f"[LOGIN] {account.user_name}+{company_name}登录成功; "
        f"tenant_id={tenant_id} company_id={company_id} code={org_code} message={org_message}"
    )

    return {
        **resp,
        # "matched_company": matched_company,
        # "expected_company_name": company_name,
        # "selected_user_role": account.user_role,
        # "selected_user_email": account.user_email,
        # "org_login_resp": org_login_resp,
        # "tenant_id": tenant_id,
        # "company_id": company_id,
        # 公司登录接口返回中提取（见 token_im.access_token、userid）
        "api_token": token_api_access_token,
        "im_token": token_im_access_token,
        "tenant_id": tenant_id,
        "company_id": company_id,
        "user_id": org_userid,
        "access_token": access_token,
        "company_name": company_name,
        "user_name": account.user_name,
    }


def login_with_retry(
    company_name: str,
    user_name: str,
    *,
    max_attempts: int | None = None,
) -> Dict[str, Any]:
    """登录失败时重试；默认最多 2 次（可用 LOGIN_MAX_ATTEMPTS 覆盖）。"""
    attempts = int(
        max_attempts if max_attempts is not None else os.environ.get("LOGIN_MAX_ATTEMPTS", "2")
    )
    last_err: Exception | None = None
    for n in range(1, attempts + 1):
        try:
            return login(company_name, user_name)
        except Exception as exc:
            last_err = exc
            if n < attempts:
                wait_s = float(os.environ.get("LOGIN_RETRY_WAIT_SECONDS", "5"))
                print(
                    f"[LOGIN] {user_name} 第{n}次失败: {exc}; "
                    f"{wait_s:.0f}s 后重试 ({n + 1}/{attempts})",
                    flush=True,
                )
                time.sleep(wait_s)
            else:
                print(
                    f"[LOGIN] {user_name} 已尝试 {attempts} 次仍失败，跳过",
                    flush=True,
                )
    assert last_err is not None
    raise last_err


if __name__ == "__main__":
    print(login(company_name="自动化测试公司", user_name="CEO"))
