#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import re
from collections import Counter
import numpy as np
from nltk.corpus import stopwords
from nltk import PorterStemmer

# import pysolr
import json
from tqdm import tqdm

porter_stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))


def tokenize_text(text):
    """
    Args:
        text(str): a string of text

    Return:
        tokens(list): a list of cleaned tokens
    """
    tokens = []
    text = re.sub(r'[\n]', ' ', text)  # remove enters
    text = re.sub(r'[,-]', ' ', text)  # remove comma and dash
    text = re.sub('[0-9]', '', text)  # remove all numbers
    text = re.sub(r'[^A-Za-z_\s]', '', text)  # only keep A-Za-z_ and space
    text = text.lower()
    tkns = text.split()
    # double check, remove empty tokens, stop words, and full numeric tokens
    tokens = [token for token in tkns if token not in stop_words and token != '' and not token.isnumeric()]
    return tokens


def make_stem_map(vocab):
    """
    Args:
        vocab(list): a list of vocabulary

    Returns:
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
    """
    token_2_stem = {}  # 1 to 1
    stem_2_tokens = {}  # 1 to n

    for token in vocab:
        stem = porter_stemmer.stem(token)
        if stem not in stem_2_tokens:
            stem_2_tokens[stem] = set()
        stem_2_tokens[stem].add(token)
        token_2_stem[token] = stem

    return token_2_stem, stem_2_tokens


####################################################################################################
def build_association(doc_tokens, token_2_stem, stem_2_tokens, query):
    """
    Args:
        doc_tokens(2-D list): tokens in each documents having structure:
                              [[token_1, token_2, ...], [...], ...]
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
        query(list): a list of tokens from query

    Return:
        query_expands(list): list of expand stem tokens ids for each token in the query
    """
    # build map from stem to index
    stems = stem_2_tokens.keys()
    stems = list(sorted(stems))
    stem_2_idx = {s: i for i, s in enumerate(stems)}

    # frequency of stems in each document
    f = np.zeros((len(doc_tokens), len(stems)), dtype=int)
    for doc_id, tokens in enumerate(doc_tokens):
        for token in tokens:
            if token in token_2_stem:
                stem = token_2_stem[token]
                stem_idx = stem_2_idx[stem]
                f[doc_id, stem_idx] += 1

    # correlation matrix
    '''
    Warning: too many query results (documents) will lead to slow calculation
             here. Especially for the "dot" calculation.
    '''
    c = np.dot(f.T, f)
    c_diag = np.diag(c)  # extract all c_{u,u}

    # normalize correlation matrix and pick the top 3 expansion tokens
    query_expands_id = []
    for token in query:
        stem = token_2_stem[token]
        stem_id = stem_2_idx[stem]

        # normalize correlation matrix for the query token
        c_token = c[stem_id, :]
        s_token = c_token / (c_token[stem_id] + c_diag + c_token)

        # pick the top 3 stems for each query token
        idx_sort = np.argsort(s_token)[::-1]  # sort decreasing by score
        idx_sort = idx_sort[1:3]  # pick top 3 tokens for each query token
        query_expands_id.extend(idx_sort.tolist())

    # convert stem ids to stem
    query_expands = []
    for stem_idx in query_expands_id:
        query_expands.append(stems[stem_idx])
    print(query_expands)
    return query_expands


def get_scalar_cluster(doc_tokens, token_2_stem, stem_2_tokens, query):
    """
    Args:
        doc_tokens(2-D list): tokens in each documents having structure:
                              [[token_1, token_2, ...], [...], ...]
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
        query(list): a list of tokens from query

    Return:
        query_expands(list): list of expand stem tokens ids for each token in the query
    """
    # build map from stem to index
    stems = stem_2_tokens.keys()
    stems = list(sorted(stems))
    stem_2_idx = {s: i for i, s in enumerate(stems)}

    # frequency of stems in each document
    f = np.zeros((len(doc_tokens), len(stems)), dtype=int)
    for doc_id, tokens in enumerate(doc_tokens):
        for token in tokens:
            if token in token_2_stem:
                stem = token_2_stem[token]
                stem_idx = stem_2_idx[stem]
                f[doc_id, stem_idx] += 1

    # correlation matrix
    c = np.dot(f.T, f)  # (#_of_stems, #_of_stems)
    c_diag = np.expand_dims(np.diag(c), axis=0)  # extract all c_{u,u} shape: (1, #_of_stems)

    # normalize correlation matrix
    s = c / (c + c_diag + c_diag.T)  # (#_of_stems, #_of_stems)
    s_norm = np.linalg.norm(s, axis=1)  # (#_of_stems,)

    # expand query
    query_expands_id = []
    for token in query:
        stem = token_2_stem[token]
        stem_id = stem_2_idx[stem]

        # calculate cosine simialrity for the token with all other stems
        stem_vec = np.expand_dims(s[stem_id, :], axis=0)
        stem_norm = np.linalg.norm(stem_vec)
        s_stem = np.dot(stem_vec, s.T).squeeze()  # (#_of_stems,)
        s_stem = (s_stem / stem_norm) / s_norm  # cosine similarity

        # pick the top 3 stems for each query token
        idx_sort = np.argsort(s_stem)[::-1]  # sort decreasing by score
        idx_sort = idx_sort[1:3]
        query_expands_id.extend(idx_sort.tolist())

    # convert stem ids to stem
    query_expands = []
    for stem_idx in query_expands_id:
        query_expands.append(stems[stem_idx])

    return query_expands


