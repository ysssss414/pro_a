"""Read-only JSON Schema diagnostics, separate from authoritative admission.

Requires the dev jsonschema dependency. Never returns instance values or validator
messages (both can contain Source text). It neither edits nor normalizes records.
"""


def diagnose_shape(record, schema):
    from jsonschema import Draft202012Validator
    Draft202012Validator.check_schema(schema)
    known = set()
    def names(node):
        known.update(node.get('properties', {}))
        for child in node.get('properties', {}).values(): names(child)
        if 'items' in node: names(node['items'])
        for child in node.get('anyOf', []): names(child)
    names(schema)
    def safe_path(path):
        return [p if isinstance(p, int) or p in known else '<unknown>' for p in path]
    def describe(error):
        item = {'path': safe_path(error.absolute_path), 'reason': error.validator}
        if error.validator == 'required':
            item['missing_fields'] = sorted(set(error.validator_value) - set(error.instance))
        elif error.validator == 'additionalProperties':
            item['extra_fields'] = [k if k in known else '<unknown>'
                                    for k in sorted(set(error.instance) - set(error.schema.get('properties', {})))]
        elif error.validator == 'type':
            item.update(expected_type=error.validator_value, actual_type=type(error.instance).__name__)
        if error.context:
            children = error.context
            # Disjoint Node branches: show errors for the declared type when it is valid.
            if error.validator == 'anyOf' and type(error.instance) is dict:
                primary = error.instance.get('primary_type')
                indices = [i for i, b in enumerate(error.schema['anyOf'])
                           if primary in b.get('properties', {}).get('primary_type', {}).get('enum', [])]
                if len(indices) == 1:
                    children = [e for e in children if list(e.schema_path)[0] == indices[0]]
            item['causes'] = [describe(child) for child in children]
        return item
    return [describe(e) for e in Draft202012Validator(schema).iter_errors(record)]
