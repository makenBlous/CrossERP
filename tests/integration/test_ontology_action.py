from crosserp.ontology.catalog import load_catalog


def test_ontology_action_catalog_has_unique_ids_and_projections() -> None:
    catalog = load_catalog()
    ids = [action.id for action in catalog.actions]
    assert len(ids) == len(set(ids))
    assert all(action.projections for action in catalog.actions)
