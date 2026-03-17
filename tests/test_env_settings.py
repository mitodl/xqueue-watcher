import unittest
from unittest.mock import patch

from xqueue_watcher.env_settings import get_manager_config_from_env
from xqueue_watcher.settings import MANAGER_CONFIG_DEFAULTS


class TestGetManagerConfigFromEnv(unittest.TestCase):
    def test_defaults_when_no_env_vars_set(self):
        with patch.dict("os.environ", {}, clear=False):
            config = get_manager_config_from_env()
        self.assertEqual(config, MANAGER_CONFIG_DEFAULTS)

    def test_poll_time_from_env(self):
        with patch.dict("os.environ", {"XQWATCHER_POLL_TIME": "30"}):
            config = get_manager_config_from_env()
        self.assertEqual(config["POLL_TIME"], 30)

    def test_requests_timeout_from_env(self):
        with patch.dict("os.environ", {"XQWATCHER_REQUESTS_TIMEOUT": "5"}):
            config = get_manager_config_from_env()
        self.assertEqual(config["REQUESTS_TIMEOUT"], 5)

    def test_poll_interval_from_env(self):
        with patch.dict("os.environ", {"XQWATCHER_POLL_INTERVAL": "3"}):
            config = get_manager_config_from_env()
        self.assertEqual(config["POLL_INTERVAL"], 3)

    def test_login_poll_interval_from_env(self):
        with patch.dict("os.environ", {"XQWATCHER_LOGIN_POLL_INTERVAL": "15"}):
            config = get_manager_config_from_env()
        self.assertEqual(config["LOGIN_POLL_INTERVAL"], 15)

    def test_http_basic_auth_from_env(self):
        with patch.dict("os.environ", {"XQWATCHER_HTTP_BASIC_AUTH": "user:secret"}):
            config = get_manager_config_from_env()
        self.assertEqual(config["HTTP_BASIC_AUTH"], "user:secret")

    def test_http_basic_auth_empty_string_returns_none(self):
        with patch.dict("os.environ", {"XQWATCHER_HTTP_BASIC_AUTH": ""}):
            config = get_manager_config_from_env()
        self.assertIsNone(config["HTTP_BASIC_AUTH"])

    def test_follow_client_redirects_true_values(self):
        for truthy in ("true", "True", "TRUE", "1", "yes", "YES"):
            with self.subTest(value=truthy):
                with patch.dict("os.environ", {"XQWATCHER_FOLLOW_CLIENT_REDIRECTS": truthy}):
                    config = get_manager_config_from_env()
                self.assertTrue(config["FOLLOW_CLIENT_REDIRECTS"])

    def test_follow_client_redirects_false_values(self):
        for falsy in ("false", "False", "FALSE", "0", "no", "NO"):
            with self.subTest(value=falsy):
                with patch.dict("os.environ", {"XQWATCHER_FOLLOW_CLIENT_REDIRECTS": falsy}):
                    config = get_manager_config_from_env()
                self.assertFalse(config["FOLLOW_CLIENT_REDIRECTS"])

    def test_follow_client_redirects_default_is_false(self):
        with patch.dict("os.environ", {}, clear=False):
            config = get_manager_config_from_env()
        self.assertFalse(config["FOLLOW_CLIENT_REDIRECTS"])

    def test_all_env_vars_together(self):
        env = {
            "XQWATCHER_HTTP_BASIC_AUTH": "admin:pass",
            "XQWATCHER_POLL_TIME": "20",
            "XQWATCHER_REQUESTS_TIMEOUT": "3",
            "XQWATCHER_POLL_INTERVAL": "2",
            "XQWATCHER_LOGIN_POLL_INTERVAL": "10",
            "XQWATCHER_FOLLOW_CLIENT_REDIRECTS": "true",
        }
        with patch.dict("os.environ", env):
            config = get_manager_config_from_env()
        self.assertEqual(config["HTTP_BASIC_AUTH"], "admin:pass")
        self.assertEqual(config["POLL_TIME"], 20)
        self.assertEqual(config["REQUESTS_TIMEOUT"], 3)
        self.assertEqual(config["POLL_INTERVAL"], 2)
        self.assertEqual(config["LOGIN_POLL_INTERVAL"], 10)
        self.assertTrue(config["FOLLOW_CLIENT_REDIRECTS"])

    def test_returns_all_expected_keys(self):
        config = get_manager_config_from_env()
        self.assertEqual(set(config.keys()), set(MANAGER_CONFIG_DEFAULTS.keys()))
