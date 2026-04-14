from ollama import chat, ChatResponse
import re
import Levenshtein
from wordfreq import zipf_frequency, top_n_list

import SystemPrompt
import ContexteHelper

url = "https://m3c.universita.corsica/s/fr/item/15"
LANG_MAP = {
    "français": "fr",
    "francais": "fr",
    "fr": "fr",

    "italien": "it",
    "it": "it",

    "anglais": "en",
    "english": "en",
    "us": "en",
    "en": "en",

    "corse": "co",

    "latin": "la"
}

def get_lang_code(url):
    """Resout le code langue utilise par les ressources lexicales d'un document.

    Principe:
    - Lit la metadonnee `langue` via le service de contexte du document.
    - Conserve uniquement la premiere langue si plusieurs valeurs sont separees par `;`.
    - Convertit les libelles humains en codes courts via `LANG_MAP`.
    - Applique des fallback explicites pour les langues peu ou non supportees
      par `wordfreq`:
      - Corse (`co`) -> Italien (`it`).
      - Latin (`la`) -> Francais (`fr`).

    Args:
        url (str): URL du document utilisee pour recuperer les metadonnees.

    Returns:
        str: Code langue normalise compatible avec les outils lexicaux en aval.
        Retourne `"fr"` par defaut si la langue est absente ou inconnue.
    """
    langue = ContexteHelper.GetInfo(url, 'langue')
    langue = langue.split(";")[0]
    print(langue)

    if langue:
        langue = langue.lower().strip()
    else:
        return "fr"

    lang_code = LANG_MAP.get(langue, "fr")

    # fallback wordfreq
    if lang_code == "co":   # corse
        return "it"

    if lang_code == "la":   # latin
        return "fr"

    return lang_code

langue = get_lang_code(url)
# =========================
# NORMALISATION
# =========================

