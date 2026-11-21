"""Shared, offline address parsing; no partner writes or external requests."""

import json
from functools import lru_cache
from pathlib import Path

from odoo import api, models

_SEPARATORS = " \t\r\n,，;；"
_MUNICIPALITIES = {"北京市", "天津市", "上海市", "重庆市"}
_VIRTUAL_CITIES = {"市辖区", "县", "省直辖县级行政区划", "自治区直辖县级行政区划"}


@lru_cache(maxsize=1)
def _divisions():
    source = Path(__file__).parent.parent / "data/address/china_divisions.json"
    return json.loads(source.read_text(encoding="utf-8"))


def _prefix_match(text, choices):
    """Only consume an unambiguous longest prefix, never names inside a road."""
    matches = [(alias, value) for alias, value in choices if text.startswith(alias)]
    if not matches:
        return None, text
    length = max(len(alias) for alias, _value in matches)
    matches = [(alias, value) for alias, value in matches if len(alias) == length]
    if len(matches) != 1:
        return None, text
    alias, value = matches[0]
    return value, text[len(alias):].lstrip(_SEPARATORS)


def _province_aliases(province, text):
    name = province["name"]
    short = name[:3] if name.startswith(("黑龙江", "内蒙古")) else name[:2]
    choices = [(name, province)]
    if text.startswith(short):
        remainder = text[len(short):].lstrip(_SEPARATORS)
        if not remainder or any(
            remainder.startswith(alias) for alias, _value in _city_choices([province], remainder)
        ) or any(
            remainder.startswith(alias) for alias, _value in _district_choices([province])
        ):
            choices.append((short, province))
    return choices


def _city_choices(provinces, text):
    for province in provinces:
        for city in province["children"]:
            if city["name"] in _VIRTUAL_CITIES:
                continue
            yield city["name"], (province, city)
            if city["name"].endswith("市") and len(city["name"]) > 2:
                short = city["name"][:-1]
                remainder = text[len(short):].lstrip(_SEPARATORS) if text.startswith(short) else ""
                if any(remainder.startswith(row["name"]) for row in city.get("children", [])):
                    yield short, (province, city)


def _district_choices(provinces, selected_city=None):
    for province in provinces:
        for city in province["children"]:
            if selected_city and city != selected_city:
                continue
            for district in city.get("children", []):
                if len(district["code"]) == 6:
                    yield district["name"], (province, city, district)


def parse_china_address(address: str) -> dict:
    """Parse known prefixes; retain unknown/new districts in the street text."""
    original = (address or "").strip()
    remaining = original
    for prefix in ("中华人民共和国", "中国"):
        if remaining.startswith(prefix):
            remaining = remaining[len(prefix):].lstrip(_SEPARATORS)
            break
    province, remaining = _prefix_match(
        remaining, [choice for row in _divisions() for choice in _province_aliases(row, remaining)],
    )
    candidates = [province] if province else _divisions()
    city_match, remaining = _prefix_match(remaining, _city_choices(candidates, remaining))
    city = None
    if city_match:
        province, city = city_match
        candidates = [province]
    district_match, detail = _prefix_match(remaining, _district_choices(candidates, city))
    district = ""
    if district_match:
        province, city, district_row = district_match
        district = district_row["name"]
        remaining = detail
    city_name = city["name"] if city else ""
    if province and province["name"] in _MUNICIPALITIES:
        city_name = province["name"]
    elif city_name in _VIRTUAL_CITIES:
        city_name = ""
    return {
        "original": original,
        "province": province["name"] if province else "",
        "city": city_name,
        "district": district,
        # Keep the district in native street so standard reports retain it.
        "street": district + remaining if province else original,
        "status": "recognized" if province and city_name else "partial" if province else "unrecognized",
    }


class ChinaAddressParser(models.AbstractModel):
    _name = "abt.address.parser"
    _description = "公共中国地址解析服务"

    @api.model
    def parse(self, address):
        """Return semantic components for any caller; never mutate records."""
        return parse_china_address(address)

    @api.model
    def partner_values(self, address):
        """Adapt the shared result to native partner address fields."""
        result = self.parse(address)
        values = {
            "street": result["street"] or False,
            "street2": False,
            "city": result["city"] or False,
            "state_id": False,
            "zip": False,
            "abt_address_original": result["original"] or False,
        }
        if result["province"]:
            china = self.env.ref("base.cn")
            state = self.env["res.country.state"].with_context(lang=False).search([
                ("country_id", "=", china.id), ("name", "=", result["province"]),
            ], limit=1)
            values.update(country_id=china.id, state_id=state.id)
        return values
