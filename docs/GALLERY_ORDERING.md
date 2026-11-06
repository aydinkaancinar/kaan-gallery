# Curated gallery ordering

The public interface has no visitor sorting control. Search, categories, and the creation-date range slider remain available. Backend `order_by` options are retained for future use.

## Default sequence

1. Items with a non-null `display_order` come first, lowest number first.
2. Within equal positions, sort by physical `creation_year`, then `creation_month`, newest first.
3. Unpositioned items follow, also sorted newest first by physical date.
4. Unknown dates follow known dates within the same position group. ID ascending resolves remaining ties.

Positions are priorities, not reserved grid slots. Zero is a real position. Duplicate values and gaps are allowed. New items default to no position. Clearing a position returns the artwork to ordinary date-based ordering.

## Administration

On the Items admin list, edit **Gallery position** and click Save. Publication status remains independently editable. Year/month columns make curation easier. Existing artworks keep their data; the migration adds nullable positions without assigning any.

## Source references

- [Item model](../items/models.py): nullable field, nonnegative validator, and shared default Meta ordering.
- [List view](../items/views.py): uses the model ordering when no explicit backend sort is requested; explicit sorting branches remain unchanged.
- [Admin](../items/admin.py): position column and inline list editing.
- [Migration](../items/migrations/0021_gallery_display_order.py): adds the field and ordering metadata.
- [Tests](../items/tests/test_gallery_ordering.py): validation, date ordering, ties, zero/gaps, clearing, publication, combined filtering/pagination, and explicit sort overrides.

A position is not an authorization mechanism. Existing MFA write permissions and draft visibility rules continue to apply. The serializer exposes the model field through its existing ModelSerializer configuration.

```bash
./.venv/bin/python manage.py test items.tests.test_gallery_ordering
```