def normalize(text: str) -> str:
    """Normalise le texte OCR avant les analyses heuristiques et lexicales.

    Principe:
    - Passe le texte en minuscules.
    - Supprime la ponctuation et les symboles speciaux en conservant lettres,
      chiffres, espaces et caracteres accentues courants.
    - Reduit les espaces multiples a un seul espace.

    Args:
        text (str): Texte OCR brut.

    Returns:
        str: Texte nettoye avec une tokenisation plus stable.
    """
    text = text.lower()
    text = re.sub(r"[^\w\sàâéèêëîïôûùüç]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# =========================
# COMMON WORDS
# =========================

COMMON_WORDS = set(top_n_list(langue, 5000))

# =========================
# HEURISTIQUES OCR
# =========================

def ocr_noise_score(text):
    """Estime la densite de bruit OCR brut via des motifs explicites.

    Principe:
    - Compte les occurrences de symboles et structures souvent liees aux artefacts OCR
      (`~`, parentheses, chiffres dans les mots, espacements anormaux).
    - Divise le total par la longueur du texte pour obtenir une densite normalisee.

    Args:
        text (str): Texte d'entree, en general deja normalise.

    Returns:
        float: Densite de bruit dans `[0, +inf)`, plus faible = meilleur.
    """
    patterns = [r"[~]", r"[()]", r"\d", r"[A-Za-z]{2,}\d", r"\d+[A-Za-z]{2,}", r"\s{2,}"]
    return sum(len(re.findall(p, text)) for p in patterns) / max(len(text), 1)

def broken_word_ratio(text):
    """Mesure la proportion de mots qui semblent structurellement corrompus.

    Principe:
    - Decoupe le texte en tokens.
    - Marque les mots contenant des symboles OCR (`~`, `(`, `)`) ou de longues
      suites improbables de consonnes.
    - Retourne la proportion de mots marques.

    Args:
        text (str): Texte d'entree.

    Returns:
        float: Ratio dans `[0, 1]`; plus eleve = tokens plus suspects.
    """
    words = text.split()
    if not words:
        return 0

    broken = 0
    for w in words:
        if re.search(r"[~()]", w):
            broken += 1
        elif re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", w.lower()):
            broken += 1

    return broken / len(words)

def repetition_score(text):
    """Quantifie les artefacts suspects de repetition de caracteres.

    Principe:
    - Detecte les sequences ou un caractere est repete au moins trois fois.
    - Normalise le nombre de repetitions par la longueur du texte.

    Args:
        text (str): Texte d'entree.

    Returns:
        float: Densite de repetition; plus elevee = corruption OCR plus probable.
    """
    repeats = re.findall(r"(.)\1{2,}", text)
    return len(repeats) / max(len(text), 1)

def subtle_ocr_patterns(text):
    """Capture des anomalies OCR subtiles non couvertes par les regles grossieres.

    Principe:
    - Recherche des motifs de confusion OCR connus (melange de casse,
      sequences `il1`, grappes `rn`, tildes inserees dans les mots).
    - Retourne une densite normalisee par la longueur du texte.

    Args:
        text (str): Texte d'entree.

    Returns:
        float: Densite d'anomalies subtiles; plus faible = meilleur.
    """
    patterns = [
        r"[a-z]{1}[A-Z]{1}[a-z]+",
        r"[a-z]{2,}[~][a-z]*",
        r"[il1]{3,}",
        r"[rn]{2,}",
    ]
    return sum(len(re.findall(p, text)) for p in patterns) / max(len(text), 1)

def ocr_error_density(text):
    """Calcule la densite d'erreurs OCR au niveau mot via des regles en couches.

    Principe:
    - Parcourt les mots et marque les erreurs probables selon plusieurs tests:
      - melange lettres/chiffres (`a1`, `1a`),
      - artefacts de ponctuation OCR (`~`, parentheses),
      - longues suites de consonnes,
      - absence de voyelles sur des mots assez longs.
    - Les mots courts (`<= 2`) sont ignores pour la regle des voyelles.

    Args:
        text (str): Texte d'entree.

    Returns:
        float: Ratio de mots marques comme erreurs OCR, dans `[0, 1]`.
    """
    words = text.split()
    if not words:
        return 0

    errors = 0
    for w in words:
        if re.search(r"[a-zA-Z]\d|\d[a-zA-Z]", w):
            errors += 1
            continue
        if re.search(r"[~()]", w):
            errors += 1
            continue
        if re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", w.lower()):
            errors += 1
            continue
        if len(w) <= 2:
            continue

        vowels = len(re.findall(r"[aeiouyàâéèêëîïôûùü]", w.lower()))
        if vowels == 0:
            errors += 1

    return errors / len(words)

# =========================
# SCORE HEURISTIQUE DURCI
# =========================

def quality_score(text):
    """Agrege la qualite OCR heuristique en un score normalise unique.

    Principe:
    - Normalise d'abord le texte pour fiabiliser l'extraction des signaux.
    - Calcule cinq composantes heuristiques:
      - densite de bruit,
      - ratio de mots casses,
      - densite d'erreurs OCR,
      - densite de repetitions,
      - densite d'anomalies subtiles.
    - Construit une penalite ponderee puis la convertit en qualite via `1 - penalite`.
    - Borne la penalite a `1.0` pour conserver un score final dans `[0, 1]`.

    Args:
        text (str): Texte OCR brut.

    Returns:
        float: Score heuristique de qualite dans `[0, 1]`; plus eleve = meilleur.
    """
    text = normalize(text)

    noise = ocr_noise_score(text)
    broken = broken_word_ratio(text)
    density = ocr_error_density(text)
    repetition = repetition_score(text)
    subtle = subtle_ocr_patterns(text)

    penalty = (
        0.25 * noise +
        0.25 * broken +
        0.3 * density +
        0.1 * repetition +
        0.1 * subtle
    )

    return 1 - min(penalty, 1.0)

# =========================
# SIGNAL LEXICAL (IMPORTANT)
# =========================

def lexical_penalty(text):
    """Estime l'anormalite lexicale via frequence et distance d'edition.

    Principe:
    - Normalise et tokenise le texte.
    - Ignore les tokens courts (`len < 4`).
    - Pour chaque token, verifie d'abord la frequence dans le corpus (`zipf_frequency`).
      Les mots frequents sont consideres comme valides.
    - Pour les mots rares, compare a un sous-ensemble de mots communs de longueur
      proche et calcule la distance minimale de Levenshtein.
    - Un mot est penalise si le meilleur candidat reste eloigne (`>= 2`).

    Args:
        text (str): Texte d'entree.

    Returns:
        float: Ratio de penalite dans `[0, 1]`; plus faible = texte plus propre lexicalement.
    """
    words = normalize(text).split()
    if not words:
        return 0

    penalty = 0
    checked = 0

    for w in words:
        if len(w) < 4:
            continue

        if zipf_frequency(w, "fr") > 2:
            checked += 1
            continue

        candidates = [ref for ref in COMMON_WORDS if abs(len(ref) - len(w)) <= 2][:50]

        if not candidates:
            continue

        min_dist = min(Levenshtein.distance(w, ref) for ref in candidates)

        if min_dist >= 2:
            penalty += 1

        checked += 1

    return penalty / max(checked, 1)

# =========================
# LLM
# =========================

def llm_classify(text):
    """Demande au LLM de classer la qualite OCR en labels discrets.

    Principe:
    - Envoie un prompt deterministe (`temperature=0`) au modele.
    - Utilise un prompt systeme dedie decrivant les classes attendues.
    - Retourne le label en minuscules.

    Args:
        text (str): Texte OCR a classer.

    Returns:
        str: L'un des labels attendus (`clean`, `medium`, `dirty`) si le modele
        suit les consignes, sinon une valeur de fallback.
    """
    response: ChatResponse = chat(
        model='Mistral',
        options={
            "temperature": 0.0,
            "top_p": 0.1,
            "num_predict": 2,
        },
        messages=[
            {
                'role': 'system',
                'content': SystemPrompt.promptCerWer()
            },
            {
                'role': 'user',
                'content': f"texte : {text}"
            },
        ]
    )

    return response.message.content.strip().lower()

def llm_to_score(label):
    """Convertit un label LLM de qualite en score numerique.

    Principe:
    - Applique une table fixe label -> score:
      - `clean -> 1.0`
      - `medium -> 0.6`
      - `dirty -> 0.2`
    - Utilise `0.5` comme fallback neutre pour les labels inconnus.

    Args:
        label (str): Label produit par le LLM.

    Returns:
        float: Score numerique compatible avec la fusion ponderee.
    """
    return {
        "clean": 1.0,
        "medium": 0.6,
        "dirty": 0.2
    }.get(label, 0.5)

# =========================
# SCORE FINAL FUSION
# =========================

def final_quality_score(text):
    """Fusionne les signaux heuristique, lexical et LLM en un score final.

    Principe:
    - Calcule le score heuristique (`h`).
    - Convertit la penalite lexicale en qualite (`lex = 1 - penalite`).
    - Recupere le label LLM puis son score numerique.
    - Combine les trois composantes avec des poids fixes:
      - heuristique: `0.5`
      - lexical: `0.3`
      - llm: `0.2`
    - Applique une sous-pondération (`* 0.8`) si le desaccord entre heuristique
      et LLM est fort (`abs(h - llm_score) > 0.4`).

    Args:
        text (str): Texte OCR a evaluer.

    Returns:
        tuple[float, str]:
            - score final fusionne dans `[0, 1]` (avec penalite de desaccord),
            - label LLM utilise dans la chaine de decision.
    """
    h = quality_score(text)
    lex = 1 - lexical_penalty(text)

    llm_label = llm_classify(text)
    llm_score = llm_to_score(llm_label)

    # fusion pondérée
    score = 0.5 * h + 0.3 * lex + 0.2 * llm_score

    # pénalité si désaccord fort
    disagreement = abs(h - llm_score)

    if disagreement > 0.4:
        score *= 0.8

    return score, llm_label

# =========================
# LABEL FINAL
# =========================

def final_label(text):
    """Convertit le score fusionne en classe finale de qualite.

    Principe:
    - Part du score numerique fusionne et du label LLM.
    - Applique une regle conservative:
      si le LLM predit `dirty` et que le score est inferieur a `0.6`, retourne `dirty`.
    - Sinon applique des seuils:
      - `> 0.75`: `clean`
      - `> 0.5`: `medium`
      - sinon: `dirty`

    Args:
        text (str): Texte OCR a classer.

    Returns:
        str: Label final dans `{clean, medium, dirty}`.
    """
    score, llm_label = final_quality_score(text)

    if llm_label == "dirty" and score < 0.6:
        return "dirty"

    if score > 0.75:
        return "clean"
    elif score > 0.5:
        return "medium"
    else:
        return "dirty"

# =========================
# DEBUG COMPLET
# =========================

def debug(text):
    """Affiche les metriques intermediaires pour inspection et ajustement.

    Principe:
    - Recalcule chaque signal majeur de la chaine de scoring.
    - Affiche score heuristique, penalite lexicale, label LLM, score fusionne
      et classe finale dans un bloc lisible.

    Args:
        text (str): Texte OCR a analyser.

    Returns:
        None: Effet de bord, impression console pour le diagnostic.
    """
    h = quality_score(text)
    lex = lexical_penalty(text)
    llm = llm_classify(text)
    final_score, _ = final_quality_score(text)

    print("\n--- DEBUG OCR ---")
    print("TEXT:", text)
    print("heuristic:", round(h, 3))
    print("lexical penalty:", round(lex, 3))
    print("llm:", llm)
    print("final score:", round(final_score, 3))
    print("final label:", final_label(text))

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    txt = "Gioja de' cori e' sempre t'ho chiamattn,li per amari a lia ( 1), sojn (~) snrdu, e muttu ; Pattu (3) più chi nno paui unn dannatn, Sto in didr (4) ::'lferno, e Li dumaonu ajuttu. Oh ingratta donna, e parchl m'hai hurlattu, E quistn pettn parchi rhai [aruttu? ( 5 ) Ê medru (6) esseri amanti, e nun amattn Ch'esseri amanti'amatm, e po' tradnttn (7), Gioja, tu m' ha"
    #txt = "Salut Je sis Fabien"
    debug(txt)  