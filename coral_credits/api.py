from coral_credits.controllers import resource_class


class CoralCreditsModule:
    def __init__(self):
        self.providers = [resource_class.ResourceClassProvider]
        self.controllers = [resource_class.ResourceClassController]
