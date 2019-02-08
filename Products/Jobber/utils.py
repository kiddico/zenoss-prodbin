

class abstractclassmethod(classmethod):

    __isabstractmethod__ = True

    def __init__(cls, method):
        method.__isabstractmethod__ = True
        super(abstractclassmethod, cls).__init__(method)


class abstractstaticmethod(classmethod):

    __isabstractmethod__ = True

    def __init__(cls, method):
        method.__isabstractmethod__ = True
        super(abstractstaticmethod, cls).__init__(method)
