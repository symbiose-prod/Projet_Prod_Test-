# Ferment Station — Streamlit (multi-pages)

L'app lit **uniquement** les fichiers du repo (`/data`, `/assets`).  
Aucune importation locale n'est nécessaire.

## Structure
- `app.py` (accueil)
- `pages/01_Production.py`, `pages/02_Optimisation.py`, `pages/03_Fiche_de_ramasse.py`
- `common/design.py` (thème & UI)
- `common/data.py` (config & chemins)
- `core/optimizer.py` (algorithmes)
- `data/production.xlsx`, `data/flavor_map.csv`
- `assets/` (images produits & modèles)

## Lancer en local (optionnel)
```bash
pip install -r requirements.txt
streamlit run app.py

--

## 🚀 Déploiement sur Kinsta
### Fichiers requis
- `Procfile` (à la racine) :
web: streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT

- `requirements.txt` (dépendances Python)

### Étapes (sans environnement local)
1. Aller sur **my.kinsta.com** → **Applications** → **Créer une application**  
2. Source **GitHub** → autoriser l’accès à l’organisation `symbiose-prod`  
3. Sélectionner le dépôt `symbiose-prod/Projet-prod` et la branche `main`  
4. Laisser Kinsta détecter Python et la commande du `Procfile`  
5. Déployer

À la fin du build, Kinsta fournit une URL du type :  
`https://projet-prod-XXXX.kinsta.app`

### Variables d’environnement (Kinsta → Settings → Environment variables)
> Ne jamais commiter de secrets. Les mettre uniquement ici.

| Nom            | Exemple / Description                                  |
|----------------|---------------------------------------------------------|
| ENV            | `production`                                           |
| PORT           | `8080` (fourni par Kinsta)                             |
| GH_REPO        | `symbiose-prod/Projet-prod`                            |
| GH_BRANCH      | `main`                                                 |
| GH_PATH_MEMOIRE| `data/memoire_longue.json` (temporaire sans DB)        |
| GH_TOKEN       | (si l’app lit/écrit le repo)                           |
| SMTP_HOST      | `smtp-relay.brevo.com`                                 |
| SMTP_PORT      | `587`                                                  |
| SMTP_USER      | (compte service)                                       |
| SMTP_PASS      | (mot de passe SMTP)                                    |
| EMAIL_FROM     | `no-reply@symbiose.internal`                           |
| BREVO_API_KEY  | (si envoi via API Brevo)                               |

### Vérifications rapides après déploiement
- L’URL Kinsta affiche bien l’interface Streamlit ✅  
- Pas d’erreur d’import / de port (le `Procfile` force l’usage de `$PORT`)  
- Test d’envoi d’email (si configuré)  
