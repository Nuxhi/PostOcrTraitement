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
    patterns = [r"[~]", r"[()]", r"\d", r"[A-Za-z]{2,}\d", r"\d+[A-Za-z]{2,}", r"\s{2,}"]
    return sum(len(re.findall(p, text)) for p in patterns) / max(len(text), 1)

def broken_word_ratio(text):
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
    repeats = re.findall(r"(.)\1{2,}", text)
    return len(repeats) / max(len(text), 1)

def subtle_ocr_patterns(text):
    patterns = [
        r"[a-z]{1}[A-Z]{1}[a-z]+",
        r"[a-z]{2,}[~][a-z]*",
        r"[il1]{3,}",
        r"[rn]{2,}",
    ]
    return sum(len(re.findall(p, text)) for p in patterns) / max(len(text), 1)

def ocr_error_density(text):
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
    return {
        "clean": 1.0,
        "medium": 0.6,
        "dirty": 0.2
    }.get(label, 0.5)

# =========================
# SCORE FINAL FUSION
# =========================

def final_quality_score(text):
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