"""多环境配置：test / pre。"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = REPO_ROOT / "test_data" / "online"
SCENARIOS_DIR = REPO_ROOT / "scenarios"
TOOLS_DIR = REPO_ROOT / "tools"
ARTIFACTS_REVIEWS_DIR = REPO_ROOT / "artifacts" / "reviews"
ARTIFACTS_SUMMARIES_DIR = REPO_ROOT / "artifacts" / "summaries"
SCHEDULE_DIR = SCRIPT_DIR / "schedule"

for _entry in (SCRIPT_DIR, SCENARIOS_DIR, TOOLS_DIR):
    _path = str(_entry)
    if _path not in sys.path:
        sys.path.insert(0, _path)

ENV_VAR = "REPORT_AGENT_ENV"


@dataclass(frozen=True)
class EnvProfile:
    name: str
    data_sheet: str
    report_data_csv: str
    report_data_xlsx: str
    report_data_dir: str
    saas_api_url: str
    im_api_url: str
    otp_mode: str  # fixed | email
    default_otp: str
    otp_email_from: str
    otp_mailbox_email: str


PROFILES: dict[str, EnvProfile] = {
    "test": EnvProfile(
        name="test",
        data_sheet="test_data",
        report_data_csv="test_report_data.csv",
        report_data_xlsx="test_report_data.xlsx",
        report_data_dir="test_report_data",
        saas_api_url="https://test-saas-api.oa-test.org",
        im_api_url="https://test-im-api.oa-test.org",
        otp_mode="fixed",
        default_otp="123456",
        otp_email_from="support@zelto.jp",
        otp_mailbox_email="",
    ),
    "pre": EnvProfile(
        name="pre",
        data_sheet="pre_data",
        report_data_csv="pre_report_data.csv",
        report_data_xlsx="pre_report_data.xlsx",
        report_data_dir="pre_report_data",
        saas_api_url="https://pre-saas-api.saas-api.org",
        im_api_url="https://pre-im-api.saas-api.org",
        otp_mode="email",
        default_otp="",
        otp_email_from="support@zelto.jp",
        otp_mailbox_email="a16621325482@gmail.com",
    ),
}


def current_env_name() -> str:
    raw = (os.environ.get(ENV_VAR) or "test").strip().lower()
    if raw not in PROFILES:
        raise ValueError(f"unsupported {ENV_VAR}={raw!r}; supported={sorted(PROFILES)}")
    return raw


def get_profile(env: str | None = None) -> EnvProfile:
    name = (env or current_env_name()).strip().lower()
    if name not in PROFILES:
        raise ValueError(f"unsupported env={name!r}; supported={sorted(PROFILES)}")
    return PROFILES[name]


def data_xlsx_path() -> Path:
    return FIXTURES_DIR / "data.xlsx"


def data_sheet_name(env: str | None = None) -> str:
    override = (os.environ.get("REPORT_AGENT_DATA_SHEET") or "").strip()
    if override:
        return override
    return get_profile(env).data_sheet


def report_data_csv(env: str | None = None) -> Path:
    return FIXTURES_DIR / get_profile(env).report_data_csv


def report_data_xlsx(env: str | None = None) -> Path:
    return FIXTURES_DIR / get_profile(env).report_data_xlsx


def report_data_dir(env: str | None = None) -> Path:
    return FIXTURES_DIR / get_profile(env).report_data_dir


def test_case_xlsx_path(env: str | None = None) -> Path:
    return FIXTURES_DIR / "周报追问Agent全面评测用例.xlsx"


def saas_api_url(env: str | None = None) -> str:
    return get_profile(env).saas_api_url.rstrip("/")


def im_api_url(env: str | None = None) -> str:
    return get_profile(env).im_api_url.rstrip("/")


def chat_stream_url(env: str | None = None) -> str:
    return f"{im_api_url(env)}/chat/report/stream"


def reports_list_url(env: str | None = None) -> str:
    return f"{im_api_url(env)}/reports/list"


def reports_create_url(env: str | None = None) -> str:
    return f"{im_api_url(env)}/reports/create"


def reports_detail_url(env: str | None = None) -> str:
    return f"{im_api_url(env)}/reports/detail"


def dataset_version_label(env: str | None = None) -> str:
    p = get_profile(env)
    return f"{p.report_data_csv}@env-{p.name}"


def apply_env(env: str | None = None) -> EnvProfile:
    profile = get_profile(env)
    os.environ[ENV_VAR] = profile.name
    os.environ.setdefault("OTP_CODE", profile.default_otp if profile.otp_mode == "fixed" else "")
    return profile


DATA_XLSX_PATH = str(data_xlsx_path())
DATA_CSV_PATH = DATA_XLSX_PATH
