import json


authority_score_file = open("precomputed_scores/hubs_score", 'r').read()
print(type(authority_score_file))
authority_score_dict = json.loads(authority_score_file)
print(type(authority_score_dict))
# max_key = max(authority_score_dict, key=authority_score_dict.get)
# print(max_key, authority_score_dict[max_key])
top_10_keys = sorted(authority_score_dict, key=authority_score_dict.get, reverse=True)[:50]

print("Top 10 keys with maximum values:")
for key in top_10_keys:
    print(key, ":", authority_score_dict[key])