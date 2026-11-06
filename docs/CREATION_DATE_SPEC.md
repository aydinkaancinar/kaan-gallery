# Physical artwork creation dates — test contract

These are completion month/year values, independent of the `created` database timestamp.
Only tests/specification were added; feature implementation is intentionally left to Kaan.

- Model/API fields: `creation_year` and `creation_month`, nullable together. Existing records remain unknown.
- Match the existing model limits: year 1999–2099 inclusive; month 1–12 inclusive. Future values within this range are allowed by this contract.
- POST accepts both components or neither; null/null is valid. Missing/null only half is invalid.
- PATCH validates the resulting object, combining submitted fields with stored values. An existing date can update just one component; clearing requires both null. Omitting dates preserves them.
- Model field validators are checked with full_clean(); direct save() does not promise automatic validation. Cross-field model/admin validation and database pair constraints can be added separately.
- Optional exact filters: creation_year; creation_month (across years); both combine with AND.
- Inclusive range parameters: created_from and created_to, strictly YYYY-MM within the same year bounds. Each bound is optional. Unknown dates are excluded when a date filter/range is applied. Invalid/empty explicit parameters return 400; reversed ranges return 400; equal bounds are valid.
- Sort: order_by=creation_date or -creation_date. Sort year then month; unknown values last in either direction; name ascending then ID ascending break ties. Default and existing sorting behavior remain unchanged.
- Search: valid YYYY or YYYY-MM input searches physical dates, not textual occurrences. Other input keeps existing name/description search. Month-name search and frontend display formatting are not specified here.
- Date restrictions combine with existing category/name/price filters; public results/counts must exclude drafts. API tests traverse pagination to check the complete order and membership.
- Do not skip or weaken these tests to achieve green. They are intended to fail until implemented.

## Suggested implementation order

1. Generate/apply the migration for the two existing model fields.
2. Complete serializer paired-field validation and PATCH behavior.
3. Validate query parameters in ItemFilterSerializer.
4. Apply exact and inclusive range filters.
5. Add sorting with null handling and tie-breakers.
6. Add date-aware search and run the full suite.

## Run focused tests

```bash
./.venv/bin/python manage.py test items.tests.test_creation_dates.CreationDateValidationTests
./.venv/bin/python manage.py test items.tests.test_creation_dates.CreationDateFilterValidationTests
./.venv/bin/python manage.py test items.tests.test_creation_dates.CreationDateAPITests
```

The first two classes test validation without database setup. The API class requires the field migration. The tests are a mixture of unit and API integration tests: persistence, routing, publication security, and pagination need integration coverage.
