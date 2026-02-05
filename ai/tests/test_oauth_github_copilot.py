"""Tests for GitHub Copilot OAuth helpers."""

from pipy_ai.oauth.github_copilot import (
    normalize_domain,
    get_github_copilot_base_url,
)


class TestNormalizeDomain:
    def test_plain_domain(self):
        assert normalize_domain("company.ghe.com") == "company.ghe.com"

    def test_url_with_https(self):
        assert normalize_domain("https://company.ghe.com") == "company.ghe.com"

    def test_url_with_path(self):
        assert normalize_domain("https://company.ghe.com/some/path") == "company.ghe.com"

    def test_empty_string(self):
        assert normalize_domain("") is None

    def test_whitespace_only(self):
        assert normalize_domain("   ") is None


class TestGetBaseUrl:
    def test_default(self):
        url = get_github_copilot_base_url()
        assert url == "https://api.individual.githubcopilot.com"

    def test_with_enterprise_domain(self):
        url = get_github_copilot_base_url(enterprise_domain="company.ghe.com")
        assert url == "https://copilot-api.company.ghe.com"

    def test_with_proxy_token(self):
        # Token format: tid=xxx;exp=xxx;proxy-ep=proxy.enterprise.com;...
        token = "tid=abc;exp=123;proxy-ep=proxy.enterprise.com;sku=abc"
        url = get_github_copilot_base_url(token=token)
        assert url == "https://api.enterprise.com"

    def test_proxy_ep_not_starting_with_proxy(self):
        token = "tid=abc;exp=123;proxy-ep=custom.host.com;sku=abc"
        url = get_github_copilot_base_url(token=token)
        assert url == "https://custom.host.com"
