import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")))
from configlookup.utils import ConfigurationUtils


def test_merge():
    x = {"server": {"resources": {"mem": "2048"}}, "name": "zenao", "tags": ["belo", "abstruso"]}
    y = {"server": {"resources": {"cpu": "1xc"}}, "id": "1", "tags": ["yellow"]}
    expected = {
        "server": {"resources": {"cpu": "1xc", "mem": "2048"}},
        "id": "1",
        "name": "zenao",
        "NAME": "zenao",
        "tags": ["belo", "abstruso", "yellow"],
        "SERVER__RESOURCES__MEM": "2048",
    }
    ConfigurationUtils.merge_dict(x, y)
    sorted_y = {k[0]: k[1] for k in sorted(y.items())}
    sorted_expected = {k[0]: k[1] for k in sorted(expected.items())}
    sorted_expected["tags"] = sorted(sorted_expected["tags"])
    sorted_y["tags"] = sorted(sorted_y["tags"])
    assert sorted_y == sorted_expected


def test_find_property():
    d = {"var1": {"big_pswd": {"cpu": "1xc"}, "big": {"pswd": "1234"}}}
    assert "big_pswd" == ConfigurationUtils.find_property("var1.big_pswd", d)["key"]
    assert "cpu" == ConfigurationUtils.find_property("var1.big_pswd.cpu", d)["key"]
    assert "pswd" == ConfigurationUtils.find_property("var1.big.pswd", d)["key"]


def test_variable_to_property():
    assert ConfigurationUtils.variable_to_property("A__B_CD_E") == "a.b_cd_e"
    assert ConfigurationUtils.variable_to_property("A_B_CD_E") == "a_b_cd_e"
    assert ConfigurationUtils.variable_to_property("A") == "a"
    assert ConfigurationUtils.variable_to_property("A__a") == "a.a"


def test_property_to_variable():
    assert ConfigurationUtils.property_to_variable("a_b.cd.e") == "A_B__CD__E"
    assert ConfigurationUtils.property_to_variable("a.b.cd.e") == "A__B__CD__E"
    assert ConfigurationUtils.property_to_variable("a") == "A"
    assert ConfigurationUtils.property_to_variable("a_a") == "A_A"


def test_prop_and_var_from_key():
    assert ConfigurationUtils.prop_and_var_from_key("A_b.Cd.e") == ("a_b.cd.e", "A_B__CD__E")
    assert ConfigurationUtils.prop_and_var_from_key("a.B.cD.e") == ("a.b.cd.e", "A__B__CD__E")
    assert ConfigurationUtils.prop_and_var_from_key("a_a") == ("a_a", "A_A")
    assert ConfigurationUtils.prop_and_var_from_key("A__A") == ("a.a", "A__A")
    assert ConfigurationUtils.prop_and_var_from_key("A__a") == ("a.a", "A__A")


def test_find_config():
    d = {
        "var1": {"big_pswd": {"cpu": "1xc"}, "big": {"pswd": "1234"}},
        "VAR1": {"big_pswd": {"cpu": "1xc"}, "big": {"pswd": "1234"}},
        "VAR1_BIG__PSWD": {"cpu": "1xc"},
        "VAR1_BIG_PSWD": "1234",
    }
    assert "big_pswd" == ConfigurationUtils.find_property("var1.big_pswd", d)["key"]
    assert "cpu" == ConfigurationUtils.find_property("var1.big_pswd.cpu", d)["key"]
    assert "pswd" == ConfigurationUtils.find_property("var1.big.pswd", d)["key"]
    assert "VAR1_BIG__PSWD" == ConfigurationUtils.find_property("VAR1_BIG__PSWD", d)["key"]
    assert "VAR1_BIG_PSWD" == ConfigurationUtils.find_property("VAR1_BIG_PSWD", d)["key"]
    assert d == ConfigurationUtils.find_property("VAR1_BIG__PSWD", d)["pointer"]
    assert d == ConfigurationUtils.find_property("VAR1_BIG_PSWD", d)["pointer"]
    c = ConfigurationUtils.find_property("VAR1_BIG_PSWD", d)
    assert "1234" == c["pointer"][c["key"]]
