from dataclasses import fields

def from_dict(cls, d):
    try:
        fieldtypes = {f.name: f.type for f in fields(cls)}
        return cls(**{f: from_dict(fieldtypes[f], d[f]) for f in d})
    except:
        return d
