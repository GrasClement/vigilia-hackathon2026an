"""Tests for veille.clean (strip_html, extract_amendement)."""

import json
from pathlib import Path

import pytest

from veille.clean import extract_amendement, strip_html

EXEMPLE = json.loads(
    (Path(__file__).parent / "data" / "amendement_exemple.json").read_text()
)


class TestStripHtml:
    """Tests for strip_html."""

    def test_decodes_hex_entities(self) -> None:
        """Hex HTML entities become accented UTF-8 characters."""
        assert strip_html("R&#x00E9;tablir") == "Rétablir"

    def test_drops_tags_and_keeps_paragraph_breaks(self) -> None:
        """Tags disappear, </p><p> boundaries become newlines."""
        result = strip_html('<p style="x">Un.</p><p>Deux.</p>')
        assert result == "Un.\nDeux."

    def test_replaces_non_breaking_spaces(self) -> None:
        """Non-breaking spaces (entity or literal) become plain spaces."""
        assert strip_html("cet&nbsp;article") == "cet article"

    def test_none_input_returns_empty(self) -> None:
        """Amendements de suppression sans exposé : None -> ''."""
        assert strip_html(None) == ""

    def test_idempotency_on_plain_text(self) -> None:
        """Already-clean text passes through unchanged."""
        assert strip_html("Texte simple.") == "Texte simple."


class TestExtractAmendement:
    """Tests for extract_amendement on a real sample."""

    def test_maps_identification_fields(self) -> None:
        """uid, numero, texte_ref, place come from the right paths."""
        doc = extract_amendement(EXEMPLE)
        assert doc["uid"] == "AMANR5L17PO838901BTC2984P0D1N000001"
        assert doc["numero"] == "1"
        assert doc["texte_ref"] == "PRJLANR5L17BTC2984"
        assert doc["place"] == "Article 2 bis"

    def test_auteur_is_full_readable_libelle(self) -> None:
        """auteur carries the readable list incl. cosigners."""
        doc = extract_amendement(EXEMPLE)
        assert doc["auteur"].startswith("M. Pauget")
        assert "Mme Bonnivard" in doc["auteur"]

    def test_date_and_sort(self) -> None:
        """date_depot is YYYY-MM-DD; sort falls back to lifecycle state."""
        doc = extract_amendement(EXEMPLE)
        assert doc["date_depot"] == "2026-06-26"
        assert doc["sort"] == "En traitement"

    def test_url_targets_official_redirect(self) -> None:
        """URL uses the documented redirect pattern with legislature."""
        doc = extract_amendement(EXEMPLE)
        assert doc["url"] == (
            "https://www.assemblee-nationale.fr/dyn/17/amendements/"
            "AMANR5L17PO838901BTC2984P0D1N000001"
        )

    def test_text_fields_are_clean(self) -> None:
        """expose and dispositif are decoded, tag-free text."""
        doc = extract_amendement(EXEMPLE)
        assert "rave parties illégales" in doc["expose"]
        assert "<p" not in doc["dispositif"]
        assert "Rétablir cet article" in doc["dispositif"]

    def test_missing_expose_yields_empty_string(self) -> None:
        """Suppression amendments without exposé produce ''."""
        raw = json.loads(json.dumps(EXEMPLE))
        del raw["corps"]["contenuAuteur"]["exposeSommaire"]
        assert extract_amendement(raw)["expose"] == ""

    def test_missing_uid_raises(self) -> None:
        """A file without uid is rejected with a clear message."""
        with pytest.raises(ValueError, match="uid"):
            extract_amendement({"legislature": "17"})
