# Documentation — Tableau de bord Grist de visualisation des amendements

**Projet :** Veille parlementaire — Assemblée nationale
**Objet :** Guide de reproduction du tableau de bord de visualisation des amendements dans Grist
**Public visé :** Toute personne de l'équipe, sans prérequis technique

---

## Sommaire

1. [Présentation](#1-présentation)
2. [Prérequis : la table de données](#2-prérequis--la-table-de-données)
3. [Concept clé : la table de résumé](#3-concept-clé--la-table-de-résumé)
4. [Procédure : créer un graphique](#4-procédure--créer-un-graphique)
5. [Mise en forme d'un graphique](#5-mise-en-forme-dun-graphique)
6. [Liste des graphiques du tableau de bord](#6-liste-des-graphiques-du-tableau-de-bord)
7. [Résolution des problèmes courants](#7-résolution-des-problèmes-courants)
8. [Sauvegarde et réutilisation](#8-sauvegarde-et-réutilisation)
9. [Glossaire](#9-glossaire)

---

## 1. Présentation

Ce tableau de bord présente, sous forme de graphiques, les amendements parlementaires collectés par le projet. Il offre une lecture visuelle et immédiate de l'activité législative.

Les graphiques permettent de répondre à des questions telles que :

- Combien d'amendements pour chaque **sort** (adopté, rejeté, en traitement, à discuter…) ?
- Quels **groupes politiques** déposent le plus d'amendements ?

Le tableau de bord est construit entièrement avec les outils standard de Grist, sans code ni extension, conformément aux choix techniques du projet.

---

## 2. Prérequis : la table de données

Tous les graphiques reposent sur une table unique : **`Requete_2`**.

Il s'agit du jeu de données « propre » : les amendements y sont déjà nettoyés et organisés en colonnes simples, à raison d'une ligne par amendement. Cette table est alimentée en amont par le traitement de données de l'équipe.

> **Important :** cette table ne doit pas être modifiée manuellement. Le tableau de bord se contente de la lire pour produire les graphiques.

---

## 3. Concept clé : la table de résumé

Un graphique de type « nombre d'amendements par catégorie » nécessite de **compter** des lignes. Grist ne réalise pas ce comptage sur une table ordinaire : il faut d'abord créer une **table de résumé**, équivalent du tableau croisé dynamique d'un tableur.

Une table de résumé fonctionne en deux temps :

1. elle regroupe les amendements en catégories selon une colonne choisie (le « regroupement ») ;
2. elle crée automatiquement une colonne **`count`** indiquant le nombre d'amendements dans chaque catégorie.

Le comptage est déclenché par le symbole **Σ** (sigma), présent à côté du nom de la table au moment de la création du graphique. En son absence, aucune colonne `count` n'est générée et le graphique reste vide. **C'est la source d'erreur la plus fréquente.**

---

## 4. Procédure : créer un graphique

La procédure suivante s'applique à chacun des graphiques du tableau de bord.

1. Cliquer sur le bouton vert **Ajouter** (en haut à gauche).
2. Sélectionner **Ajouter une vue à la page**.
3. Dans la colonne *Choisir la vue*, choisir **Graphique**.
4. Dans la colonne *Choisir les données source*, repérer **`Requete_2`** et cliquer sur le symbole **Σ** situé à côté de son nom.
   *Cette étape est indispensable : le symbole Σ transforme la table en table de résumé.*
5. Dans la colonne *Grouper par*, cocher la colonne de regroupement souhaitée (voir la section 6).
6. Cliquer sur **Ajouter à la Page**.
7. Dans le panneau de configuration (à droite), à la section **SERIES**, cliquer sur **+ Ajouter une série** et sélectionner **`count`**.

Le graphique s'affiche alors avec ses barres.

---

## 5. Mise en forme d'un graphique

Une fois le graphique créé, les réglages suivants (panneau de droite) améliorent nettement sa lisibilité.

| Réglage | Emplacement | Effet |
|---|---|---|
| **Titre** | Clic sur le titre du graphique | Remplacer le nom technique par un intitulé clair (ex. « Amendements par sort ») |
| **Orientation horizontale** | Option *Orientation* → *Horizontal* | Rend lisibles les étiquettes longues (recommandé pour les groupes politiques) |
| **Tri décroissant** | Tri de la table de résumé sur `count` | Classe les barres de la plus grande à la plus petite |
| **Enregistrer** | Bouton vert *Enregistrer* sur le graphique | Fige les réglages effectués |

---

## 6. Liste des graphiques du tableau de bord

| Graphique | Colonne de regroupement | Série |
|---|---|---|
| **Amendements par sort** | `sortAmendement` | `count` |
| **Amendements par groupe politique** | colonne du groupe politique (à plat) | `count` |

> **Note sur le graphique par groupe politique :** l'orientation horizontale est fortement recommandée, les noms de groupes étant longs et illisibles en vertical.

---

## 7. Résolution des problèmes courants

**La colonne `count` n'est pas proposée.**
Le graphique n'est pas basé sur une table de résumé. Vérifier que le titre du graphique contient des crochets, par exemple `Requete_2 [by sortAmendement]`. Si ce n'est pas le cas, recréer le graphique en veillant à cliquer sur le symbole **Σ** à l'étape 4.

**Le graphique reste vide ou plat.**
Vérifier qu'une série `count` a bien été ajoutée à la section SERIES. Sans série, aucune barre ne peut s'afficher.

**Un graphique par date n'affiche qu'une seule barre.**
Cela survient lorsque tous les amendements partagent la même date de dépôt. Dans ce cas, un graphique par jour n'apporte pas d'information exploitable.

**Le widget « Personnalisée » (Advanced charts / Plotly).**
Ce widget autorise le choix des couleurs mais requiert un accès complet au document et complexifie la maintenance. Le projet a fait le choix de s'en tenir aux graphiques standard. Ne pas l'utiliser sans décision d'équipe.

**Le choix des couleurs.**
Les graphiques standard attribuent les couleurs automatiquement et ne permettent pas de les définir manuellement. Il s'agit d'une limite connue de Grist, et non d'une erreur de manipulation.

---

## 8. Sauvegarde et réutilisation

Les options suivantes sont accessibles via le menu **Partager**, en haut à droite du document ouvert.

- **Duplicate Document** : crée une copie complète du document, données comprises. Recommandé comme sauvegarde de sécurité avant toute modification importante.
- **Save Copy** avec l'option **As Template** : conserve la structure et les graphiques sans les données. Recommandé pour fournir un modèle réutilisable sur un autre jeu d'amendements.

---

## 9. Glossaire

| Terme | Définition |
|---|---|
| **Table de résumé** | Table qui regroupe les lignes par catégorie et les compte automatiquement. Équivalent d'un tableau croisé dynamique. |
| **Σ (sigma)** | Symbole activant le comptage lors de la création d'un graphique. Transforme une table ordinaire en table de résumé. |
| **`count`** | Colonne générée automatiquement par une table de résumé, indiquant le nombre de lignes de chaque catégorie. |
| **Série** | Donnée tracée en hauteur des barres d'un graphique (ici, toujours `count`). |
| **Regroupement (Grouper par)** | Colonne qui définit les catégories du graphique (axe des abscisses). |
| **`Requete_2`** | Table de données nettoyée servant de source à tous les graphiques. |
