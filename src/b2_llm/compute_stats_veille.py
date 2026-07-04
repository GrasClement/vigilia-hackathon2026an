"""Statistiques déterministes pour une veille quotidienne d'amendements.

Le module expose une fonction principale, ``main``, importable depuis un
pipeline. Elle lit le CSV des résultats d'une veille sur un jour et retourne un
objet JSON-sérialisable contenant les seuls chiffres que le LLM est autorisé à
reprendre dans son message.

La fonction ne génère pas le message Tchap : elle prépare uniquement les faits,
les répartitions, les signaux et une courte liste d'amendements à ouvrir.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from textwrap import shorten
from typing import Any

SEUIL_VOLUME_ELEVE = 50
SEUIL_VOLUME_EXCEPTIONNEL = 200
STATUTS_NOTABLES = {"Adopté", "Rejeté", "Retiré", "Irrecevable"}
CHAMPS_TEXTUELS = ("dispositif", "exposeSommaire", "titre_dossier", "titre_dossier_court")

Row = dict[str, str]
JsonDict = dict[str, Any]


def normaliser_texte(valeur: object | None) -> str:
    """Normalise une valeur textuelle pour les recherches exactes.

    Paramètres
    ----------
    valeur : object or None
        Valeur à convertir en chaîne normalisée.

    Retour
    ------
    str
        Chaîne en minuscules, sans accents et avec espaces normalisés.
    """
    if valeur is None:
        return ""
    texte = unicodedata.normalize("NFKD", str(valeur))
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.lower()
    return re.sub(r"\s+", " ", texte).strip()


def lire_csv(path: str | Path) -> list[Row]:
    """Lit le CSV quotidien de veille en conservant les valeurs textuelles."""
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def parser_filtres(valeur: object | None) -> list[str]:
    """Parse le champ ``_filtres_trouves`` en liste de filtres.

    La fonction accepte un JSON valide, une liste Python sérialisée ou une chaîne
    imitant une liste NumPy/Pandas.
    """
    if valeur is None or str(valeur).strip() == "":
        return []
    texte = str(valeur).strip()
    try:
        loaded = json.loads(texte)
        if isinstance(loaded, list):
            return [str(x) for x in loaded]
    except json.JSONDecodeError:
        pass
    return re.findall(r"['\"]([^'\"]+)['\"]", texte) or [texte]


def top(counter: Counter[str], n: int) -> list[JsonDict]:
    """Retourne les ``n`` modalités les plus fréquentes d'un compteur."""
    return [{"modalite": k, "nombre": v} for k, v in counter.most_common(n)]


def texte_recherche(row: Row) -> str:
    """Concatène les champs textuels utiles à la recherche de mots-clés."""
    return normaliser_texte(" ".join(row.get(col, "") for col in CHAMPS_TEXTUELS))


def chercher_mot_cle(rows: list[Row], mot_cle: str) -> list[str]:
    """Retourne les UID des amendements contenant exactement un mot-clé."""
    cible = normaliser_texte(mot_cle)
    if not cible:
        return []
    motif = re.compile(rf"\b{re.escape(cible)}\b")
    return [row["uid"] for row in rows if row.get("uid") and motif.search(texte_recherche(row))]


def chercher_depute(rows: list[Row], nom_complet: str) -> list[str]:
    """Retourne les UID des amendements déposés par un député suivi."""
    cible = normaliser_texte(nom_complet)
    parties = [p for p in cible.split() if p]
    uids: list[str] = []
    for row in rows:
        auteur = normaliser_texte(f"{row.get('auteur_prenom', '')} {row.get('auteur_nom', '')}")
        if cible in auteur or all(part in auteur for part in parties):
            if row.get("uid"):
                uids.append(row["uid"])
    return uids


