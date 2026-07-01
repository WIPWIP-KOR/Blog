(function () {
  var input = document.getElementById("search-input");
  var results = document.getElementById("search-results");
  if (!input || !results) return;

  var indexData = [];
  fetch(window.SEARCH_INDEX_URL)
    .then(function (res) { return res.json(); })
    .then(function (data) { indexData = data; });

  function render(items) {
    if (!input.value) {
      results.innerHTML = "";
      return;
    }
    if (items.length === 0) {
      results.innerHTML = "<p>검색 결과가 없습니다.</p>";
      return;
    }
    results.innerHTML = items
      .map(function (item) {
        return (
          '<article class="post-card">' +
          '<h2><a href="' + item.permalink + '">' + item.title + "</a></h2>" +
          '<p class="post-summary">' + item.description + "</p>" +
          "</article>"
        );
      })
      .join("");
  }

  input.addEventListener("input", function () {
    var query = input.value.trim().toLowerCase();
    if (!query) {
      render([]);
      return;
    }
    var matches = indexData.filter(function (item) {
      var haystack = [
        item.title,
        item.description,
        (item.tags || []).join(" "),
        (item.categories || []).join(" "),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.indexOf(query) !== -1;
    });
    render(matches);
  });
})();
