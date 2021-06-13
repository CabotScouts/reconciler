class ReconcilerError(Exception):
    pass


class ReconcilerParameterError(ReconcilerError):
    # A parameter is missing, or being used incorrectly
    pass


class ReconcilerMailerError(ReconcilerError):
    # Something is wrong with the mailer
    pass
