from pysolr import Solr
import json
solr_url = 'http://localhost:8983/solr/nutch'
solr = Solr(solr_url)
batch_size = 1000  # Number of documents to retrieve in each batch
total_documents = 129698  # Total number of documents to retrieve

documents = []  # List to store retrieved documents

start = 0
while start < total_documents:
    # Query for a batch of documents
    if total_documents-start == 698:
        results = solr.search('*:*', start=start, rows=698)
    else:
        results = solr.search('*:*', start=start, rows=batch_size)
    documents.extend(results)

    start += batch_size
    print(f" got {start} rows")

print(len(documents))
with open("diving.json", 'w') as json_file:
    json.dump(documents, json_file,indent=4)

print(f"Dumped {len(documents)} to diving json")

