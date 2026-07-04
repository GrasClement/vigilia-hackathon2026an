# Design de la synthèse — bloc B2

Ce document est le contrat d'entrée de B4 (génération) : B4 implémente ce
qui est écrit ici, il n'improvise pas la structure du prompt. Bloc de
réflexion, aucun code — MÉTIER rédige, DEV/DATA relit pour vérifier que
c'est implémentable tel quel.

Le format du reste du digest (top 5 par veille, section évolutions, lien
Grist) est déjà acté dans `docs/architecture.md` (bloc B5) : ce document
ne couvre que le paragraphe de synthèse en tête de digest.

## À trancher pendant B2

- [ ] **Longueur et ton.** 3 à 5 phrases, mais sur quel registre — neutre
  informatif, ou orienté vers l'action ("à surveiller", "déjà voté") ?
- [ ] **Ordre des idées.** Par quoi commence la synthèse : le fait le plus
  significatif, un chiffre de volume, ou un rappel de l'objectif de la
  veille ?
- [ ] **Usage de `objectif`.** Comment la phrase d'intention de chaque
  veille (table `veilles`, colonne `objectif`) transforme le contenu :
  exemple, une veille avec l'objectif *"repérer les impacts budgétaires
  pour anticiper les amendements de crédits"* devrait produire une
  synthèse qui relie explicitement les documents détectés à un impact
  budgétaire, pas juste les lister.
- [ ] **Évolutions.** La synthèse mentionne-t-elle les changements de sort
  (`evolution`, alimentés par B1.5), ou se limite-t-elle aux nouveaux
  résultats du jour, les évolutions restant dans leur propre section du
  digest (B5) ?
- [ ] **Cas déluge (PLF).** Sur un jour à 200+ documents pour une veille,
  la synthèse annonce un volume et une tendance ("212 amendements déposés,
  majoritairement sur le volet fiscal") plutôt que de tenter un résumé
  exhaustif — à confirmer et à formuler précisément.
- [ ] **Veille sans objectif renseigné.** Comportement de repli : résumé
  neutre des extraits, sans prétendre à une intention.
- [ ] **Plusieurs veilles le même jour.** La synthèse couvre-t-elle toutes
  les veilles actives en un seul paragraphe, ou un paragraphe par veille
  avec résultats ? (impacte directement le prompt de B4 et la mise en page
  de B5)

## Gabarit de prompt (à valider, consommé tel quel par B4)

```
Système : Tu résumes en 3 à 5 phrases, en français, uniquement à partir
des extraits fournis. N'invente aucun fait absent des extraits. Pour
chaque veille, relie les documents détectés à l'objectif déclaré par
l'utilisateur quand il est renseigné.

Utilisateur : <pour chaque veille active du jour>
- Veille : <id> — objectif : <objectif ou "non renseigné">
  Extraits : <liste des `extrait` du jour, + `evolution` s'il y en a>
```

À ajuster une fois les premiers essais faits sur des veilles réelles (B3).

## Exemple annoté (à compléter avec un cas réel pendant B2/B4)

**Entrée** — veille `fiscalite-verte`, objectif : *"repérer les impacts
budgétaires pour anticiper les amendements de crédits"* ; extraits du
jour : deux amendements sur la fiscalité du gazole non routier.

**Sortie attendue** — un paragraphe qui nomme le nombre de documents,
relie leur contenu à l'impact budgétaire annoncé par l'objectif, et laisse
les citations exactes aux extraits déjà présents dans le digest (jamais
reformulées par la synthèse).

*(à remplacer par un exemple réel dès que B1 a produit des résultats sur
une veille de démonstration)*
