"""Tests pour veille.synthese — aucun appel réseau réel."""

from unittest.mock import MagicMock

import pytest
import requests

from veille.synthese import (
    construire_message_utilisateur,
    construire_stats,
    generer_message,
    message_secours,
    niveau_priorite,
    ordonner_par_pertinence,
    url_amendement,
)

CONTEXTE = {
    "veille_nom": "veille_2",
    "objectif": "suivre le renforcement de la protection des mineurs",
    "veille_termes": "protection",
    "veille_noms": "Gouffier Valente",
}


def amendement(**kw) -> dict:
    base = {
        "uid": "AMANR5L17PO883517B2841P0D1N001018",
        "auteur_nom": "Bonnivard", "auteur_prenom": "Émilie", "auteur_civ": "Mme",
        "groupe_politique_abrege": "DR", "sortAmendement": "En traitement",
        "titre_dossier_court": "Protection des enfants",
        "filtres_trouves": "['exposeSommaire:protection']",
        "dateDepot": "2026-07-01T00:00:00.000Z", "nombreCoSignataires": 7,
        "dispositif": "L'article L. 221-9 est complété...",
        "exposeSommaire": "Le présent amendement prévoit une obligation de publication.",
    }
    return base | kw


class TestUrlAmendement:
    def test_construction(self) -> None:
        assert url_amendement("AMAN123").endswith("/dyn/17/amendements/AMAN123")

    def test_uid_vide_leve(self) -> None:
        with pytest.raises(ValueError, match="uid vide"):
            url_amendement("")


class TestNiveauPriorite:
    def test_sort_notable_est_forte(self) -> None:
        assert niveau_priorite(amendement(sortAmendement="Adopté"), CONTEXTE) == "Forte"

    def test_depute_suivi_est_forte(self) -> None:
        a = amendement(auteur_nom="Gouffier Valente")
        assert niveau_priorite(a, CONTEXTE) == "Forte"

    def test_filtres_multiples_est_moyenne(self) -> None:
        a = amendement(filtres_trouves="['a:x', 'b:y']")
        assert niveau_priorite(a, CONTEXTE) == "Moyenne"

    def test_defaut_est_faible(self) -> None:
        assert niveau_priorite(amendement(), CONTEXTE) == "Faible"


class TestConstruireStats:
    def test_total_et_repartitions(self) -> None:
        stats = construire_stats([amendement(), amendement(sortAmendement="Adopté")])
        assert stats["total"] == 2
        assert stats["par_statut"]["Adopté"] == 1

    def test_vide(self) -> None:
        assert construire_stats([])["total"] == 0


class TestOrdonnerParPertinence:
    def test_repli_par_date_sans_objectif(self) -> None:
        """Sans query, aucun appel réseau : tri dateDepot décroissante."""
        a1 = amendement(uid="A", dateDepot="2026-07-01")
        a2 = amendement(uid="B", dateDepot="2026-07-02")
        res = ordonner_par_pertinence([a1, a2], {"objectif": "", "veille_termes": ""})
        assert [a["uid"] for a in res] == ["B", "A"]

    def test_repli_si_rerank_echoue(self, monkeypatch) -> None:
        session = MagicMock()
        session.post.side_effect = requests.ConnectionError()
        monkeypatch.setenv("ALBERT_API_KEY", "x")
        a1 = amendement(uid="A", dateDepot="2026-07-01")
        a2 = amendement(uid="B", dateDepot="2026-07-02")
        res = ordonner_par_pertinence([a1, a2], CONTEXTE, session=session)
        assert [a["uid"] for a in res] == ["B", "A"]

    def test_ordre_du_rerank_applique(self, monkeypatch) -> None:
        """L'index renvoyé par l'API est bien la clé de jointure."""
        monkeypatch.setenv("ALBERT_API_KEY", "x")
        session = MagicMock()
        reponse = MagicMock()
        reponse.json.return_value = {"results": [
            {"relevance_score": 0.9, "index": 1},
            {"relevance_score": 0.1, "index": 0}]}
        session.post.return_value = reponse
        a1, a2 = amendement(uid="A"), amendement(uid="B")
        res = ordonner_par_pertinence([a1, a2], CONTEXTE, session=session)
        assert [a["uid"] for a in res] == ["B", "A"]

    def test_expose_vide_exclu_du_batch(self, monkeypatch) -> None:
        """minLength: 1 côté API — l'exposé vide ne part pas, il finit en queue."""
        monkeypatch.setenv("ALBERT_API_KEY", "x")
        session = MagicMock()
        reponse = MagicMock()
        reponse.json.return_value = {"results": [{"relevance_score": 0.5, "index": 0}]}
        session.post.return_value = reponse
        plein, vide = amendement(uid="A"), amendement(uid="B", exposeSommaire="")
        res = ordonner_par_pertinence([plein, vide], CONTEXTE, session=session)
        docs = session.post.call_args.kwargs["json"]["documents"]
        assert len(docs) == 1
        assert [a["uid"] for a in res] == ["A", "B"]


class TestGenererMessage:
    def test_zero_amendement_sans_appel(self) -> None:
        assert "Aucun amendement" in generer_message(CONTEXTE, [])

    def test_secours_si_chat_echoue(self, monkeypatch) -> None:
        monkeypatch.setenv("ALBERT_API_KEY", "x")
        session = MagicMock()
        session.post.side_effect = requests.ConnectionError()
        msg = generer_message(CONTEXTE, [amendement()], session=session)
        assert "⚠️" in msg
        assert "veille_2" in msg

    def test_secours_annonce_echec(self) -> None:
        stats = construire_stats([amendement()])
        msg = message_secours(CONTEXTE, stats, [(amendement(), "Forte")])
        assert "synthèse automatique a échoué" in msg
        assert "assemblee-nationale.fr" in msg


class TestConstruireMessageUtilisateur:
    def test_trois_blocs_et_plafond(self) -> None:
        stats = construire_stats([amendement()] * 3)
        msg = construire_message_utilisateur(
            CONTEXTE, stats, [(amendement(), "Forte")], [amendement(), amendement()])
        assert "Contexte de veille" in msg
        assert "seule source de chiffres" in msg
        assert "1 sur 3 détectés" in msg
        assert "Autres amendements (2)" in msg
