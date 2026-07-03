"""Tests for veille.fetch_api (URL building, no network)."""

import pytest

from veille.fetch_api import DATE_FIELDS, build_url, fetch_mots_cles


class TestBuildUrl:
    """Tests for build_url."""

    def test_matches_documented_pattern(self) -> None:
        """URL carries date bounds, sort, pagination and search."""
        url = build_url("amendements", "2026-07-02", search="budget", per_page=10)
        assert url.startswith("https://parlement.tricoteuses.fr/v2/amendements?")
        assert "dateDepot.gte=2026-07-02T00%3A00%3A00.000Z" in url
        assert "dateDepot.lte=2026-07-02T23%3A59%3A59.999Z" in url
        assert "sort=dateDepot.desc" in url
        assert "perPage=10" in url
        assert "search=budget" in url

    def test_encodes_multiword_keyword(self) -> None:
        """'budget vert' is URL-encoded."""
        url = build_url("questions", "2026-07-02", search="budget vert")
        assert "search=budget+vert" in url or "search=budget%20vert" in url

    def test_each_known_resource_has_its_date_field(self) -> None:
        """Every DATE_FIELDS entry produces its recommended field."""
        for resource, field in DATE_FIELDS.items():
            assert f"{field}.gte=" in build_url(resource, "2026-07-02")

    def test_date_field_override(self) -> None:
        """dateSort can replace dateDepot to watch outcomes."""
        url = build_url("amendements", "2026-07-02", date_field="dateSort")
        assert "dateSort.gte=" in url
        assert "dateDepot" not in url

    def test_unknown_resource_raises(self) -> None:
        """A resource without known date field raises ValueError."""
        with pytest.raises(ValueError, match="champ de date"):
            build_url("acteurs", "2026-07-02")

    def test_bad_date_raises(self) -> None:
        """A non ISO day raises ValueError."""
        with pytest.raises(ValueError, match="YYYY-MM-DD"):
            build_url("amendements", "02/07/2026")

    def test_no_search_param_when_absent(self) -> None:
        """Without keyword, no search parameter is emitted."""
        assert "search=" not in build_url("amendements", "2026-07-02")


class TestFetchMotsCles:
    """Tests for fetch_mots_cles validation."""

    def test_empty_keywords_raise(self) -> None:
        """Only blank keywords -> ValueError before any network call."""
        with pytest.raises(ValueError, match="mot-clé"):
            fetch_mots_cles("amendements", "2026-07-02", ["", "  "])
