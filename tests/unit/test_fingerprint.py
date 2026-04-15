from utils.fingerprint import get_fingerprint, _USER_AGENTS, _VIEWPORTS, _LOCALES


def test_get_fingerprint_has_all_keys():
    fp = get_fingerprint()
    assert "user_agent" in fp
    assert "viewport" in fp
    assert "locale" in fp


def test_user_agent_from_pool():
    for _ in range(50):
        fp = get_fingerprint()
        assert fp["user_agent"] in _USER_AGENTS


def test_viewport_is_valid_dict():
    for _ in range(50):
        fp = get_fingerprint()
        assert fp["viewport"] in _VIEWPORTS
        assert fp["viewport"]["width"] > 0
        assert fp["viewport"]["height"] > 0


def test_locale_from_pool():
    for _ in range(50):
        fp = get_fingerprint()
        assert fp["locale"] in _LOCALES


def test_pool_sizes():
    assert len(_USER_AGENTS) >= 10
    assert len(_VIEWPORTS) >= 5
    assert len(_LOCALES) >= 3


def test_randomness_produces_variety():
    seen_uas = set()
    for _ in range(200):
        seen_uas.add(get_fingerprint()["user_agent"])
    # 10 UA, 200 çağrı → en az 5 farklı görülmeli (olasılıksal ama güvenli)
    assert len(seen_uas) >= 5
