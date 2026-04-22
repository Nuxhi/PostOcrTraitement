from ollama import chat, ChatResponse
import re
import Levenshtein
from wordfreq import zipf_frequency, top_n_list


try:
    import app.SystemPrompt as SystemPrompt
except ModuleNotFoundError:
    import SystemPrompt as SystemPrompt

try:
    import app.ContexteHelper as ContexteHelper
except ModuleNotFoundError:
    import ContexteHelper as ContexteHelper

import threading

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

ACTIVE_LANG = "fr"
COMMON_WORDS = set(top_n_list(ACTIVE_LANG, 5000))
ACTIVE_MODEL = "Mistral"

def getLangCode(url):
    """Return a supported language code inferred from article metadata."""
    frl = {"fr", "français", "francais"}

    langue_raw = ContexteHelper.getInfo(url, 'langue')
    if not langue_raw:
        return "fr"

    langues = [part.strip().lower() for part in str(langue_raw).split(";") if part.strip()]
    if not langues:
        return "fr"

    if len(langues) >= 2 and langues[1] in frl:
        return "fr"

    langue = langues[0]

    lang_code = LANG_MAP.get(langue, "fr")

    if lang_code == "co":   # corse
        return "it"

    if lang_code == "la":   # latin
        return "fr"

    return lang_code

def configureArticleLanguage(url: str) -> str:
    """Configure active lexical language from article URL."""
    global ACTIVE_LANG, COMMON_WORDS
    ACTIVE_LANG = getLangCode(url)
    COMMON_WORDS = set(top_n_list(ACTIVE_LANG, 5000))
    return ACTIVE_LANG


def configureModel(model_name: str) -> str:
    """Configure active LLM model for OCR classification."""
    global ACTIVE_MODEL
    if model_name:
        ACTIVE_MODEL = str(model_name).strip()
    return ACTIVE_MODEL

# =========================
# NORMALISATION
# =========================

def normalize(text: str) -> str:
    """Lowercase and sanitize OCR text for stable token processing."""
    text = text.lower()
    text = re.sub(r"[^\w\sàâéèêëîïôûùüç]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()



# =========================
# HEURISTIQUES OCR
# =========================

def ocrNoiseScore(text):
    """Estimate raw OCR noise density from simple artifact patterns."""
    patterns = [r"[~]", r"[()]", r"\d", r"[A-Za-z]{2,}\d", r"\d+[A-Za-z]{2,}", r"\s{2,}"]
    return sum(len(re.findall(p, text)) for p in patterns) / max(len(text), 1)

def brokenWordRatio(text):
    """Return ratio of tokens that look structurally broken."""
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

def repetitionScore(text):
    """Measure repeated-character artifacts in the OCR text."""
    repeats = re.findall(r"(.)\1{2,}", text)
    return len(repeats) / max(len(text), 1)

def subtleOcrPatterns(text):
    """Capture subtle OCR confusion motifs not covered by coarse rules."""
    patterns = [
        r"[a-z]{1}[A-Z]{1}[a-z]+",
        r"[a-z]{2,}[~][a-z]*",
        r"[il1]{3,}",
        r"[rn]{2,}",
    ]
    return sum(len(re.findall(p, text)) for p in patterns) / max(len(text), 1)

def ocrErrorDensity(text):
    """Estimate per-word OCR error density using layered regex heuristics."""
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

def qualityScore(text):
    """Compute a weighted heuristic OCR quality score in [0, 1]."""
    text = normalize(text)

    noise = ocrNoiseScore(text)
    broken = brokenWordRatio(text)
    density = ocrErrorDensity(text)
    repetition = repetitionScore(text)
    subtle = subtleOcrPatterns(text)

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

def lexicalPenalty(text):
    """Estimate lexical anomaly penalty using frequency and edit distance."""
    words = normalize(text).split()
    if not words:
        return 0

    penalty = 0
    checked = 0

    for w in words:
        if len(w) < 4:
            continue

        if zipf_frequency(w, ACTIVE_LANG) > 2:
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

def llmClassify(text):
    """Ask the LLM for a discrete OCR quality label."""
    response: ChatResponse = chat(
        model=ACTIVE_MODEL,
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

def llmToScore(label):
    """Map an LLM quality label to a numeric score."""
    return {
        "clean": 1.0,
        "medium": 0.6,
        "dirty": 0.2
    }.get(label, 0.5)

# =========================
# SCORE FINAL FUSION
# =========================

def _finalFusion(text):
    """Run parallel scoring (algo + LLM) and return fused score and label."""
    algo_results = {}
    llm_results = {}
    errors = []

    def algoWorker():
        print("[MERICSCERWER] - [WORKER ALGO]")
        try:
            algo_results["h"] = qualityScore(text)
            algo_results["lex"] = 1 - lexicalPenalty(text)
        except Exception as exc:
            errors.append(exc)

    def llmWorker():
        print("[MERICSCERWER] - [WORKER LLM]")
        try:
            llm_label_local = llmClassify(text)
            llm_results["llm_label"] = llm_label_local
            llm_results["llm_score"] = llmToScore(llm_label_local)
        except Exception as exc:
            errors.append(exc)

    algo_thread = threading.Thread(target=algoWorker, name="algo-worker")
    llm_thread = threading.Thread(target=llmWorker, name="llm-worker")

    algo_thread.start()
    llm_thread.start()

    algo_thread.join()
    llm_thread.join()

    if errors:
        raise errors[0]

    h = algo_results["h"]
    lex = algo_results["lex"]
    llm_label = llm_results["llm_label"]
    llm_score = llm_results["llm_score"]

    algo_score = 0.55 * h + 0.30 * lex
    score = 0.55 * h + 0.30 * lex + 0.15 * llm_score

    disagreement = abs(h - llm_score)
    if disagreement > 0.4:
        score *= 0.8

    if llm_label == "dirty" and score < 0.6:
        final_label_value = "dirty"
    elif score > 0.75:
        final_label_value = "clean"
    elif score > 0.5:
        final_label_value = "medium"
    else:
        final_label_value = "dirty"

    return score, final_label_value, llm_label, algo_score


def scoreDetails(text):
    """Return all scoring details needed by the caller."""
    final_score, final_label_value, llm_label, algo_score = _finalFusion(text)
    return {
        "algo_score": algo_score,
        "llm_label": llm_label,
        "final_score": final_score,
        "final_label_value": final_label_value,
    }
