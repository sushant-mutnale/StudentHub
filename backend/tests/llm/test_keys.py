from backend.services.llm.keys import ApiKeyPool, fingerprint


def test_fingerprint_is_stable_and_short():
    value = "gsk_example_key_value"
    assert fingerprint(value) == fingerprint(value)
    assert len(fingerprint(value)) == 16


def test_fingerprint_does_not_contain_the_raw_key():
    value = "gsk_supersecret"
    assert value not in fingerprint(value)


def test_pool_skips_blank_keys_and_numbers_the_rest():
    pool = ApiKeyPool(["gsk_a", "", "   ", "gsk_b"])
    assert len(pool) == 2
    assert [key.index for key in pool] == [0, 1]
    assert [key.value for key in pool] == ["gsk_a", "gsk_b"]


def test_pool_is_empty_when_nothing_is_configured():
    pool = ApiKeyPool([None, "", "  "])
    assert pool.empty is True
    assert len(pool) == 0


def test_key_repr_never_leaks_the_value():
    pool = ApiKeyPool(["gsk_supersecret"])
    key = list(pool)[0]
    assert "gsk_supersecret" not in repr(key)
    assert key.keyhash in repr(key)


def test_pool_gives_each_key_a_distinct_fingerprint():
    pool = ApiKeyPool(["gsk_a", "gsk_b", "gsk_c"])
    hashes = {key.keyhash for key in pool}
    assert len(hashes) == 3
