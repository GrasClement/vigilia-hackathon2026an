"""B4 — Génération du message de veille quotidien via Albert API.

Contrat (voir docs/synthese-design.md et DECISIONS.md) :
- entrée : le contexte d'une veille (ligne Grist `veilles`) et les
  amendements du jour (lignes Grist `resultats`, schéma Requete_1) ;
- le LLM ne calcule rien : stats, niveaux de priorité et sélection des
  K amendements en texte intégral sont faits en Python (rerank Albert
  pour l'ordre, repli déterministe par date) ;
- sortie : le message Tchap complet en markdown, jamais vide — si le
  chat échoue, un gabarit de secours part avec un bandeau d'échec.
"""

import json
import os
from collections import Counter
from typing import Any

import requests

ALBERT_BASE_URL = "https://albert.api.etalab.gouv.fr/v1"
MODELE_CHAT = "mistralai/Mistral-Small-3.2-24B-Instruct-2506"
MODELE_RERANK = "BAAI/bge-reranker-v2-m3"
K_TEXTE_INTEGRAL = 25
MAX_CHARS_RERANK = 1500
TIMEOUT_S = 60

SORTS_NOTABLES = {"adopté", "rejeté", "retiré", "irrecevable", "tombé"}

PROMPT_SYSTEME = """Tu es un assistant de veille parlementaire. Tu rédiges un message Tchap \
synthétique à partir du résultat quotidien d'une seule veille sur les amendements \
de l'Assemblée nationale.

Tu reçois trois objets :
1. un contexte de veille (objectif, mots-clés, députés suivis) ;
2. un JSON de statistiques calculées par Python ;
3. les amendements détectés : les prioritaires en texte intégral (dispositif et \
exposé sommaire), les autres en une ligne.

Règles strictes :
- Utilise exclusivement les informations fournies. N'invente aucun fait.
- Tout chiffre doit provenir du JSON de statistiques. Ne compte jamais toi-même, \
ne recalcule aucune répartition. Si un chiffre manque, formule sans chiffre.
- Les niveaux de priorité (Forte/Moyenne/Faible) et l'ordre des amendements sont \
déjà calculés : reprends-les tels quels, ne les rejuge pas.
- Les statistiques portent sur la totalité des amendements détectés ; seuls les \
prioritaires te sont fournis en texte intégral. Ne présente jamais les \
prioritaires comme s'ils étaient les seuls résultats.
- Utilise uniquement les URLs fournies pour les liens Markdown. N'en construis \
jamais toi-même.
- L'objectif de veille est une grille de lecture : relie les amendements à \
l'objectif seulement si le dispositif, l'exposé, le dossier, le statut, \
l'auteur ou les filtres le justifient. Sans objectif, résumé neutre.
- Si des députés suivis apparaissent, signale explicitement leurs amendements.
- Ton neutre, informatif, orienté action de veille. Français.
- Si aucun amendement n'est fourni, réponds uniquement : "Aucun amendement \
détecté aujourd'hui pour cette veille."

Respecte strictement le format suivant :

📌 Veille : <nom de la veille>

**Synthèse**
<5 à 10 lignes maximum. Commencer par le nombre total d'amendements détectés \
(JSON) et le signal principal. Relier à l'objectif si justifié.>

**Chiffres clés**
- Amendements détectés : <nombre du JSON>
- Dossiers concernés : <liste courte du JSON>
- Statuts : <répartition du JSON>
- Principaux auteurs ou groupes : <liste courte du JSON>
- Filtres déclencheurs : <liste courte du JSON>

**Priorités**
1. [<niveau fourni>] <signal prioritaire>
2. [<niveau fourni>] <signal suivant>
3. [<niveau fourni>] <signal suivant>

**Amendements à ouvrir**
- <lien Markdown> — <auteur, groupe, statut, résumé en une phrase>
- <lien Markdown> — <auteur, groupe, statut, résumé en une phrase>
- <lien Markdown> — <auteur, groupe, statut, résumé en une phrase>

**Limites**
<Une phrase maximum si nécessaire, sinon omettre la section.>"""


def _entetes() -> dict[str, str]:
    """Construire les en-têtes d'authentification Albert depuis l'environnement.

    Returns
    -------
    dict[str, str]
        En-têtes ``Authorization`` (Bearer) et ``Content-Type``.

    Raises
    ------
    RuntimeError
        Si la variable d'environnement ``ALBERT_API_KEY`` est absente.
    """
    cle = os.environ.get("ALBERT_API_KEY")
    if not cle:
        msg = "ALBERT_API_KEY absente de l'environnement (voir .env.example)"
        raise RuntimeError(msg)
    return {"Authorization": f"Bearer {cle}", "Content-Type": "application/json"}


