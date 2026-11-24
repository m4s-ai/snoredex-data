"""Check the printed collector number against the assigned printing with Tesseract, offline (#658).

A guard, never evidence: a reading that contradicts the printing stops intake until the owner
corrects the assignment or confirms it; a number Tesseract cannot read stops nothing. Measured in #655
on 272 gallery photos: read exactly in 58 %, not read in 36 %, misread in 3 %. It cannot tell apart
variants with the same number (holo and reverse holo, stamps, patterns); that stays the owner's
assignment. The set code is not checked: Tesseract read it in only 18 %.
"""

import io
import os
import re
import shutil
import subprocess

from PIL import Image, ImageOps

# Tesseract's language data per catalogue language, English added for the digits and Latin codes
LANGUAGES = {"Japanese": "jpn", "German": "deu", "Chinese (Simplified)": "chi_sim",
             "Chinese (Traditional)": "chi_tra", "Korean": "kor", "French": "fra", "Italian": "ita",
             "Spanish (Europe)": "spa", "Spanish (Latin America)": "spa", "Portuguese": "por",
             "Indonesian": "ind", "Thai": "tha", "Russian": "rus", "Polish": "pol", "Dutch": "nld"}
CONFUSIONS = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "l": "1", "I": "1", "|": "1", "i": "1",
                            "S": "5", "B": "8", "Z": "2", "z": "2"})
# a printed number over its set size, with the letter prefixes some sets print (TG10/TG30, SV107/SV122)
PAIR = re.compile(r"[A-Z]{0,4}\d{1,3}/[A-Z]{0,4}\d{1,3}")


def tesseract():
    """The Tesseract binary: TESSERACT, else the one on PATH; None when it is not installed."""
    return os.environ.get("TESSERACT") or shutil.which("tesseract")


def installed_languages(binary):
    done = subprocess.run([binary, "--list-langs"], capture_output=True, text=True, timeout=30)
    return set(done.stdout.split()[1:]) if done.returncode == 0 else set()


def languages(binary, language):
    local = LANGUAGES.get(language)
    return f"{local}+eng" if local and local in installed_languages(binary) else "eng"


def bottom_band(face):
    """The lowest seventh of the card face, where the number has been printed since the e-Card era."""
    gray = face.convert("L")
    band = gray.crop((0, round(gray.height * 0.86), gray.width, gray.height))
    band = band.resize((2400, round(band.height * 2400 / band.width)), Image.LANCZOS)
    return ImageOps.autocontrast(band)


def binarized(image):
    """Otsu's threshold, the second reading that #655 found to add the most hits."""
    histogram = image.histogram()
    total = sum(histogram)
    weighted = sum(i * count for i, count in enumerate(histogram))
    best, threshold, below, below_weight = -1.0, 128, 0, 0
    for level, count in enumerate(histogram):
        below += count
        below_weight += level * count
        if below in (0, total):
            continue
        mean_low, mean_high = below_weight / below, (weighted - below_weight) / (total - below)
        spread = below * (total - below) * (mean_low - mean_high) ** 2
        if spread > best:
            best, threshold = spread, level
    return image.point(lambda value: 255 if value > threshold else 0)


def read_text(binary, image, lang):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    done = subprocess.run([binary, "stdin", "stdout", "-l", lang, "--psm", "11"], input=buffer.getvalue(),
                          capture_output=True, timeout=120)
    return done.stdout.decode("utf-8", "replace")


def expected(number, denominator):
    """The printed number: 066/080 or TG10/TG30 as printed, or the digits of a number printed without
    denominator (LOR 143 -> 143)."""
    number = re.sub(r"\s+", "", number or "")
    if denominator:
        return (number + "/" + re.sub(r"\s+", "", denominator)).upper()
    match = re.search(r"\d+$", number)
    return match[0] if match else number.upper()


def normal(text):
    """One reading's word in a comparable form: upper case, with the usual letter-for-digit confusions."""
    return text.upper().translate(CONFUSIONS)


def verdict(wanted, text):
    """match, mismatch or unreadable, with the numbers that were read. Words stay apart, so digits of
    neighbouring words never join into a number; a slash with spaces around it still joins."""
    tokens = [normal(token) for token in re.sub(r"\s*/\s*", "/", text).split()]
    pairs = sorted({pair for token in tokens for pair in PAIR.findall(token)})
    numerators = {re.sub(r"^[A-Z]*", "", pair.split("/")[0]).lstrip("0") for pair in pairs}
    seven = str.maketrans("7", "1")  # the small italic 1 and 7 are the commonest confusion
    wanted = normal(wanted).translate(seven)
    alone = any(re.search(rf"(?<!\d){re.escape(wanted)}(?!\d)", token.translate(seven)) for token in tokens)
    if alone or ("/" not in wanted and wanted.lstrip("0") in numerators):
        return "match", pairs
    return ("mismatch" if pairs else "unreadable"), pairs


def check(face, number, denominator, language):
    """The guard's result for one card face: {result, expected, read}; unavailable without Tesseract."""
    wanted = expected(number, denominator)
    binary = tesseract()
    if not binary:
        return {"result": "unavailable", "expected": wanted, "read": []}
    band = bottom_band(face)
    try:  # a missing binary or a hanging Tesseract is no reason to refuse the owner's corners
        lang = languages(binary, language)
        text = read_text(binary, band, lang) + "\n" + read_text(binary, binarized(band), lang)
    except (OSError, subprocess.TimeoutExpired):
        return {"result": "unavailable", "expected": wanted, "read": []}
    result, pairs = verdict(wanted, text)
    return {"result": result, "expected": wanted, "read": pairs}
