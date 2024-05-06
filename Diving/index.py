import string
import random
import flask
from flask_cors import CORS
import pysolr
import re
from flask import request, jsonify, render_template
import json
from qe import query_expansion
# from query_expansion.Association_Cluster import association_main
# from query_expansion.Metric_Clusters import metric_cluster_main
# from qe.scalar_cluster import scalar_main
from spellchecker import SpellChecker

spell = SpellChecker()
# Create a client instance. The timeout and authentication options are not required.
solr = pysolr.Solr('http://localhost:8983/solr/nutch/', always_commit=True, timeout=10)

app = flask.Flask(__name__)
CORS(app)
app.config["DEBUG"] = True


@app.route('/')
def index():
    return render_template('index.html')


@app.route('//api/v1/index', methods=['GET', 'POST'])
def get_query():
    # print("9")
    if 'query' in request.args:
        print(request.args)
        query = request.args.get('query', default=None)
        relevance = request.args.get('relevance', default=None)
        clustering_type = request.args.get('clustering', default=None)
        expansion = request.args.get('expansion', default=None)
        print(query)
        expanded_query = ''
        total_results = 50
        solr_results = get_results_from_solr(query, total_results)
        parsed_results = parse_solr_results(solr_results)
        parsed_results = parsed_results[:50]
        results = None

        # Handle clustering if selected
        if relevance:
            if relevance == 'page_rank':
                results = get_page_rank_results(parsed_results)
            elif relevance == 'hits':
                results = get_hits_results(parsed_results)

        if clustering_type:
            if relevance:
                results = get_clustering_results(results, clustering_type)
            else:
                results = get_clustering_results(parsed_results, clustering_type)

        # Handle query expansion if selected
        if expansion:
            if expansion == 'association_qe':
                expanded_query, results = get_association_qe_results(parsed_results, query)
            elif expansion == 'metric_qe':
                expanded_query, results = get_metric_qe_results(parsed_results, query)  # check -- sleep?
            elif expansion == 'scalar_qe':
                expanded_query, results = get_scalar_qe_results(parsed_results, query)

        # Serialize only the first 20 results if not empty
        # print([result['url'] for result in results])
        if results:
            # return results
            return jsonify({'results': results[:20], 'expanded_query': expanded_query})
        else:
            return jsonify({'results': [], 'error': 'Unable to process the query'})

    return jsonify({'results': [], 'error': 'Invalid query or type'})


def get_results_from_solr(query, no_of_results):
    query = query.translate(str.maketrans('', '', string.punctuation))
    query_words = query.split(' ')
    for i in range(len(query_words)):
        query_words[i] = 'content:' + query_words[i]
    query = ' OR '.join(query_words)
    print(query)
    solr_response = solr.search(query, search_handler="/select", **{
        "wt": "json",
        "rows": no_of_results
    })
    # print(solr_response)
    return solr_response


def parse_solr_results(solr_results):
    if solr_results.hits == 0:
        return jsonify({'results': [], 'error': 'No results found'})
    else:
        # for result in results:
        #     print(result["url"])
        solr_results = [result for result in solr_results if "pinterest.com" not in result["url"]]
        # print(len(solr_results))
        solr_results = results_check(solr_results)
        # print(solr_results)
        return solr_results


def results_check(results):
    # List to keep track of seen content
    seen_urls = set()

    # Initialize the solr_results list
    solr_Results = []
    title_retrieved = []
    # Iterate through the results dictionary
    for result in results:
        url = result['url']
        title = result['title'] if "title" in result.keys() else None
        content = result['content']
        # Check if the content is not already in the seen_contents set
        if url not in seen_urls:
            if not title:
                continue
            if title in title_retrieved:
                continue
            # Add the content to the seen_contents set
            seen_urls.add(content)
            title_retrieved.append(title)
            # Add the result to solr_Results
            solr_Results.append(result)
    # solr_Results now contains only results with unique content
    print("after removing ---- ", len(solr_Results))
    return solr_Results


def get_page_rank_results(solr_results):
    page_rank_results = {}
    # print("using page rank")
    with open('HITS/precomputed_scores/pageRank_scores.txt') as file:
        for line in file:
            line_out = line.split(' ')
            url = line_out[0].strip()
            score = line_out[1].strip()
            page_rank_results[url] = score
    results = sorted(solr_results, key=lambda k: float(page_rank_results.get(k['url'], 0)))#, reverse=True)
    return results


def get_hits_results(results):
    # hits_results = {}
    authority_score_file = open("HITS/precomputed_scores/authority_score_1", 'r').read()
    authority_score_dict = json.loads(authority_score_file)
    # with open('HITS/precomputed_scores/authority_score_1') as file:
    #     for line in file:
    #         # print(line)
    #         line_out = line.split(' ')
    #         url = line_out[0].strip()
    #         score = line_out[1].strip()
    #         hits_results[url] = score

    results = sorted(results, key=lambda x: authority_score_dict.get(x['url'], 0.0), reverse=True)
    return results


