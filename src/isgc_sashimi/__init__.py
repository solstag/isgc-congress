#! /usr/bin/env python

import pandas as pd

from . import clean as clean_m


""" NOTES

- Data columns:
    ['abstract_text',
     'abstract_title',
     'bibliography',
     'cancelled',
     'code',
     'figure_legend_1',
     'figure_legend_2',
     'figure_title_1',
     'figure_title_2',
     'final_status',
     'id',
     'is_complete',
     'keyword_1',
     'keyword_2',
     'keyword_3',
     'keyword_4',
     'keywords',
     'legend_1',
     'legend_2',
     'not_to_remind',
     'program_day',
     'program_session',
     'publish_onsite',
     'relance_register',
     'topic_1',
     'topic_2',
     'topic_3',
     'user_id',
     'validate',
     'year']
"""


def get_data(file_paths, clean=True, drop=True):
    df = pd.concat(
        [pd.read_csv(file, sep="\t", dtype=str) for file in file_paths],
        ignore_index=True,
    )
    print(f"Found {len(df)} entries.")
    if drop:
        df = df.dropna(subset=["abstract_text"])
        print(f" Kept {len(df)} entries containing an abstract.")

    if clean:
        df["abstract_text__has_authors"] = df["abstract_text"].map(clean_m.has_authors)
        clean_abstract_text = clean_m.clean_text(df)
        df["abstract_text__is_cleaned"] = ~df["abstract_text"].eq(clean_abstract_text)
        df["abstract_text__cleaned"] = clean_abstract_text
        print(f" Cleaned {df['abstract_text__is_cleaned'].sum()} entries.")

        if drop:
            df = df.dropna(subset=["abstract_text"])
            print(f" Kept {len(df)} entries after cleaning.")

    df.index.name = "index"
    return df
