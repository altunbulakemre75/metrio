from utils.proxy_pool import ProxyPool


def test_disabled_returns_none():
    pool = ProxyPool(proxy_list="http://u:p@1.2.3.4:8080", enabled=False)
    assert pool.pick() is None


def test_enabled_but_empty_returns_none():
    pool = ProxyPool(proxy_list="", enabled=True)
    assert pool.pick() is None


def test_enabled_with_single_proxy():
    pool = ProxyPool(proxy_list="http://user:pass@1.2.3.4:8080", enabled=True)
    result = pool.pick()
    assert result is not None
    assert result["server"] == "http://1.2.3.4:8080"
    assert result["username"] == "user"
    assert result["password"] == "pass"


def test_enabled_rotates_multiple_proxies():
    pool = ProxyPool(
        proxy_list="http://u1:p1@1.1.1.1:80,http://u2:p2@2.2.2.2:80",
        enabled=True,
    )
    picks = {pool.pick()["server"] for _ in range(50)}
    assert len(picks) == 2  # ikisinden de seçilmeli


def test_proxy_without_auth():
    pool = ProxyPool(proxy_list="http://1.2.3.4:8080", enabled=True)
    result = pool.pick()
    assert result["server"] == "http://1.2.3.4:8080"
    assert result["username"] == ""
    assert result["password"] == ""
