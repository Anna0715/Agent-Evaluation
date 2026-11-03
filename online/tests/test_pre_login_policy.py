"""Offline policy regressions: synthetic values only; no mailbox connections."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from unittest.mock import Mock
from types import SimpleNamespace
import sys


spec = importlib.util.spec_from_file_location(
    "policy_email_otp", Path(__file__).resolve().parents[1] / "email_otp.py"
)
otp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(otp)


class MailboxPasswordPolicyTests(unittest.TestCase):
    def test_unicode_whitespace_is_removed_in_memory(self):
        original = "abcd\u00a0efgh\u2003ijkl\u202fmnop"
        self.assertEqual(
            otp.normalize_mailbox_password("synthetic@gmail.com", original),
            "abcdefghijklmnop",
        )
        self.assertIn("\u00a0", original)

    def test_non_gmail_password_is_unchanged(self):
        original = " synthetic ordinary password "
        self.assertEqual(otp.normalize_mailbox_password("synthetic@example.invalid", original), original)

    def test_invalid_configuration_fails_before_network_or_resend(self):
        for value in ("", "synthetic-secret", "abcdefghijklmno1", "abcdefghijklmnoé"):
            with self.subTest(kind=len(value)):
                with patch.object(otp.imaplib, "IMAP4_SSL") as network:
                    with patch.object(otp, "try_fetch_latest_otp") as fetch:
                        from unittest.mock import Mock
                        resend = Mock()
                        with self.assertRaises(otp.MailboxConfigurationError) as caught:
                            otp.fetch_otp_with_resend(
                                mailbox_email="synthetic@gmail.com",
                                mailbox_password=value,
                                recipient_email="recipient@example.invalid",
                                sent_after=100,
                                resend_code=resend,
                            )
                        self.assertEqual(str(caught.exception),
                            "GMAIL_APP_PASSWORD_CONFIG: Password2 must contain 16 ASCII letters")
                        network.assert_not_called()
                        fetch.assert_not_called()
                        resend.assert_not_called()


class MailboxRoutingTests(unittest.TestCase):
    def test_proxy_folder_uses_imap_modified_utf7(self):
        mail = Mock()
        mail.select.return_value = ("OK", [])
        self.assertTrue(otp._select_imap_folder(mail, "蜂巢"))
        mail.select.assert_called_once_with("&hwJd4g-")
        self.assertEqual(otp._imap_folder_name("A&B"), "A&-B")
        self.assertEqual(otp._imap_folder_name("INBOX"), "INBOX")

    def account(self, name="annaz", email="recipient@example.invalid", password="saas-only", mailbox_password=""):
        return SimpleNamespace(user_name=name, user_email=email, login_account=email,
                               password=password, mailbox_password=mailbox_password)

    def test_annaz_uses_shared_entry_with_fixed_target(self):
        account = self.account()
        with patch("env_config.get_profile", return_value=SimpleNamespace(name="pre")), \
             patch.object(otp, "otp_mailbox_email", return_value="override@example.invalid") as override, \
             patch.object(otp, "resolve_otp_mailbox_credentials", return_value=("a16621325482@gmail.com", "abcdefghijklmnop")) as shared:
            self.assertEqual(otp.resolve_otp_mailbox_for_account(account),
                             ("a16621325482@gmail.com", "abcdefghijklmnop", account.login_account))
            shared.assert_called_once_with(xlsx_path=None, sheet_name="pre_data", target_mailbox="a16621325482@gmail.com")
            override.assert_not_called()

    def test_multiple_company_rows_keep_first_selected_source(self):
        rows = [self.account(email="a16621325482@gmail.com", mailbox_password="abcd efgh ijkl mnop"),
                self.account(email="a16621325482@gmail.com", mailbox_password="ponmlkjihgfedcba")]
        with patch("excel_tool.get_accounts", return_value=rows) as getter:
            self.assertEqual(otp.resolve_otp_mailbox_credentials(xlsx_path="synthetic.xlsx", target_mailbox="a16621325482@gmail.com"),
                             ("a16621325482@gmail.com", "abcdefghijklmnop"))
            getter.assert_called_once_with("synthetic.xlsx", sheet_name="pre_data")
        self.assertEqual(rows[0].mailbox_password, "abcd efgh ijkl mnop")

    def test_missing_password2_does_not_use_saas_or_second_row(self):
        rows = [self.account(email="a16621325482@gmail.com", password="abcdefghijklmnop"),
                self.account(email="a16621325482@gmail.com", mailbox_password="abcdefghijklmnop")]
        with patch("excel_tool.get_accounts", return_value=rows):
            with self.assertRaises(otp.MailboxConfigurationError) as caught:
                otp.resolve_otp_mailbox_credentials(target_mailbox="a16621325482@gmail.com")
        self.assertEqual(str(caught.exception), "MAILBOX_CONFIG: missing mailbox password")

    def test_anna390_uses_own_account(self):
        account = self.account(name="anna390", email="own@gmail.com", mailbox_password="abcd efgh ijkl mnop")
        with patch("env_config.get_profile", return_value=SimpleNamespace(name="pre")), \
             patch.object(otp, "resolve_otp_mailbox_credentials") as shared:
            self.assertEqual(otp.resolve_otp_mailbox_for_account(account),
                             (account.login_account, "abcdefghijklmnop", account.login_account))
            shared.assert_not_called()
        account.mailbox_password = ""
        with patch("env_config.get_profile", return_value=SimpleNamespace(name="pre")):
            with self.assertRaises(otp.MailboxConfigurationError):
                otp.resolve_otp_mailbox_for_account(account)

    def test_legacy_shared_target_and_outlook_route(self):
        account = self.account(name="ordinary_outlook", email="recipient@outlook.com")
        with patch("env_config.get_profile", return_value=SimpleNamespace(name="pre")), \
             patch.object(otp, "resolve_otp_mailbox_credentials", return_value=("proxy@gmail.com", "abcdefghijklmnop")) as shared:
            self.assertEqual(otp.resolve_otp_mailbox_for_account(account),
                             ("proxy@gmail.com", "abcdefghijklmnop", account.login_account))
            shared.assert_called_once_with(xlsx_path=None, sheet_name="pre_data")
        with patch.object(otp, "otp_mailbox_email", return_value="legacy@gmail.com") as target, \
             patch("excel_tool.get_accounts", return_value=[self.account(email="legacy@gmail.com", mailbox_password="abcdefghijklmnop")]):
            self.assertEqual(otp.resolve_otp_mailbox_credentials()[0], "legacy@gmail.com")
            target.assert_called_once_with()

    def test_preflight_gates_before_first_send(self):
        import login

        class StopAtSend(Exception):
            pass

        cases = [("pre", "", "", True), ("pre", "654321", "", False),
                 ("pre", "", "654321", False), ("test", "", "", False)]
        for profile, explicit, environment, required in cases:
            with self.subTest(profile=profile, explicit=bool(explicit), environment=bool(environment)), \
                 patch.dict(login.os.environ, {"OTP_CODE": environment}), \
                 patch.object(login, "get_profile", return_value=SimpleNamespace(name=profile)), \
                 patch.object(login, "resolve_otp_mailbox_for_account", side_effect=otp.MailboxConfigurationError("MAILBOX_CONFIG: missing mailbox password")) as resolver, \
                 patch.object(login, "_send_verification_code", side_effect=StopAtSend) as send, \
                 patch.object(login, "fetch_otp_with_resend") as fetch:
                client = Mock()
                with self.assertRaises(otp.MailboxConfigurationError if required else StopAtSend):
                    login.login_flow_for_account(client, account=self.account(), otp_code=explicit, phone_area_code="")
                if required:
                    resolver.assert_called_once()
                    send.assert_not_called()
                else:
                    resolver.assert_not_called()
                    send.assert_called_once()
                client.assert_not_called()
                client.login_by_code.assert_not_called()
                fetch.assert_not_called()


class AuthenticationBoundaryTests(unittest.TestCase):
    def test_missing_password_is_sanitized(self):
        import login
        account = SimpleNamespace(password="")
        client = Mock()
        with self.assertRaisesRegex(login.PasswordAuthenticationError,
                                    "^PASSWORD_AUTH: missing_password$"):
            login.password_login_flow_for_account(client, account=account)
        client.password_login_precheck.assert_not_called()

    def test_password_stage_boundaries(self):
        import login
        account = SimpleNamespace(password="synthetic", user_name="synthetic",
                                  login_account="synthetic@example.invalid")
        for scenario in ("email", "unknown", "rejected", "joined", "programming", "success"):
            with self.subTest(scenario=scenario):
                client = Mock()
                method = ("LOGIN_METHOD_EMAIL_CODE" if scenario == "email" else
                          "UNRECOGNIZED" if scenario == "unknown" else "LOGIN_METHOD_PASSWORD")
                client.password_login_precheck.return_value = {"data": {"nextLoginMethod": method}}
                client.get_password_public_key.return_value = {}
                client.login_by_password.return_value = {"ok": scenario != "rejected"}
                client.get_joined_company_list.return_value = {"ok": scenario != "joined"}
                if scenario == "programming":
                    client.password_login_precheck.side_effect = TypeError("synthetic")
                with patch.object(login, "_api_ok", side_effect=lambda r: (r.get("ok", True), "")), \
                     patch.object(login, "_extract_password_public_key", return_value="synthetic"), \
                     patch.object(login, "_encrypt_password_pkcs1_v1_5", return_value="synthetic"), \
                     patch.object(login, "_extract_access_token_from_login_resp", return_value="synthetic"):
                    if scenario in ("email", "rejected"):
                        with self.assertRaises(login.PasswordAuthenticationError):
                            login.password_login_flow_for_account(client, account=account)
                        client.get_joined_company_list.assert_not_called()
                    elif scenario == "success":
                        login.password_login_flow_for_account(client, account=account)
                        client.get_joined_company_list.assert_called_once()
                    else:
                        expected = {"unknown": RuntimeError, "joined": AssertionError,
                                    "programming": TypeError}[scenario]
                        with self.assertRaises(expected) as caught:
                            login.password_login_flow_for_account(client, account=account)
                        self.assertNotIsInstance(caught.exception, login.PasswordAuthenticationError)

    def test_entrypoint_catches_only_classified_failure_once(self):
        import login
        class StopAtOtp(Exception):
            pass
        account = SimpleNamespace(user_name="synthetic", login_account="synthetic@example.invalid",
                                  company_name="Company")
        for error in (login.PasswordAuthenticationError("password_rejected"),
                      RuntimeError("LOGIN_METHOD_EMAIL_CODE"), TypeError("synthetic"),
                      ValueError("postauth")):
            with self.subTest(error=type(error).__name__), \
                 patch.object(login, "get_profile", return_value=SimpleNamespace(name="pre")), \
                 patch.object(login, "pwd_login", side_effect=error), \
                 patch.object(login, "get_account_from_data_csv", return_value=account), \
                 patch.object(login, "SaasApiClient", return_value=Mock()), \
                 patch.object(login, "device_id_for_user", return_value="synthetic"), \
                 patch.object(login, "login_flow_for_account", side_effect=StopAtOtp) as flow:
                if isinstance(error, login.PasswordAuthenticationError):
                    with self.assertRaises(StopAtOtp):
                        login.login("Company", "synthetic")
                    flow.assert_called_once()
                else:
                    with self.assertRaises(type(error)):
                        login.login("Company", "synthetic")
                    flow.assert_not_called()

    def test_missing_pre_otp_never_submits_fixed_code(self):
        import login
        account = SimpleNamespace(user_name="synthetic", login_account="synthetic@example.invalid")
        client = Mock()
        with patch.dict(login.os.environ, {"OTP_CODE": ""}), \
             patch.object(login, "get_profile", return_value=SimpleNamespace(name="pre")), \
             patch.object(login, "resolve_otp_mailbox_for_account", return_value=("synthetic", "synthetic", "synthetic")), \
             patch.object(login, "_resolve_otp_code", return_value=""), \
             patch.object(login, "_send_verification_code") as send, \
             patch.object(login, "fetch_otp_with_resend") as fetch:
            with self.assertRaisesRegex(RuntimeError, "^OTP_AUTH: resolve: unavailable$"):
                login.login_flow_for_account(client, account=account,
                                             phone_area_code="", run_send_code=False)
            client.login_by_code.assert_not_called()
            send.assert_not_called()
            fetch.assert_not_called()

    def test_test_environment_keeps_fixed_fallback(self):
        import login
        class StopAtLogin(Exception):
            pass
        account = SimpleNamespace(user_name="synthetic", login_account="synthetic@example.invalid")
        client = Mock()
        client.login_by_code.side_effect = StopAtLogin
        with patch.object(login, "get_profile", return_value=SimpleNamespace(name="test")), \
             patch.object(login, "_resolve_otp_code", return_value=""), \
             patch.object(login, "resolve_otp_mailbox_for_account") as mailbox:
            with self.assertRaises(StopAtLogin):
                login.login_flow_for_account(client, account=account,
                                             phone_area_code="", run_send_code=False)
            self.assertEqual(client.login_by_code.call_args.kwargs["code"], "123456")
            mailbox.assert_not_called()


class GooglemailAliasTests(unittest.TestCase):
    def test_alias_normalization_and_no_saas_fallback(self):
        for domain in ("gmail.com", "googlemail.com"):
            address = "synthetic@" + domain
            with self.subTest(domain=domain):
                self.assertEqual(otp.normalize_mailbox_password(address, "abcd\u2003efgh ijkl mnop"),
                                 "abcdefghijklmnop")
                with self.assertRaises(otp.MailboxConfigurationError):
                    otp.normalize_mailbox_password(address, "abcdefghijklmno1")
                account = SimpleNamespace(user_name="ordinary", user_email=address,
                                          login_account=address, password="abcdefghijklmnop",
                                          mailbox_password="")
                with patch("env_config.get_profile", return_value=SimpleNamespace(name="pre")):
                    with self.assertRaises(otp.MailboxConfigurationError):
                        otp.resolve_otp_mailbox_for_account(account)
                with patch("excel_tool.get_accounts", return_value=[account]):
                    with self.assertRaises(otp.MailboxConfigurationError):
                        otp.resolve_otp_mailbox_credentials(target_mailbox=address)


if __name__ == "__main__":
    unittest.main()
