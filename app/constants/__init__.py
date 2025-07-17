from enum import IntFlag

class PERMISSIONS(IntFlag):
    VIEW = 1 << 0
    EDIT = 1 << 1
    DELETE = 1 << 2
    CREATE = 1 << 3
    IMPORT = 1 << 4
    EXPORT = 1 << 5
    FACEREGISTER = 1 << 6