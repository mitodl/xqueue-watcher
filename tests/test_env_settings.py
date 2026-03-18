import logging
import unittest
from unittest.mock import patch

from xqueue_watcher.env_settings import configure_logging, get_manager_config_from_env
from xqueue_watcher.settings import MANAGER_CONFIG_DEFAULTS


class TestConfigureLogging(unittest.TestCase):
    def tearDown(self):
        # Reset root logger after each test so handlers don't accumulate.
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)

    def test_default_level_is_info(self):
        with patch.dict("os.environ", {}, clear=False):
            configure_logging()
        self.assertEqual(logging.getLogger().level, logging.INFO)

    def test_custom_level_from_env(self):
        with patch.dict("os.environ", {"XQWATCHER_LOG_LEVEL": "DEBUG"}):
            configure_logging()
        self.assertEqual(logging.getLogger().level, logging.DEBUG)

    def test_stdout_handler_installed(self):
        import sys
        with patch.dict("os.environ", {}, clear=False):
            configure_logging()
        handlers = logging.getLogger().handlers
        self.assertEqual(len(handlers), 1)
        self.assertIsInstance(handlers[0], logging.StreamHandler)
        self.assertIs(handlers[0].stream, sys.stdout)

    def test_requests_logger_set_to_warning(self):
        with patch.dict("os.environ", {"XQWATCHER_LOG_LEVEL": "DEBUG"}):
            configure_logging()
        self.assertEqual(logging.getLogger("requests").level, logging.WARNING)
        self.assertEqual(logging.getLogger("urllib3").level, logging.WARNING)

    def test_invalid_level_raises(self):
        with patch.dict("os.environ", {"XQWATCHER_LOG_LEVEL": "NOTLEVEL"}):
            with self.assertRaises(ValueError):
                configure_logging()


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
