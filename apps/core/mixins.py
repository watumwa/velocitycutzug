class ActiveListMixin:
    active_param = "active"

    def show_inactive(self, request) -> bool:
        return request.GET.get(self.active_param) == "all"
