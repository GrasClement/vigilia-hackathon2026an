from collections.abc import Sequence
import polars as pl


def filtrer_amendements_mots_cles(
    df: pl.DataFrame,
    *,
    mots_expose: Sequence[str] | None = None,
    mots_dossier_ref_uid: Sequence[str] | None = None,
    mots_auteur_nom: Sequence[str] | None = None,
) -> pl.DataFrame:
    """
    Filtre avec une logique OU globale.

    Un amendement est gardé si au moins un mot est trouvé dans :
    - exposeSommaire ;
    - dossier_ref_uid ;
    - auteur_nom.

    Ajoute une colonne _filtres_trouves pour contrôler ce qui a matché.
    """

    if df.is_empty():
        return df

    def nettoyer_mots(mots: Sequence[str] | None) -> list[str]:
        if mots is None:
            return []

        return list(
            dict.fromkeys(
                mot.strip().lower()
                for mot in mots
                if isinstance(mot, str) and mot.strip()
            )
        )

    specs = {
        "exposeSommaire": nettoyer_mots(mots_expose),
        "dossier_ref_uid": nettoyer_mots(mots_dossier_ref_uid),
        "auteur_nom": nettoyer_mots(mots_auteur_nom),
    }

    specs = {
        col: mots
        for col, mots in specs.items()
        if mots and col in df.columns
    }

    if not specs:
        raise ValueError(
            "Aucun filtre exploitable. Vérifie les mots-clés et les colonnes disponibles."
        )

    expressions_match = []

    for col, mots in specs.items():
        texte_col = (
            pl.col(col)
            .cast(pl.String, strict=False)
            .fill_null("")
            .str.to_lowercase()
        )

        for mot in mots:
            expressions_match.append(
                pl.when(texte_col.str.contains(mot, literal=True))
                .then(pl.lit(f"{col}:{mot}"))
                .otherwise(None)
            )

    df_filtre = df.with_columns(
        pl.concat_list(expressions_match)
        .list.drop_nulls()
        .alias("_filtres_trouves")
    )

    return df_filtre.filter(
        pl.col("_filtres_trouves").list.len() > 0
    )