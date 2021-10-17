import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")))
import pytest

from configlookup.main import Configuration
from configlookup.overrider.abstract_overrider import AbstractOverrider

RESOURCES_DIR = f"{os.path.dirname(os.path.realpath(__file__))}/resources"
JSON_FILE_1_SUFFIX = "_all"
JSON_FILE_2_SUFFIX = "_test2"
JSON_FILES_SUFFIXES = [JSON_FILE_1_SUFFIX, JSON_FILE_2_SUFFIX]

JSON_FILE_1 = f"{os.path.dirname(os.path.realpath(__file__))}/resources/configlookup_all.json"


class DummyOverrider(AbstractOverrider):
    def __init__(self, key: str, value: str):
        self.__key = key
        self.__value = value

    def get(self, key) -> str:
        _result = None
        if key == self.__key:
            _result = self.__value
        return _result


@pytest.fixture
def instance(monkeypatch):
    monkeypatch.setenv("CONFIGLOOKUP_DIR", RESOURCES_DIR)
    return Configuration()


def test_type_error(instance, monkeypatch):
    with pytest.raises(TypeError) as x:
        instance._Configuration__load(1234)


def test_value_error(instance):
    with pytest.raises(FileNotFoundError) as x:
        instance._Configuration__load("not_a_file")


def test_one_level_dict(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert instance.get("server.url") == instance.get("SERVER__URL") == "http://www.site.com", f"failed: {instance}"


def test_one_level_dict_underscored(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert instance.get("name_prefix") == instance.get("NAME_PREFIX") == "mr", f"failed: {instance}"


def test_one_level_obj(instance):
    _expected_dict = {
        "resources": {"color": "yellow", "mem": 2048, "mem_min": 1024},
        "url": "http://www.site.com",
    }
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert (
        sorted(instance.get("server").items())
        == sorted(instance.get("SERVER").items())
        == sorted(_expected_dict.items())
    )


def test_one_level_obj_underscored(instance):
    _expected_dict = {"n": 3, "mem_min": 1024}
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert (
        sorted(instance.get("rack.blade_lowspec").items())
        == sorted(instance.get("RACK__BLADE_LOWSPEC").items())
        == sorted(_expected_dict.items())
    )


def test_two_level_dict(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert instance.get("server.name_prefix") == instance.get("SERVER__NAME_PREFIX") == "mr"


def test_two_level_dict__overriden_underscores(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=JSON_FILES_SUFFIXES)
    assert instance.get("server.name_prefix") == instance.get("SERVER__NAME_PREFIX") == "dr"


def test_first_level_text(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert instance.get("name") == instance.get("NAME") == "myname"


def test_first_level_number(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert instance.get("id") == instance.get("ID") == 12345


def test_first_level_array(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    assert instance.get("tags") == instance.get("TAGS")
    assert sorted(instance.get("tags")) == sorted(["server", "api"])


def test_override_by_environment_check_dict(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=[JSON_FILE_1_SUFFIX])
    instance._Configuration__overriders.append(DummyOverrider("SERVER__RESOURCES__MEM", "9192"))
    expected = {"color": "yellow", "mem": 2048, "mem_min": 1024}
    assert instance.get("server.resources.mem") == instance.get("SERVER__RESOURCES__MEM") == "9192"
    assert instance.get("server.resources") == expected


def test_override_by_environment_check_dict_with_file(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files=[JSON_FILE_1])
    instance._Configuration__overriders.append(DummyOverrider("SERVER__RESOURCES__MEM", "9192"))
    expected = {"color": "yellow", "mem": 2048, "mem_min": 1024}
    assert instance.get("server.resources.mem") == instance.get("SERVER__RESOURCES__MEM") == "9192"
    assert instance.get("server.resources") == expected


def test_overrider(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files=[JSON_FILE_1])
    instance._Configuration__overriders.append(DummyOverrider("SERVER__RESOURCES__COLOR", "brown"))
    _expected_dict = {"color": "yellow", "mem": 2048, "mem_min": 1024}
    assert instance.get("server.resources") == _expected_dict
    assert instance.get("SERVER__RESOURCES__COLOR") == "brown"
    assert instance.get("server.resources.color") == "brown"


def test_filter_key_no_key(instance):
    with pytest.raises(LookupError) as x:
        instance._Configuration__load(
            files_path=RESOURCES_DIR,
            files=[JSON_FILE_1],
        )
        instance.get("SERVER_RESOURCES_MEMX")
    assert "key SERVER_RESOURCES_MEMX not found" == str(x.value)


def test_filter_key_overridden(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files=[JSON_FILE_1])
    instance._Configuration__overriders.append(DummyOverrider("OTHER__VAR4", "AAA"))

    assert instance.get("OTHER__VAR1") == instance.get("other.var1") == "GOLD"
    assert instance.get("OTHER__VAR4") == instance.get("other.var4") == "AAA"
    assert instance.get("OTHER__VAR5") == instance.get("other.var5") == "A"


def test_filter_key_overridden_multiple_files(instance):
    instance._Configuration__load(files_additional_suffixes=JSON_FILES_SUFFIXES, files_path=RESOURCES_DIR)
    assert instance.get("BIG_PSWD") == "stilldummy"


def test_filter_key_overridden_multiple_files_variables_overrider(instance):
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=JSON_FILES_SUFFIXES)
    instance._Configuration__overriders.append(DummyOverrider("BIG_PSWD", "definitely_not_dummy"))
    assert instance.get("BIG_PSWD") == "definitely_not_dummy"


def test_filter_key_overridden_multiple_files_variables_overrider_env(monkeypatch, instance):
    monkeypatch.setenv("BIG_PSWD", "intelligent")
    instance._Configuration__load(files_path=RESOURCES_DIR, files_additional_suffixes=JSON_FILES_SUFFIXES)
    instance._Configuration__overriders.insert(
        len(instance._Configuration__overriders) - 1,
        DummyOverrider("BIG_PSWD", "definitely_not_dummy"),
    )
    assert instance.get("BIG_PSWD") == "intelligent"


def test_filter_key_no_key(instance):
    instance._Configuration__load(files=[JSON_FILE_1], files_path=RESOURCES_DIR)
    with pytest.raises(LookupError) as x:
        instance.get("SERVER_RESOURCES_MEMX")
    assert "[get] key SERVER_RESOURCES_MEMX not found" == str(x.value)


def test_filter_key_multiple_sources(monkeypatch, instance):
    monkeypatch.setenv("OTHER__VAR8", "BOG")
    instance._Configuration__load(files_additional_suffixes=JSON_FILES_SUFFIXES, files_path=RESOURCES_DIR)
    assert instance.get("OTHER__VAR1") == "GOLD"
    assert instance.get("OTHER__VAR3") == "BRONZE"
    assert instance.get("OTHER__VAR4") == "WOODEN"
    assert instance.get("OTHER__VAR5") == "C"
    assert instance.get("OTHER__VAR6") == "WATER"
    assert instance.get("OTHER__VAR7") == "1000"
    assert instance.get("OTHER__VAR8") == "BOG"


def test_dummy_to_reset_configuration_singleton(monkeypatch, instance):
    # we need to keep this test here to reset the configuration data, after doing tests on it
    instance._Configuration__load()
    assert True
