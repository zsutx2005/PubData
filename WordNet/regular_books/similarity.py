# -*- coding: utf-8 -*-

# Copyright (C) 2015-2016 Bohdan Khomtchouk and Kasra A. Vand
# This file is part of PubData.

# -------------------------------------------------------------------------------------------

import numpy as np
from itertools import chain
from functools import wraps
from collections import Counter
from itertools import permutations
import json
import glob


class Initializer:
    def __init__(self, *args):
        self.main_dict = self.refine_data()
        self.all_words = self.create_words()
        self.w_w_i = self.create_words_with_indices()
        self.all_sent = self.get_sentences()
        self.s_w_i = self.create_sentences_with_indices()

    def create_words_with_indices(self):
        return {w: i for i, w in enumerate(self.all_words)}

    def create_sentences_with_indices(self):
        return {s: i for i, s in enumerate(self.all_sent)}

    def refine_data(self):
        main_dict = self.load_data()
        return {k: v for k, v in main_dict.items() if v}

    def load_data(self):
        file_names = glob.glob("files/*.json")
        result = {}
        for name in file_names:
            with open(name) as f:
                result.update(json.load(f))
        return result

    def create_words(self):
        all_words = set(chain.from_iterable(self.main_dict.values()))
        return list(all_words)

    def get_sentences(self):
        return list(map(str, self.main_dict))

    def create_WSM(self):
        """
        Initialize the word similarity matrix by creating a matrix with
        1 as its main digonal and columns with word names.
        """
        dt = np.dtype({"names": self.all_words, "formats": [np.float16] * len(self.all_words)})
        wsm = np.zeros(len(self.all_words), dtype=dt)
        wsm_view = wsm.view(np.float16).reshape(len(self.all_words), -1)
        np.fill_diagonal(wsm_view, 1)
        return wsm

    def create_SSM(self):
        """
        Initialize the sentence similarity matrix by creating a NxN zero filled
        matrix where N is the number of sentences.
        """
        size = len(self.main_dict)
        dt = np.dtype({"names": self.all_sent,
                       "formats": [np.float16] * size})
        return np.zeros(size, dtype=dt)


class FindSimilarity(Initializer):
    def __init__(self, *args):
        super(FindSimilarity, self).__init__(*args)
        try:
            self.iteration_number = args[0]
        except IndexError:
            raise Exception("Please provide an iteration number!")
        self.latest_WSM = self.create_WSM()
        self.latest_SSM = self.create_SSM()

    def cache_matrix(f):
        cache_WSM = {}
        cache_SSM = {}
        if f.__name__ == "WSM":
            cache = cache_WSM
        else:
            cache = cache_SSM

        @wraps(f)
        def wrapped(*args):
            try:
                result = cache[args]
            except KeyError:
                result = cache[args] = f(*args)
            return result
        return wrapped

    def cache_weight(f):
        cache = {}

        @wraps(f)
        def wrapped(self, **kwargs):
            try:
                result = cache[kwargs.values()]
            except KeyError:
                result = cache[kwargs.values()] = f(self, **kwargs)
            return result
        return wrapped

    def cache_affinity(f):
        cache = {}

        @wraps(f)
        def wrapped(*args):
            try:
                result = cache[args]
            except KeyError:
                result = cache[args] = f(*args)
            return result
        return wrapped

    @cache_affinity
    def affinity_WS(self, W, S, n):
        return max(self.WSM(n)[W][self.w_w_i[wi]] for wi in self.main_dict[S])

    @cache_affinity
    def affinity_SW(self, S, W, n):
        return max(self.SSM(n)[S][self.s_w_i[sj]] for sj in self.sentence_include_word(W))

    def similarity_W(self, W1, W2, n):
        return sum(self.weight(s=s, w=W1) * self.affinity_SW(s, W2, n - 1)
                   for s in self.sentence_include_word(W1))

    def similarity_S(self, S1, S2, n):
        return sum(self.weight(w=w, s=S1) * self.affinity_WS(w, S2, n - 1) for w in self.main_dict[S1])

    def sentence_include_word(self, word):
        return {str(sent) for sent, words in self.main_dict.items() if word in words}

    def update_WSM(self):
        for w in self.all_words:
            for index in range(len(self.all_words)):
                self.latest_WSM[w][index] = self.similarity_W(w, self.all_words[index])

    def update_SSM(self):
        for s in self.all_sent:
            for index in range(len(self.all_sent)):
                self.latest_SSM[s][index] = self.similarity_S(s, self.all_sent[index])

    @cache_matrix
    def WSM(self, n):
        if n > 0:
            self.update_WSM()
        return self.latest_WSM

    @cache_matrix
    def SSM(self, n):
        if n > 0:
            self.update_SSM()
        return self.latest_SSM

    @cache_weight
    def weight(self, **kwargs):
        W, S = kwargs['s'], kwargs['s']
        counter = Counter(self.all_words)
        sum5 = sum(j for _, j in counter.most_common(5))
        word_factor = max(0, 1 - counter[W] / sum5)
        other_words_factor = sum(max(0, 1 - counter[w] / sum5) for w in self.main_dict[S])
        return word_factor / other_words_factor

    def iteration(self):
        for i in range(self.iteration_number):
            for w1, w2 in permutations(self.all_words, 2):
                self.similarity_W(w1, w2, i)
            for s1, s2 in permutations(self.all_sent, 2):
                self.similarity_S(s1, s2, i)
        self.save_matrixs()

    def save_matrixs(self):
        np.savetxt("SSM.txt", self.latest_SSM)
        np.savetxt("WSM.txt", self.latest_WSM)


if __name__ == "__main__":
    FS = FindSimilarity(2)
    print("All words {}".format(len(FS.all_words)))
    # print(FS.all_words)
    FS.iteration()
