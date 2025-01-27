# Python script to extract the inlinks and outlinks from the dump file and compute the hub, authority and pageRank scores
import networkx as nx

# read inlinks
max_inlinks = -1
with open("C:/Program Files/apache-nutch-1.19/runtime/local/crawl/inlinks/part-r-00000",
          encoding='utf8') as f:
    inlinks = {}
    for line in f:
        line = line.strip()
        if line:
            if "Inlinks" in line:
                key = line.split("\t")[0]
                values = []
            elif "fromUrl" in line:
                values.append(line.split()[1])
        else:
            if values:  # checks if d_value is not empty before adding to dictionary
                inlinks[key] = values
                if len(values) > max_inlinks:
                    max_inlinks = len(values)
print('Max In Links - ', max_inlinks)
# create outlinks
outlinks = {}
for key, urls in inlinks.items():
    for url in urls:
        outlinks.setdefault(url, []).append(key)

max_outlinks = -1
for i in outlinks:
    if len(outlinks[i]) > max_outlinks:
        max_outlinks = len(outlinks[i])

print('Max Out Links - ', max_outlinks)

# HITS Algorithm
G = nx.Graph(outlinks)
print('edges - ', G.number_of_edges())
print('nodes - ', G.number_of_nodes())

# PageRank Algorithm
pageRank = nx.pagerank(G, alpha=0.85)
print(pageRank)
pageRank_sorted = dict(sorted(pageRank.items(), key=lambda x: x[1], reverse=True))
# This code is used to generate the page rank scores of the crawled pages. It is used to generate the page rank scores of the crawled pages. The page rank scores of the crawled pages are saved in a file named pageRank_scores.txt.
with open('C:/Users/AGM230006/Documents/Diving/HITS/precomputed_scores/pageRank_scores.txt', 'w') as convert_file:
    for i, (key, value) in enumerate(pageRank_sorted.items()):
        if i == len(pageRank_sorted) - 1:  # if it's the last item
            convert_file.write(str(key) + ' ' + str(value))  # remove the newline
        else:
            convert_file.write(str(key) + ' ' + str(value) + '\n')