def construire_url(row: Row, prefixe_by_document: dict[str, str] | None = None) -> JsonDict:
    """Construit les liens vers la page web et le JSON officiel de l'amendement.

    Le lien web nécessite le préfixe d'organe d'examen. La fonction le prend
    d'abord dans le CSV s'il existe, puis dans ``prefixe_by_document``.
    """
    uid = row.get("uid", "")
    document_uid = row.get("document_uid", "")

    legislature = re.search(r"L(\d+)", uid or "")
    numero = re.search(r"N0*(\d+)$", uid or "")
    texte = re.search(r"B(?:TC)?(\d+)", document_uid or uid or "")

    prefixe = (
        row.get("prefixe_organe_examen")
        or row.get("prefixeOrganeExamen")
        or row.get("identification.prefixeOrganeExamen")
        or (prefixe_by_document or {}).get(document_uid)
    )

    legislature = legislature.group(1) if legislature else None
    numero = numero.group(1) if numero else None
    texte = texte.group(1) if texte else None

    url_web = None
    if legislature and texte and prefixe and numero:
        url_web = f"https://www.assemblee-nationale.fr/dyn/{legislature}/amendements/{texte}/{prefixe}/{numero}"

    return {
        "numero": numero,
        "url_amendement": url_web,
        "url_json": f"https://www.assemblee-nationale.fr/dyn/opendata/{uid}.json" if uid else None,
    }


def resumer_source(row: Row, width: int = 260) -> str:
    """Produit un court résumé source déterministe à partir du texte disponible."""
    texte = row.get("dispositif") or row.get("exposeSommaire") or ""
    texte = re.sub(r"\s+", " ", texte).strip()
    return shorten(texte, width=width, placeholder="…") if texte else ""


def dedupliquer_uids(*listes_uids: list[str]) -> list[str]:
    """Concatène plusieurs listes d'UID en conservant l'ordre et sans doublons."""
    out: list[str] = []
    deja_vus: set[str] = set()
    for uids in listes_uids:
        for uid in uids:
            if uid and uid not in deja_vus:
                out.append(uid)
                deja_vus.add(uid)
    return out


