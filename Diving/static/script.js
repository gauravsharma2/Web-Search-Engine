/**
 * @author Sasipreetam Morsa
 */
 
var BASE_URL = "http://127.0.0.1:5000//api/v1/index"
var data = [];

function customEngine(input) {
    var divingIFrame = document.getElementById("diving").contentWindow.document;
    var expandedQuery = document.getElementById("expanded_query_result");

    if(expandedQuery != null) {
        expandedQuery.innerHTML = '';
        var textNode = document.createTextNode(data['expanded_query']);
        expandedQuery.appendChild(textNode);
    }

    let frameElement = document.getElementById("diving");
    let doc = frameElement.contentDocument;
    doc.body.innerHTML = doc.body.innerHTML + '<style>a {margin: 0px 0px 0px 0px;}</style>';
    
    divingIFrame.open();
    
    var out = "";
    var i;
    for (var i = 0; i < data['results'].length; i++) {
      out += '<a style="color:black;" href="' + data['results'][i].url + '">' +
             data['results'][i].title + '</a> ';

      if (data['results'][i].cluster_id) {
          out += '<span style="color:black;">(' + data['results'][i].cluster_id + ')</span>';
      }

      out += '<br>';

      out += '<p style="color:black;">' +
             data['results'][i].content.substring(0, 500) + "............" + '</p>';
    }
    divingIFrame.write(out);
    
    divingIFrame.close();
}

function queryToGoogleBing() {
    var input = document.getElementById("UserInput").value;
    document.getElementById("google").src = "https://www.google.com/search?igu=1&source=hp&ei=lheWXriYJ4PktQXN-LPgDA&q=" + input;
    document.getElementById("bing").src = "https://www.bing.com/search?q=" + input;
}

function erase_data() {
    document.getElementById("expanded_query_result").innerHTML = "";
}

function search() {
    var input = document.getElementById("UserInput").value;
    
    var page_rank = document.getElementById("page_rank").checked;
    var hits = document.getElementById("hits").checked;
    var flat_clustering = document.getElementById("flat_clustering").checked;
    var hierarchical_clustering_complete = document.getElementById("hierarchical_clustering_complete").checked;
    var hierarchical_clustering_single = document.getElementById("hierarchical_clustering_single").checked;
    var association_qe = document.getElementById("association_qe").checked;
    var metric_qe = document.getElementById("metric_qe").checked;
    var scalar_qe = document.getElementById("scalar_qe").checked;
//    var none = document.getElementById("none").checked;
//    var none1 = document.getElementById("none1").checked;
//    var none2 = document.getElementById("none2").checked;
    var type,type1,type2;
    
    if (page_rank) {
        type = "page_rank";
        console.log("page rank select");
    }
    else if (hits) {
        type = "hits";
    }
//    else if (none) {
//        type = "none";
//    }
    if (flat_clustering) {
        type1 = "flat_clustering";
    }
    else if (hierarchical_clustering_single) {
        type1 = "single_HAC_clustering";
    }
    else if (hierarchical_clustering_complete) {
        type1 = "complete_HAC_clustering";
    }
//    else if (none1) {
//        type1 = "none";
//    }
    if (association_qe) {
        type2 ="association_qe";
    }
    else if (metric_qe) {
        type2 ="metric_qe";
    }
    else if (scalar_qe) {
        type2 ="scalar_qe";
    }
//    else if (none2) {
//        type2 ="none";
//    }

    $.get( BASE_URL, {"query": input, "relevance": type, "clustering":type1, "expansion":type2})
    
    .done(function(resp) {
        data = resp
        customEngine(input);

    })
    .fail(function(e) {
        
        console.log("error", e);
    })
}

