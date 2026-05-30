from __future__ import annotations

from typing import Any, Optional

from rest_framework.pagination import BasePagination
from rest_framework.response import Response


class NoCountPageNumberPagination(BasePagination):
    """
    Page-number pagination that avoids the expensive COUNT(*) query.

    Response shape matches DRF list pagination but omits `count`.
    """

    page_query_param = "page"
    page_size_query_param = "page_size"

    # Keep these consistent with global DRF settings
    page_size = 20
    max_page_size = 200

    def _get_page_size(self, request) -> int:
        raw = request.query_params.get(self.page_size_query_param)
        if raw is None:
            return self.page_size

        try:
            size = int(raw)
        except (TypeError, ValueError):
            return self.page_size

        if size <= 0:
            return self.page_size

        if self.max_page_size is not None and size > self.max_page_size:
            size = self.max_page_size

        return size

    def _get_page_number(self, request) -> int:
        raw = request.query_params.get(self.page_query_param, "1")
        try:
            page = int(raw)
        except (TypeError, ValueError):
            page = 1

        if page < 1:
            page = 1

        return page

    def paginate_queryset(self, queryset, request, view=None):
        page = self._get_page_number(request)
        page_size = self._get_page_size(request)

        offset = (page - 1) * page_size
        limit = page_size

        # Fetch one extra row to determine whether there's a next page.
        page_plus_one = list(queryset[offset : offset + limit + 1])
        results = page_plus_one[:limit]
        has_next = len(page_plus_one) > limit

        self._previous_url = None
        self._next_url = None

        if page > 1:
            prev_page = page - 1
            self._previous_url = self._build_page_url(request, prev_page, page_size)

        if has_next:
            next_page = page + 1
            self._next_url = self._build_page_url(request, next_page, page_size)

        return results

    def _build_page_url(self, request, page: int, page_size: int) -> str:
        # Use the current URL's base; preserve other query params.
        params = request.query_params.copy()
        params[self.page_query_param] = str(page)
        params[self.page_size_query_param] = str(page_size)

        base_url = request.build_absolute_uri(request.path)
        return f"{base_url}?{params.urlencode()}"

    def get_paginated_response(self, data):
        return Response(
            {
                "results": data,
                "next": self._next_url,
                "previous": self._previous_url,
                # Intentionally no `count` to avoid COUNT(*).
            }
        )