def get_clustering_results(parsed_results, param_type):
    if param_type == "flat_clustering":
        f = open('clustering/precomputed_clusters/clustering_f.txt')
        lines = f.readlines()
        f.close()
    elif param_type == "single_HAC_clustering":
        f = open('clustering/precomputed_clusters/clustering_h_4dim_single.txt')
        lines = f.readlines()
        f.close()
    elif param_type == "complete_HAC_clustering":
        f = open('clustering/precomputed_clusters/clustering_h_4dim_complete.txt')
        lines = f.readlines()
        f.close()

    cluster_map = {}
    for line in lines:
        line_split = line.split(",")
        line_split[0] = line_split[0].strip()
        line_split[1] = line_split[1].strip()
        if line_split[1] == "":
            line_split[1] = "99"
        cluster_map.update({line_split[0]: line_split[1]})

    for curr_resp in parsed_results:
        curr_url = curr_resp["url"]
        if curr_url not in cluster_map:
            if param_type == 'flat_clustering':
                curr_cluster = random.randint(1, 10)
            elif param_type == 'single_HAC_clustering':
                curr_cluster = str(float(random.randint(1, 4)))
            elif param_type == 'complete_HAC_clustering':
                curr_cluster = str(float(random.randint(1, 7)))
            # print(curr_url)
            # print(curr_cluster)
        else:
            curr_cluster = cluster_map.get(curr_url, "1.0")
        curr_resp.update({"cluster": curr_cluster})
        curr_resp.update({"done": "False"})

    clust_resp = []
    curr_rank = 1
    for curr_resp in parsed_results:
        if curr_resp["done"] == "False":
            curr_cluster = curr_resp["cluster"]
            curr_resp.update({"done": "True"})
            curr_resp.update({"rank": str(curr_rank)})
            curr_rank += 1
            if "title" in curr_resp and "content" in curr_resp and "url" in curr_resp and "boost" in curr_resp and "rank" in curr_resp:
                clust_resp.append({"title": curr_resp["title"], "url": curr_resp["url"],
                                   "content": curr_resp["content"], "rank": curr_resp["rank"],
                                   "boost": curr_resp["boost"], "cluster_id": curr_cluster})
                for remaining_resp in parsed_results:
                    if remaining_resp["done"] == "False":
                        if remaining_resp["cluster"] == curr_cluster:
                            remaining_resp.update({"done": "True"})
                            remaining_resp.update({"rank": str(curr_rank)})
                            curr_rank += 1
                            print(curr_cluster)
                            if "title" in remaining_resp and "content" in remaining_resp and "url" in remaining_resp and "boost" in remaining_resp and "rank" in remaining_resp:
                                clust_resp.append({"title": remaining_resp["title"], "url": remaining_resp["url"],
                                                   "content": remaining_resp["content"], "rank": remaining_resp["rank"],
                                                   "boost": remaining_resp["boost"], "cluster_id": curr_cluster})
    clust_resp = sorted(clust_resp, key=lambda i: i['boost'], reverse=True)
    clust_sort = {}
    for res in clust_resp:
        cluster_id = res["cluster_id"]
        entry = {"title": res["title"], "url": res["url"],
                 "content": res["content"], "rank": res["rank"], "boost": res["boost"], "cluster_id": cluster_id}
        if cluster_id in clust_sort:
            clust_sort[cluster_id].append(entry)
        else:
            clust_sort[cluster_id] = [entry]

    flattened_values = [value for sublist in clust_sort.values() for value in sublist]
    return flattened_values


def get_association_qe_results(results, query):
    # results = sorted(results, key = lambda i: i['boost'], reverse=True)
    results = results[:20]
    expanded_query = query_expansion.cluster_main(query, results, 'association')
    print(expanded_query)
    solr_results = get_results_from_solr(expanded_query, 20)
    parsed_results = parse_solr_results(solr_results)
    results = [result for result in parsed_results]
    return expanded_query, results

def get_metric_qe_results(results, query):
    results = sorted(results, key = lambda i: i['boost'], reverse=True)
    results = results[:5]
    expanded_query = query_expansion.cluster_main(query, results, 'metric')
    print(expanded_query)
    solr_results = get_results_from_solr(expanded_query, 20)
    parsed_results = parse_solr_results(solr_results)
    results = [result for result in parsed_results]
    return expanded_query, results

def get_scalar_qe_results(results, query):
    results = sorted(results, key = lambda i: i['boost'], reverse=True)
    # results = results[:5]
    expanded_query = query_expansion.cluster_main(query, results, 'scalar')
    print(expanded_query)
    solr_results = get_results_from_solr(expanded_query, 20)
    parsed_results = parse_solr_results(solr_results)
    results = [result for result in parsed_results]
    return expanded_query, results


if __name__ == "__main__":
    app.run(debug=True,port=5000)

