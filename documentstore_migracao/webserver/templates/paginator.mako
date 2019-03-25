<nav aria-label="...">
  <ul class="pagination">
    <li class="page-item
      % if not items.previous_page:
        disabled
      % endif
      ">
      <a class="page-link" href="${links['previous_page']['href']}" tabindex="-1" aria-disabled="true">Previous</a>
    </li>

    % for page in links['range_pages']:

        % if page['type'] == "current_page":
            <li class="page-item active" aria-current="page">
              <a class="page-link" href="#">${links['current_page']['value']} <span class="sr-only">(current)</span></a>
            </li>
        % elif page['type'] == "page" :
            <li class="page-item"><a class="page-link" href="${page['href']}">${page['value']}</a></li>
        % endif

    % endfor

    <li class="page-item
      % if not items.next_page:
        disabled
      % endif
      ">
      <a class="page-link" href="${links['next_page']['href']}">Next</a>
    </li>
  </ul>
</nav>