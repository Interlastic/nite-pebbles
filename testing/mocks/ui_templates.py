class MockView:
    def add_item(self, item):
        pass

class Template:
    def message(self, *args, **kwargs):
        return MockView()
    def success(self, *args, **kwargs):
        return MockView()
    def error(self, *args, **kwargs):
        return MockView()
    def warning(self, *args, **kwargs):
        return MockView()
    def confirm(self, *args, **kwargs):
        return MockView()
    def loading(self, *args, **kwargs):
        return MockView()

template = Template()