def get_metric_clusters(doc_tokens, token_2_stem, stem_2_tokens, query):
    """
    Args:
        doc_tokens(2-D list): tokens in each documents having structure:
                              [[token_1, token_2, ...], [...], ...]
        token_2_stem(dict): a map from token to its stem having structure {token:stem}
        stem_2_tokens(dict): a map from stem to its corresponding tokens having structure:
                             {stem:set(token_1, token_2, ...)}
        query(list): a list of tokens from query

    Return:
        query_expands(list): list of expand stem tokens ids for each token in the query
    """
    # build map from stem to index
    stems = stem_2_tokens.keys()
    stems = list(sorted(stems))
    stem_2_idx = {s: i for i, s in enumerate(stems)}

    # count the number of variants for each stem
    stem_len = [len(stem_2_tokens[s]) for s in stems]
    stem_len = np.array(stem_len)

    # build correlation matrix
    c = np.zeros((len(stem_2_idx), len(stem_2_idx)), dtype=int)
    for doc_id, tokens in enumerate(doc_tokens):
        tokens_count = Counter(tokens)
        # for each documents, count the difference between each pair of tokens
        # and add them to their corresponding stems
        for token_1, count_1 in tokens_count.items():
            stem_1 = token_2_stem[token_1]
            stem_1_id = stem_2_idx[stem_1]
            for token_2, count_2 in tokens_count.items():
                stem_2 = token_2_stem[token_2]
                stem_2_id = stem_2_idx[stem_2]
                if stem_1 == stem_2:
                    continue
                if count_1 != count_2:
                    c[stem_1_id, stem_2_id] += 1. / abs(count_1 - count_2)

    # normalize correlation matrix and pick the top 3 expansion tokens
    query_expands_id = []
    for token in query:
        stem = token_2_stem[token]
        stem_id = stem_2_idx[stem]

        # normalize correlation matrix
        s_stem = c[stem_id, :] / (stem_len[stem_id] * stem_len)

        # pick the top 3 stems for each query token
        s_stem = np.argsort(s_stem)[::-1]  # sort decreasing by score
        s_stem = s_stem[:1]
        query_expands_id.extend(s_stem.tolist())

    # convert stem ids to stem
    query_expands = []
    for stem_idx in query_expands_id:
        query_expands.append(stems[stem_idx])

    return query_expands


####################################################################################################

def cluster_main(query, solr_results, clustertype):
    """
    Args:
        query(str): a text string of query
        solr_results(list): result for the query from function 'get_results_from_solr'

    Return:
        query(str): a text string of expanded query
    """
    # query = 'olympic medal'
    # solr = pysolr.Solr('http://localhost:8983/solr/nutch/', always_commit=True, timeout=10)
    # results = get_results_from_solr(query, solr)
    vocab = set()
    doc_tokens = []

    # tokenize query and query results, then build vocabulary
    if 'content:' == query[:8]:
        query = query[8:]
    # print('Initial query:', query)
    query_text = query  # keep original query text
    query = tokenize_text(query)
    vocab.update(query)
    # for result in tqdm(solr_results, desc='Preprocessing results'):
    for result in solr_results:
        if 'content' not in result:
            tokens = []
        else:
            tokens = tokenize_text(result['content'])
        doc_tokens.append(tokens)
        vocab.update(tokens)

    vocab = list(sorted(vocab))
    token_2_stem, stem_2_tokens = make_stem_map(vocab)

    # expand query
    if clustertype == 'association':
        query_expands_stem = build_association(doc_tokens, token_2_stem, stem_2_tokens, query)
    elif clustertype == 'scalar':
        query_expands_stem = get_scalar_cluster(doc_tokens, token_2_stem, stem_2_tokens, query)
    elif clustertype == 'metric':
        query_expands_stem = get_metric_clusters(doc_tokens, token_2_stem, stem_2_tokens, query)
    # print(query_expands_stem)
    # convert from stem to tokens
    query_expands = []
    for token in query:
        for stem in query_expands_stem:
            if token_2_stem[token] == stem:
                query_expands_stem.remove(stem)
    for stem in query_expands_stem:
        temp = list(stem_2_tokens[stem])
        query_expands.append(temp[0])
    query_expands = set(query_expands)
    # query_expands = set()
    # for stem in query_expands_stem:
    #     query_expands.update(list(stem_2_tokens[stem]))
    # print(stem_2_tokens)
    # generate new query
    for token in query:
        query_expands.discard(token)

    query.extend(list(query_expands))
    query = ' '.join(query)

    # print('Expanded query:', query)

    return query


if __name__ == '__main__':
    json_path = 'dive.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)
    print('total number of results:', len(results['response']['docs']))
    solar = results['response']['docs'][:30]
    queries = ['diving destinations']
    clustertype = 'association'
    #     clustertype = 'scalar'
    #     clustertype = 'metric'
    print(clustertype)
    for query in queries:
        cluster_main(query, solar, clustertype)