def url_amendement(uid: str, *, legislature: int = 17) -> str:
    """Construire l'URL publique d'un amendement depuis son uid AN.

    Parameters
    ----------
    uid : str
        Identifiant AN, ex. ``AMANR5L17PO883517B2841P0D1N001018``.
    legislature : int, default=17
        Numéro de législature du segment ``/dyn/{leg}/``.

    Returns
    -------
    str
        URL sur assemblee-nationale.fr. Le LLM ne construit jamais d'URL :
        seule cette fonction le fait, côté Python.

    Raises
    ------
    ValueError
        Si ``uid`` est vide.

    Examples
    --------
    >>> url_amendement("AMANR5L17PO883517B2841P0D1N001018")
    'https://www.assemblee-nationale.fr/dyn/17/amendements/AMANR5L17PO883517B2841P0D1N001018'
    """
    if not uid:
        msg = "uid vide : impossible de construire l'URL"
        raise ValueError(msg)
    return f"https://www.assemblee-nationale.fr/dyn/{legislature}/amendements/{uid}"


def _est_suivi(amendement: dict[str, Any], contexte: dict[str, Any]) -> bool:
    """Tester si l'auteur de l'amendement figure parmi les députés suivis."""
    noms = (contexte.get("veille_noms") or "").strip()
    if not noms:
        return False
    auteur = (amendement.get("auteur_nom") or "").casefold()
    return any(n.strip().casefold() in auteur or auteur in n.strip().casefold()
               for n in noms.split(",") if n.strip())


def niveau_priorite(amendement: dict[str, Any], contexte: dict[str, Any]) -> str:
    """Attribuer un niveau de priorité déterministe à un amendement.

    Forte : sort notable (adopté, rejeté, retiré, irrecevable, tombé) ou
    auteur suivi. Moyenne : plusieurs filtres déclencheurs. Faible : le reste.

    Parameters
    ----------
    amendement : dict[str, Any]
        Ligne Grist (schéma Requete_1) ; champs utilisés :
        ``sortAmendement``, ``auteur_nom``, ``filtres_trouves``.
    contexte : dict[str, Any]
        Ligne de la veille ; champ utilisé : ``veille_noms``.

    Returns
    -------
    str
        ``"Forte"``, ``"Moyenne"`` ou ``"Faible"``. Le LLM reprend ce
        niveau tel quel, il ne le rejuge pas.

    Examples
    --------
    >>> niveau_priorite({"sortAmendement": "Adopté", "filtres_trouves": ""}, {})
    'Forte'
    >>> niveau_priorite({"sortAmendement": "En traitement",
    ...                  "filtres_trouves": "['a:x', 'b:y']"}, {})
    'Moyenne'
    """
    sort = (amendement.get("sortAmendement") or "").casefold()
    if any(s in sort for s in SORTS_NOTABLES) or _est_suivi(amendement, contexte):
        return "Forte"
    filtres = amendement.get("filtres_trouves") or ""
    if filtres.count(":") >= 2:
        return "Moyenne"
    return "Faible"


