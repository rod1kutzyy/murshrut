class ServiceError(Exception):
    pass


class Unauthorized(ServiceError):
    pass


class Forbidden(ServiceError):
    pass


class NotFound(ServiceError):
    pass


class OnboardingRequired(ServiceError):
    pass


class InvalidInput(ServiceError):
    pass


class ProviderUnavailable(ServiceError):
    pass
