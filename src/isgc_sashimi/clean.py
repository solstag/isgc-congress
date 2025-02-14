#!/usr/bin/env python

"""
TODO:
- [ ] trouver les abstracts avec une ligne auteurs
- [x] ajouter une variable si l'abstract a été modifié ou pas

List of abstracts with some issue:

- 187, 661 (longuer de la ligne pas des majuscules)
- 1610 - trop de chiffres
- 1340, 1634, 1642 (ligne trop courte)
- 315, 873 biblio mais il y a l'année (ou DOI)
- 871 :P
- 1028 'authors acknowledge...'
- 1314 biblio sans année
- 'Abstract: ...' peut-être assouplir le critère (sans \n)
- 871 (table ronde), 1401
-- Majuscules (peut-être pas tous):
- 978, 1161 formule chimique pleine de majuscules
- 1205 ligne d'abstract avec majuscules
- 1701 plein d'acronymes
- première ligne toute en majuscule

"""

import re
import pandas as pd
from difflib import unified_diff
from itertools import permutations

CLEAN_REFLAGS = re.IGNORECASE | re.MULTILINE | re.DOTALL | re.VERBOSE


def clean_text(df):
    """
    Known untreated entries:
    - some title plus authors headers with no clear separation
    """

    def and_sections(re0, re1):
        return re0 + r"\s* (?: and | & ) \s*" + re1

    # Remove entries with no valid content
    unwanted_res = "^Lorem ipsum dolor sit amet"
    b_unwanted = df["abstract_text"].str.contains(unwanted_res)
    clean_df = df[~b_unwanted]
    b_unwanted = df["abstract_text"].map(len).lt(100)
    clean_df = df[~b_unwanted]

    # Section names to be removed
    section_names_res = [
        r"backgrounds?",
        r"conclusions?",
        r"discussions?",
        r"experiments?",
        r"experimental",
        r"intro",
        r"introductions?",
        r"materials?",
        r"methods?",
        r"motivation?",
        r"perspectives?",
        r"prospects?",
        r"objectives?",
        r"outlooks?",
        r"overview?",
        r"results?",
        r"key\ results?",
        r"significance",
        r"summary",
    ]
    section_names_re = r"|".join(
        [and_sections(x, y) for x, y in permutations(section_names_res, 2)]
        + section_names_res
    )
    section_numbering_re = r"[^\n\w]* (?: \d? [^\n\w]* )"
    # Remove invalid content from entries
    unclean_from_start_of_text_res = [
        r"(?: ^ | .* \n)" + section_numbering_re + r"abstract [^\n\w,]* [\n:]",
    ]
    unclean_res = [
        r"^" + section_numbering_re + r"keys?\ ?words? (?: [^\n\w]* \n )? [^\n]*",
        r"^"
        + section_numbering_re
        + r"(?:"
        + section_names_re
        + r") (?: \ * section)? (?: [^\n\w]* \n | \s* [^\n\w\s,&]+ )",
    ]
    unclean_until_end_of_text_res = [
        r"^" + section_numbering_re + r"ac?knowled?ge?m?ents? :? .*",
        r"^" + section_numbering_re + r"r[eé]f[eé]rences? \s* :? .*",
        r"^ [^\n\w]* [12] [^\n\w]+ \w [^\n]+ (?<!\d)(?:1[6789]|20)[0-9]{2}(?!\d) .*",
    ]
    unclean_rx = re.compile(
        pattern=r"|".join(
            unclean_from_start_of_text_res + unclean_res + unclean_until_end_of_text_res
        ),
        flags=CLEAN_REFLAGS,
    )
    clean_abstract_text = clean_df["abstract_text"].str.replace(unclean_rx, "")

    # Remove even more funding info (max 61) excluding (10) manually identified wrong matches
    clean_extra_funding_rx = re.compile(
        r"(^ [^\n]*"
        r"(?: fund[eis] | financ | supported\ by | support\ of | support\ from | grant )"
        r"[^\n]* \s* ) \Z",
        flags=CLEAN_REFLAGS,
    )
    up_index = clean_abstract_text.index.difference(
        [23, 968, 999, 1243, 1373, 1416, 1469, 1560, 1700, 1710]
    )
    clean_abstract_text = clean_abstract_text.loc[up_index].str.replace(
        clean_extra_funding_rx, ""
    )

    return clean_abstract_text


# TODO: find a use for these in clean_text()?
def is_author_affiliation(line, verbose=False):
    author_words = r"and of at in de et und".split()
    words_re = fr'\b(?:{"|".join(author_words)})\b'
    line = re.sub(r"[-\.]", " ", line)
    line = re.sub(r",", " , ", line)
    line = re.sub(r"\d+", "", line)
    line = re.sub(r"[^\w\s,]*|\b[a-z]\b", "", line)
    words = line.split()
    point_words = [
        x for x in words if x[0].isupper() or x == "," or re.match(words_re, x)
    ]
    if verbose:
        print(point_words)
        print(words)
    return len(words) > 4 and len(point_words) / len(words) > 0.8


def is_email_address(line):
    return re.search(r"[\w-]+@[\w-]+\.[\w-]+", line)


def has_authors(txt):
    split = int(len(txt) / 2)
    txts = txt[:split].split("\n")[:-1]
    for line in txts:
        if is_author_affiliation(line) or is_email_address(line):
            return True
    return False


def remove_lines_like_authors(txt):
    newtxt = []
    split = int(len(txt) / 2)
    txts = txt[:split].split("\n")
    tail = [txts.pop()]
    for line in txts:
        if not is_author_affiliation(line) and not is_email_address(line):
            newtxt.append(line)
    return "\n".join(newtxt + tail) + txt[split:]


## Interactive

def check_clean(df_or_series, clean_abstract_text, start=0, interactive=True):
    """Compares two textual series showing diffs for each entry.

    If passed a dataframe as first argument, picks the "abstract_text" column.
    If `start` is provided, skips abstracts indexed less than its value.
    If not `interactive`, returns the diffs as a `pandas.Series`
    If `interactive`, waits for input at each entry, stopping if sent a nonempty string.
    """
    if not isinstance(df_or_series, pd.Series):
        abstract_text = df_or_series["abstract_text"]
    else:
        abstract_text = df_or_series
    abstract_text = abstract_text.loc[clean_abstract_text.index]
    comp = abstract_text.compare(clean_abstract_text)
    if comp.empty:
        print("No differences found.")
        return
    diff = comp.agg(
        lambda x: unified_diff(x["self"].split("\n"), x["other"].split("\n")), axis=1
    )
    if not interactive:
        return diff.map("\n".join)
    print(f"Found {len(diff)} modified documents.\n")
    for idx, diff in diff.loc[start:].items():
        for line in diff:
            print(line)
        print("\n" + 70 * "-" + str(idx) + "\n")
        if input():
            print("\nInterrupted!\n")
            break


def search_text(df, rexp):
    sel = df.abstract_text.str.contains(
        rexp,
        flags=CLEAN_REFLAGS,
    )
    for idx, txt in df.loc[sel, "abstract_text"].items():
        print(txt)
        print("\n" + 70 * "-" + str(idx) + "\n")
        if input():
            break


def extract_text(df, rexp):
    return (
        df["abstract_text"]
        .str.extractall(
            rexp,
            flags=CLEAN_REFLAGS,
        )
        .dropna()
    )