def ordonner_par_pertinence(
    amendements: list[dict[str, Any]],
    contexte: dict[str, Any],
    *,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Ordonner les amendements par pertinence sémantique via /v1/rerank.

    La query est l'``objectif`` de la veille, à défaut ``veille_termes``.
    Sans query, sans exposé exploitable ou si l'appel échoue, repli
    déterministe : tri par ``dateDepot`` décroissante. Les amendements à
    exposé vide (refusés par le reranker, ``minLength: 1``) sont placés
    en fin de liste.

    Parameters
    ----------
    amendements : list[dict[str, Any]]
        Lignes Grist du jour pour une veille.
    contexte : dict[str, Any]
        Ligne de la veille ; champs utilisés : ``objectif``, ``veille_termes``.
    session : requests.Session | None, default=None
        Session HTTP réutilisable (tests, pooling). ``None`` = requests direct.

    Returns
    -------
    list[dict[str, Any]]
        Les mêmes dicts, réordonnés. Jamais d'exception : le repli par
        date est la garantie que B4 ne bloque pas le digest.
    """
    tri_date = sorted(amendements,
                      key=lambda a: a.get("dateDepot") or "", reverse=True)
    query = (contexte.get("objectif") or contexte.get("veille_termes") or "").strip()
    if not query or len(amendements) < 2:
        return tri_date

    avec_expose = [a for a in amendements if (a.get("exposeSommaire") or "").strip()]
    sans_expose = [a for a in amendements if not (a.get("exposeSommaire") or "").strip()]
    if not avec_expose:
        return tri_date

    http = session or requests
    try:
        r = http.post(
            f"{ALBERT_BASE_URL}/rerank",
            headers=_entetes(),
            json={
                "model": MODELE_RERANK,
                "query": query,
                "documents": [a["exposeSommaire"][:MAX_CHARS_RERANK]
                              for a in avec_expose],
            },
            timeout=TIMEOUT_S,
        )
        r.raise_for_status()
        resultats = r.json()["results"]  # triés par score décroissant
        ordonnes = [avec_expose[res["index"]] for res in resultats]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return tri_date
    return ordonnes + sorted(sans_expose,
                             key=lambda a: a.get("dateDepot") or "", reverse=True)


def construire_stats(amendements: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculer le JSON de statistiques, seule source autorisée de chiffres.

    Parameters
    ----------
    amendements : list[dict[str, Any]]
        Lignes Grist du jour pour une veille.

    Returns
    -------
    dict[str, Any]
        ``total``, ``par_statut``, ``par_dossier``, ``par_groupe``,
        ``principaux_auteurs`` (top 5), ``filtres_declencheurs``.

    Examples
    --------
    >>> construire_stats([])["total"]
    0
    """
    def top(cle: str, n: int = 5) -> dict[str, int]:
        return dict(Counter(a.get(cle) or "inconnu" for a in amendements).most_common(n))

    return {
        "total": len(amendements),
        "par_statut": top("sortAmendement", 10),
        "par_dossier": top("titre_dossier_court"),
        "par_groupe": top("groupe_politique_abrege"),
        "principaux_auteurs": top("auteur_nom"),
        "filtres_declencheurs": top("filtres_trouves", 10),
    }


def _ligne_courte(a: dict[str, Any]) -> str:
    """Formater un amendement non prioritaire en une ligne."""
    return (f"- {a.get('uid', '?')} | {a.get('auteur_prenom', '')} "
            f"{a.get('auteur_nom', '')} ({a.get('groupe_politique_abrege', '?')}) | "
            f"{a.get('sortAmendement', '?')} | {a.get('titre_dossier_court', '?')}")


def _bloc_prioritaire(a: dict[str, Any], niveau: str) -> str:
    """Formater un amendement prioritaire en texte intégral pour le prompt."""
    return "\n".join([
        f"### {a.get('uid', '?')} [{niveau}]",
        f"URL : {url_amendement(a['uid']) if a.get('uid') else 'non disponible'}",
        f"Auteur : {a.get('auteur_civ', '')} {a.get('auteur_prenom', '')} "
        f"{a.get('auteur_nom', '')} ({a.get('groupe_politique_abrege', '?')}) — "
        f"{a.get('nombreCoSignataires', 0)} cosignataires",
        f"Dossier : {a.get('titre_dossier_court', '?')} | "
        f"Statut : {a.get('sortAmendement', '?')} | "
        f"Déposé : {a.get('dateDepot', '?')} | "
        f"Filtres : {a.get('filtres_trouves', '')}",
        f"Dispositif : {a.get('dispositif', '')}",
        f"Exposé sommaire : {a.get('exposeSommaire', '')}",
    ])


def construire_message_utilisateur(
    contexte: dict[str, Any],
    stats: dict[str, Any],
    prioritaires: list[tuple[dict[str, Any], str]],
    autres: list[dict[str, Any]],
) -> str:
    """Assembler le message utilisateur envoyé au modèle de chat.

    Parameters
    ----------
    contexte : dict[str, Any]
        Ligne de la veille (nom, objectif, termes, députés suivis).
    stats : dict[str, Any]
        Sortie de :func:`construire_stats`.
    prioritaires : list[tuple[dict[str, Any], str]]
        Paires (amendement, niveau) en texte intégral, déjà ordonnées.
    autres : list[dict[str, Any]]
        Le reste, résumé en une ligne chacun.

    Returns
    -------
    str
        Blocs concaténés : contexte JSON, stats JSON, amendements.
    """
    ctx = {k: contexte.get(k) for k in
           ("veille_nom", "objectif", "veille_termes", "veille_noms",
            "veille_dossiers", "jour_veille")}
    parties = [
        "Contexte de veille\n" + json.dumps(ctx, ensure_ascii=False, indent=1),
        "Statistiques calculées (seule source de chiffres)\n"
        + json.dumps(stats, ensure_ascii=False, indent=1),
        f"Amendements prioritaires en texte intégral "
        f"({len(prioritaires)} sur {stats['total']} détectés)\n"
        + "\n\n".join(_bloc_prioritaire(a, n) for a, n in prioritaires),
    ]
    if autres:
        parties.append(f"Autres amendements ({len(autres)}), une ligne chacun\n"
                       + "\n".join(_ligne_courte(a) for a in autres))
    return "\n\n---\n\n".join(parties)


def message_secours(contexte: dict[str, Any], stats: dict[str, Any],
                    prioritaires: list[tuple[dict[str, Any], str]]) -> str:
    """Construire le digest déterministe quand le chat Albert est indisponible.

    Le message part quand même : bandeau d'échec, chiffres clés issus des
    stats Python, top des prioritaires avec liens. Aucune prose générée.

    Parameters
    ----------
    contexte : dict[str, Any]
        Ligne de la veille.
    stats : dict[str, Any]
        Sortie de :func:`construire_stats`.
    prioritaires : list[tuple[dict[str, Any], str]]
        Paires (amendement, niveau) déjà ordonnées.

    Returns
    -------
    str
        Message Tchap markdown de secours.
    """
    lignes = [
        f"📌 Veille : {contexte.get('veille_nom', '?')}",
        "",
        "⚠️ La synthèse automatique a échoué (Albert indisponible ou quota "
        "atteint) : message généré sans rédaction.",
        "",
        "**Chiffres clés**",
        f"- Amendements détectés : {stats['total']}",
        f"- Statuts : {stats['par_statut']}",
        f"- Dossiers : {list(stats['par_dossier'])}",
        "",
        "**Amendements à ouvrir**",
    ]
    for a, niveau in prioritaires[:5]:
        lignes.append(
            f"- [{a.get('uid', '?')}]({url_amendement(a['uid'])}) [{niveau}] — "
            f"{a.get('auteur_prenom', '')} {a.get('auteur_nom', '')} "
            f"({a.get('groupe_politique_abrege', '?')}), "
            f"{a.get('sortAmendement', '?')}")
    return "\n".join(lignes)


def generer_message(
    contexte: dict[str, Any],
    amendements: list[dict[str, Any]],
    *,
    k: int = K_TEXTE_INTEGRAL,
    modele: str = MODELE_CHAT,
    session: requests.Session | None = None,
) -> str:
    """Générer le message Tchap complet d'une veille pour la journée.

    Point d'entrée de B4, appelé par run.py une fois par veille active.
    Enchaîne : stats Python → ordre par rerank (repli date) → niveaux
    déterministes → appel chat → repli :func:`message_secours` si échec.

    Parameters
    ----------
    contexte : dict[str, Any]
        Ligne Grist de la veille (``veille_nom``, ``objectif``, ...).
    amendements : list[dict[str, Any]]
        Lignes Grist `resultats` du jour pour cette veille (schéma
        Requete_1). Liste vide = message fixe, aucun appel API.
    k : int, default=25
        Nombre d'amendements fournis en texte intégral au modèle.
    modele : str, default=MODELE_CHAT
        Identifiant du modèle de chat Albert (voir ``GET /v1/models``).
    session : requests.Session | None, default=None
        Session HTTP réutilisable (tests, pooling).

    Returns
    -------
    str
        Message Tchap markdown, jamais vide.

    Raises
    ------
    RuntimeError
        Si ``ALBERT_API_KEY`` est absente de l'environnement.

    Notes
    -----
    Deux appels réseau maximum par veille (rerank + chat), largement sous
    les quotas Expérimentation (50 RPM / 1000 RPD sur Mistral-Small).
    """
    if not amendements:
        return "Aucun amendement détecté aujourd'hui pour cette veille."

    stats = construire_stats(amendements)
    ordonnes = ordonner_par_pertinence(amendements, contexte, session=session)
    prioritaires = [(a, niveau_priorite(a, contexte)) for a in ordonnes[:k]]
    autres = ordonnes[k:]

    http = session or requests
    try:
        r = http.post(
            f"{ALBERT_BASE_URL}/chat/completions",
            headers=_entetes(),
            json={
                "model": modele,
                "temperature": 0.2,
                "max_completion_tokens": 2500,
                "messages": [
                    {"role": "system", "content": PROMPT_SYSTEME},
                    {"role": "user", "content": construire_message_utilisateur(
                        contexte, stats, prioritaires, autres)},
                ],
            },
            timeout=TIMEOUT_S * 2,
        )
        r.raise_for_status()
        contenu = r.json()["choices"][0]["message"]["content"]
        if not (contenu or "").strip():
            msg = "réponse chat vide"
            raise ValueError(msg)
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return message_secours(contexte, stats, prioritaires)
    return contenu.strip()