def main(
    csv_path: str | Path,
    veille: JsonDict,
    *,
    output_json_path: str | Path | None = None,
    prefixe_by_document: dict[str, str] | None = None,
    top_n: int = 10,
    max_amendements_a_ouvrir: int = 12,
) -> JsonDict:
    """Calcule le JSON de statistiques d'une veille quotidienne.

    Paramètres
    ----------
    csv_path : str or pathlib.Path
        Chemin du CSV des résultats de la veille sur un jour.
    veille : dict
        Contexte de veille. Clés attendues : ``id_veille``, ``nom_veille``,
        ``objectif``, ``mots_cles_suivis``, ``deputes_suivis``. La clé
        optionnelle ``formes_proches`` permet de suivre des variantes lexicales,
        par exemple ``{"agriculture": ["agricole", "agricoles"]}``.
    output_json_path : str or pathlib.Path or None, default=None
        Chemin de sortie optionnel. Si renseigné, le JSON est écrit sur disque.
    prefixe_by_document : dict or None, default=None
        Mapping optionnel ``document_uid -> prefixe_organe_examen`` pour générer
        les URL web lorsque le préfixe n'est pas déjà présent dans le CSV.
    top_n : int, default=10
        Nombre de modalités conservées dans les répartitions.
    max_amendements_a_ouvrir : int, default=12
        Nombre maximal d'amendements sélectionnés pour la section opérationnelle.

    Retour
    ------
    dict
        Statistiques JSON-sérialisables, à transmettre au LLM.
    """
    rows = lire_csv(csv_path)
    colonnes = list(rows[0].keys()) if rows else []
    uids = [row.get("uid", "") for row in rows if row.get("uid")]
    row_by_uid = {row.get("uid", ""): row for row in rows if row.get("uid")}

    mots_cles = list(veille.get("mots_cles_suivis") or [])
    deputes = list(veille.get("deputes_suivis") or [])
    formes_proches = dict(veille.get("formes_proches") or {})

    hits_mots_cles = {mot: chercher_mot_cle(rows, mot) for mot in mots_cles}
    hits_formes_proches = {
        mot: {forme: chercher_mot_cle(rows, forme) for forme in formes}
        for mot, formes in formes_proches.items()
    }
    hits_deputes = {depute: chercher_depute(rows, depute) for depute in deputes}

    statuts_notables_uids = [
        row["uid"] for row in rows
        if row.get("uid") and row.get("sortAmendement") in STATUTS_NOTABLES
    ]

    c_sort = Counter(row.get("sortAmendement") or "Non renseigné" for row in rows)
    c_etat = Counter(row.get("etatLibelle") or "Non renseigné" for row in rows)
    c_dossier = Counter(row.get("titre_dossier_court") or "Non renseigné" for row in rows)
    c_groupe = Counter(row.get("groupe_politique_abrege") or row.get("groupe_politique") or "Non renseigné" for row in rows)
    c_auteur = Counter(
        f"{row.get('auteur_prenom', '').strip()} {row.get('auteur_nom', '').strip()}".strip() or "Non renseigné"
        for row in rows
    )
    c_filtre: Counter[str] = Counter()
    for row in rows:
        c_filtre.update(parser_filtres(row.get("_filtres_trouves")))

    nb = len(rows)
    nb_dossiers = len({row.get("dossier_ref_uid") or row.get("titre_dossier_court") for row in rows})
    nb_auteurs = len({auteur for auteur in c_auteur if auteur != "Non renseigné"})
    nb_groupes = len({groupe for groupe in c_groupe if groupe != "Non renseigné"})

    signaux: list[JsonDict] = []
    if nb > SEUIL_VOLUME_EXCEPTIONNEL:
        signaux.append({"niveau": "Forte", "type_signal": "volume_exceptionnel", "nombre_amendements": nb})
    elif nb > SEUIL_VOLUME_ELEVE:
        signaux.append({"niveau": "Forte", "type_signal": "volume_eleve", "nombre_amendements": nb})

    for mot, hit_uids in hits_mots_cles.items():
        signaux.append({
            "niveau": "Forte" if hit_uids else "Faible",
            "type_signal": "mot_cle_suivi",
            "mot_cle": mot,
            "nombre_amendements": len(hit_uids),
            "uids": hit_uids[:max_amendements_a_ouvrir],
        })

    for mot, formes in hits_formes_proches.items():
        uids_formes = sorted({uid for uids in formes.values() for uid in uids})
        if uids_formes:
            signaux.append({
                "niveau": "Moyenne",
                "type_signal": "forme_proche_mot_cle",
                "mot_cle": mot,
                "formes_detectees": [forme for forme, uids in formes.items() if uids],
                "nombre_amendements": len(uids_formes),
                "uids": uids_formes[:max_amendements_a_ouvrir],
            })

    for depute, hit_uids in hits_deputes.items():
        if hit_uids:
            signaux.append({
                "niveau": "Forte",
                "type_signal": "depute_suivi",
                "depute": depute,
                "nombre_amendements": len(hit_uids),
                "uids": hit_uids[:max_amendements_a_ouvrir],
            })

    if statuts_notables_uids:
        signaux.append({
            "niveau": "Forte",
            "type_signal": "statuts_notables",
            "nombre_amendements": len(statuts_notables_uids),
            "repartition": top(Counter(row.get("sortAmendement") for row in rows if row.get("sortAmendement") in STATUTS_NOTABLES), top_n),
            "uids": statuts_notables_uids[:max_amendements_a_ouvrir],
        })

    uids_formes_proches = [uid for formes in hits_formes_proches.values() for uids in formes.values() for uid in uids]
    selection = dedupliquer_uids(
        *hits_mots_cles.values(),
        uids_formes_proches,
        *hits_deputes.values(),
        statuts_notables_uids,
    )[:max_amendements_a_ouvrir]

    amendements_a_ouvrir = []
    for uid in selection:
        row = row_by_uid[uid]
        liens = construire_url(row, prefixe_by_document=prefixe_by_document)
        auteur = f"{row.get('auteur_prenom', '').strip()} {row.get('auteur_nom', '').strip()}".strip()
        amendements_a_ouvrir.append({
            "uid": uid,
            "numero": liens["numero"],
            "url_amendement": liens["url_amendement"],
            "url_json": liens["url_json"],
            "dossier": row.get("titre_dossier_court"),
            "auteur": auteur or None,
            "groupe": row.get("groupe_politique_abrege") or row.get("groupe_politique"),
            "sort_amendement": row.get("sortAmendement"),
            "etat": row.get("etatLibelle"),
            "filtres_trouves": parser_filtres(row.get("_filtres_trouves")),
            "resume_source": resumer_source(row),
        })

    faits = [
        f"{nb} amendements sont présents dans le CSV de résultats fourni.",
        f"Les amendements concernent {nb_dossiers} dossiers distincts.",
        f"{len(statuts_notables_uids)} amendements ont un sort notable parmi : {', '.join(sorted(STATUTS_NOTABLES))}.",
    ]
    faits += [f"Le CSV contient {len(uids)} amendements mentionnant le mot-clé exact {mot}." for mot, uids in hits_mots_cles.items()]
    faits += [f"{depute} est auteur de {len(uids)} amendements dans le CSV." for depute, uids in hits_deputes.items()]

    stats = {
        "schema_version": "veille_amendements_stats_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "veille": veille,
        "integrite_entree": {
            "nombre_lignes_csv": nb,
            "nombre_uid_uniques": len(set(uids)),
            "nombre_doublons_uid": nb - len(set(uids)),
            "colonnes_presentes": colonnes,
            "colonnes_manquantes_critiques": [
                col for col in ("uid", "dispositif", "exposeSommaire", "sortAmendement", "etatLibelle", "auteur_nom", "document_uid")
                if col not in colonnes
            ],
        },
        "chiffres_cles": {
            "nombre_amendements_detectes": nb,
            "nombre_dossiers_distincts": nb_dossiers,
            "nombre_auteurs_distincts": nb_auteurs,
            "nombre_groupes_distincts": nb_groupes,
            "nombre_deputes_suivis_detectes": sum(1 for uids in hits_deputes.values() if uids),
            "nombre_amendements_a_statut_notable": len(statuts_notables_uids),
            "volume": {
                "niveau": "exceptionnel" if nb > SEUIL_VOLUME_EXCEPTIONNEL else "eleve" if nb > SEUIL_VOLUME_ELEVE else "standard",
                "seuil_volume_eleve": SEUIL_VOLUME_ELEVE,
                "seuil_volume_exceptionnel": SEUIL_VOLUME_EXCEPTIONNEL,
            },
        },
        "repartitions": {
            "par_sort_amendement": top(c_sort, top_n),
            "par_etat_libelle": top(c_etat, top_n),
            "par_dossier": top(c_dossier, top_n),
            "par_groupe_politique": top(c_groupe, top_n),
            "par_auteur": top(c_auteur, top_n),
            "par_filtre_declencheur": top(c_filtre, top_n),
        },
        "mots_cles_suivis": {mot: {"nombre_amendements": len(uids), "uids": uids} for mot, uids in hits_mots_cles.items()},
        "formes_proches": {
            mot: {forme: {"nombre_amendements": len(uids), "uids": uids} for forme, uids in formes.items()}
            for mot, formes in hits_formes_proches.items()
        },
        "deputes_suivis": {
            "detectes": [{"nom": dep, "nombre_amendements": len(uids), "uids": uids} for dep, uids in hits_deputes.items() if uids],
            "non_detectes": [dep for dep, uids in hits_deputes.items() if not uids],
        },
        "signaux_prioritaires": signaux,
        "amendements_a_ouvrir": amendements_a_ouvrir,
        "faits_autorises_pour_le_llm": faits,
        "contraintes_generation": {
            "source_unique_des_chiffres": "json_stats",
            "interdictions_llm": [
                "Ne pas recompter les lignes du CSV.",
                "Ne pas produire de chiffre absent du JSON de statistiques.",
                "Ne pas produire de pourcentage absent du JSON de statistiques.",
                "Ne pas construire d'URL : utiliser uniquement les URL fournies dans le JSON.",
            ],
        },
    }

    if output_json_path is not None:
        Path(output_json_path).write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    return stats


def _cli() -> None:
    """Interface minimale pour tester le module en ligne de commande."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--veille-json", required=True)
    parser.add_argument("--output", required=False)
    parser.add_argument("--prefixe-json", required=False)
    args = parser.parse_args()

    veille = json.loads(Path(args.veille_json).read_text(encoding="utf-8"))
    prefixe = None
    if args.prefixe_json:
        prefixe = json.loads(Path(args.prefixe_json).read_text(encoding="utf-8"))

    stats = main(args.csv, veille, output_json_path=args.output, prefixe_by_document=prefixe)
    if args.output is None:
        print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli()
