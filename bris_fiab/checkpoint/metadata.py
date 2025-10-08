from dataclasses import dataclass


@dataclass
class BrisParameter:
    '''BrisParameter decodes parameters, as used in bris checkpoints'''

    parameter: str
    level: int | None = None

    @classmethod
    def from_string(cls, name: str) -> 'BrisParameter':
        elements = name.split('_')

        if len(elements) == 1:
            return BrisParameter(elements[0], None)
        elif len(elements) == 2:
            return BrisParameter(elements[0], int(elements[1]))

        raise ValueError(f"Invalid parameter name: {name}")

    def has_level(self) -> bool:
        return self.level is not None


def adapt_metdata(original_metadata: dict, replace_path: str = 'dataset.variables_metadata'):
    '''Rewrite all parameter metadata so that it is usable in a mars request. Note that this will modify the input dict!'''

    variables = original_metadata
    for p in replace_path.split('.'):
        variables = variables[p]

    for k, v in variables.items():
        if not 'mars' in v:
            continue
        p = BrisParameter.from_string(k)
        mars = v['mars']
        if p.has_level():
            mars["levtype"] = "pl"
            mars["levelist"] = p.level
            mars["param"] = p.parameter
        else:
            mars["levtype"] = "sfc"
            if p.parameter in ('z', 'lsm'):
                v["constant_in_time"] = True


if __name__ == "__main__":
    import json
    with open('inference-last.json') as f:
        metadata = json.load(f)
    print(metadata['dataset']['variables_metadata']["z"])
    adapt_metdata(metadata)
    print(metadata['dataset']['variables_metadata']["z"])
