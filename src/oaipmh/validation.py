#
class BadArgumentError(Exception):
    pass


def validate(argspec, dictionary):
    exclusive = None
    for arg_name, arg_type in list(argspec.items()):
        if arg_type == "exclusive":
            exclusive = arg_name
    # check if we have unknown arguments
    for key, _value in list(dictionary.items()):
        if key not in argspec:
            msg = f"Unknown argument: {key}"
            raise BadArgumentError(msg)
    # first investigate if we have exclusive argument
    if exclusive in dictionary:
        if len(dictionary) > 1:
            msg = f"Exclusive argument {exclusive} is used but other arguments found."
            raise BadArgumentError(msg)
        return
    # if not exclusive, check for required
    for arg_name, arg_type in list(argspec.items()):
        if arg_type == "required":
            msg = f"Argument required but not found: {arg_name}"
            if arg_name not in dictionary:
                raise BadArgumentError(msg)
    return


class ValidationSpec:
    GetRecord = {"identifier": "required", "metadataPrefix": "required"}
    GetMetadata = {"identifier": "required", "metadataPrefix": "required"}

    Identify = {}

    ListIdentifiers = {
        "from_": "optional",
        "until": "optional",
        "metadataPrefix": "required",
        "set": "optional",
    }

    ListMetadataFormats = {"identifier": "optional"}

    ListRecords = {
        "from_": "optional",
        "until": "optional",
        "set": "optional",
        "metadataPrefix": "required",
    }

    ListSets = {}


class ResumptionValidationSpec(ValidationSpec):
    ListIdentifiers = {
        "from_": "optional",
        "until": "optional",
        "metadataPrefix": "required",
        "set": "optional",
        "resumptionToken": "exclusive",
    }

    ListRecords = {
        "from_": "optional",
        "until": "optional",
        "set": "optional",
        "metadataPrefix": "required",
        "resumptionToken": "exclusive",
    }

    ListSets = {
        "resumptionToken": "exclusive",
    }


def validateArguments(verb, kw):
    validate(getattr(ValidationSpec, verb), kw)


def validateResumptionArguments(verb, kw):
    validate(getattr(ResumptionValidationSpec, verb), kw)
