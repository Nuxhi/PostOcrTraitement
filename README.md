# POST-OCR M3C - Correction LLM de documents historiques

## 1) Principe du projet

Ce projet est une experimentation de **post-traitement OCR** sur des documents historiques de la base **M3C**.

Contexte:
- Les documents ont deja ete passes en OCR en amont (ex: Tesseract).
- Ce projet ne fait pas l'OCR initial.
- Il se concentre sur l'etape **POST-OCR**: detection de qualite du texte OCR, puis correction selective avec LLM.

Objectif:
- Recuperer un document M3C (metadonnees + PDF),
- Extraire le texte page par page,
- Evaluer la qualite OCR avec des algorithmes + un classifieur LLM,
- Ne corriger avec LLM que les pages jugees necessaires,
- Produire un fichier de sortie exploitable avec trace du modele et de l'opinion de fidelite.

---

## 2) Idee cle: correction selective (et non systematique)

Le projet applique une regle simple:

- si la page est estimee **clean** (propre): on ne corrige pas, on conserve le texte tel quel,
- si la page est estimee **medium** ou **dirty**: on envoie la page a un LLM pour correction OCR,
- la correction est ensuite verifiee par un second appel LLM (fidele / doute / altere).

Cela permet d'eviter des modifications inutiles sur des pages deja propres et de concentrer le cout de correction sur les zones a risque.

---

## 3) Pipeline fonctionnel

1. L'utilisateur fournit une URL d'article M3C.
2. Le systeme extrait le contexte documentaire (titre, description, date, langue, etc.).
3. Le PDF est localise dans la page (via navigateur headless), puis telecharge.
4. Le PDF est lu page par page.
5. Pour chaque page:
	 - calcul d'un score de qualite OCR (heuristiques + lexical + label LLM),
	 - decision clean/medium/dirty,
	 - correction LLM seulement si necessaire,
	 - verification de fidelite,
	 - ecriture dans un fichier de sortie.

---

## 4) Architecture du code

- `main.py`
	- point d'entree,
	- orchestration globale,
	- gestion menu CLI,
	- appel correction + verification LLM,
	- ecriture des sorties.

- `app/ContexteHelper.py`
	- scraping des metadonnees depuis la page M3C (`requests` + `BeautifulSoup`).

- `app/PdfDownloader.py`
	- recuperation de l'URL PDF dynamique via `selenium` headless,
	- telechargement et sauvegarde du PDF.

- `app/PdfChunking.py`
	- lecture PDF avec `pypdf`,
	- extraction du texte page par page.

- `app/MetricsCerWer.py`
	- coeur de l'evaluation qualite OCR,
	- heuristiques de bruit OCR,
	- signal lexical (`wordfreq` + `Levenshtein`),
	- classification LLM `clean/medium/dirty`,
	- fusion des signaux et label final.

- `app/SystemPrompt.py`
	- prompts systemes pour:
		- correction OCR,
		- verification de fidelite,
		- classification qualite OCR.

- `app/CheckModel.py`
	- verification/pull du modele Ollama local.

- `app/headers.py`
	- en-tetes HTTP utilises pour les requetes web.

---

## 5) Evaluation de qualite OCR (comment la decision est prise)

Le module `MetricsCerWer` combine 3 familles de signaux:

1. **Heuristiques OCR**
	 - caracteres/symboles suspects,
	 - mots casses,
	 - densite d'erreurs,
	 - repetitions anormales,
	 - motifs OCR subtils.

2. **Signal lexical**
	 - frequence de mots (`wordfreq`),
	 - distance a des mots courants (`Levenshtein`).

3. **Signal LLM**
	 - classification de la page en `clean`, `medium`, `dirty`.

Puis une fusion ponderee produit un label final. Ce label pilote la logique:

- `clean` -> pas de correction,
- `medium` / `dirty` -> correction LLM.

---

## 6) Utilisation des LLM

Le projet utilise `ollama` localement pour 3 usages distincts:

1. **Classification qualite OCR**
	 - prompt court de classification,
	 - sortie attendue: `clean`, `medium`, `dirty`.

2. **Correction OCR**
	 - prompt strict: corriger uniquement les erreurs OCR evidentes,
	 - conserver sens, structure, ordre des mots, et style historique.

3. **Verification de fidelite**
	 - compare texte original OCR et texte corrige,
	 - sortie attendue: `fidele`, `doute`, `altere`.

---

## 7) Prerequis

- Python 3.10+
- Ollama installe et operationnel en local
- Chrome + ChromeDriver compatibles (pour Selenium)

Dependances Python (voir `requirements.txt`):
- `ollama`
- `requests`
- `beautifulsoup4`
- `selenium`
- `pypdf`
- `wordfreq`
- `Levenshtein`
- `jiwer`

---

## 8) Installation rapide

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Lancement:

```bash
python main.py
```

Au demarrage, le projet verifie si le modele Ollama choisi est present localement et tente de le recuperer sinon.

---

## 9) Fichiers de sortie

Les resultats sont ecrits dans le dossier `output/`.

Chaque bloc contient notamment:
- le modele utilise,
- l'opinion de fidelite (`fidele`, `doute`, `altere`),
- le numero de page,
- le texte final (corrige ou non selon le label qualite).

---

## 10) Limites actuelles

- Projet experimental (etat alpha), non encore industrialise.
- La qualite depend du modele LLM local et de ses prompts.
- Le scraping est sensible aux evolutions HTML/JS de la plateforme M3C.
- La logique de score et les seuils peuvent encore etre calibres.
- Le projet suppose une etape OCR amont deja effectuee.

---

## 11) Perspectives

- Ajouter une evaluation automatique plus complete (CER/WER de reference si ground truth disponible).
- Versionner et comparer plusieurs strategies de prompts.
- Ameliorer la robustesse du telechargement PDF.
- Produire des rapports de qualite consolides (par document / par collection).

---

## 12) Resume en une phrase

Ce projet teste une approche **POST-OCR selective** pour corpus historiques M3C: **on scrape, on telecharge, on mesure la qualite OCR, on corrige uniquement les pages necessaires avec LLM, puis on trace la fidelite en sortie**.