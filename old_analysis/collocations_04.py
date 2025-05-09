# for information on the weird reduce/mul business, see:
# https://stackoverflow.com/questions/595374/whats-the-function-like-sum-but-for-multiplication-product

from collections import Counter
from functools import reduce
from operator import mul
from math import sqrt

import pandas
from numpy import nan
from nltk.util import ngrams

from clean_data_03 import tokenize


def go(df, ngram_size, counts, total_tokens):
    ngrams = dict(Counter([b for (i, row) in df.iterrows() for b in row["post_ngrams"]]))
    total_ngrams = sum(ngrams.values())

    ngrams_df = pandas.DataFrame([{"ngram" : b, "raw_freq" : ngrams[b], "rel_freq" : ngrams[b] / total_ngrams}
                                   for b in ngrams])

    for i in range(0, ngram_size):
        ngrams_df["w" + str(i + 1) + "_raw_freq"] = ngrams_df["ngram"].apply(lambda x : counts[x[i]])
        ngrams_df["w" + str(i + 1) + "_rel_freq"] = ngrams_df["w" + str(i + 1) + "_raw_freq"] / total_tokens
        del ngrams_df["w" + str(i + 1) + "_raw_freq"]

    ngrams_df["ngram"] = ngrams_df["ngram"].apply(lambda x : " ".join(x))

    ngrams_df["P(ngram)"] = ngrams_df.apply(lambda x : reduce(mul,
                                                              [x["w" + str(i + 1) + "_rel_freq"] for i in range(0, ngram_size)],
                                                              1), axis=1)

    ngrams_df["t"] = ngrams_df.apply(lambda x : (x["rel_freq"] - x["P(ngram)"]) / sqrt((x["rel_freq"] / total_tokens)), axis=1)

    ngrams_df.sort_values(by="t", ascending=False, inplace=True)

    print(ngrams_df)
    

###
if __name__ == "__main__":
    csv_file = "troon_instagram_raw_post_data.csv"
    ngram_size = 8
    
    df = pandas.read_csv(csv_file, index_col="id")
    df.dropna(how="all", subset=["age", "likes", "post_text"], inplace=True)

    df["post_tokens"] = df["post_text"].apply(tokenize)
    df["post_ngrams"] = df["post_tokens"].apply(lambda x : list(ngrams(x, ngram_size)))

    counts = dict(Counter([t for (i, row) in df.iterrows() for t in row["post_tokens"]]))
    total_tokens = sum(counts.values())
    #print(sorted(counts.items(), key=lambda x : x[1], reverse=True))

    go(df, ngram_size, counts, total_tokens)
