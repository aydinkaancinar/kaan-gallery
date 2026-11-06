# Security implementation and learning notes

Reviewed: 2026-11-06. This is a code-based snapshot of a local development application, not a security certification or production-readiness claim. The full Django suite passed 100 tests during this review. Passing tests cover only the scenarios asserted; they do not prove absence of vulnerabilities.

This document contains source references and design explanations, not credentials or private deployment details. It is suitable for review alongside the public repository. Nothing was deployed or pushed when this document was created.

## 1. Security boundaries and intended policy

Protected assets include admin accounts/sessions, unpublished artwork and images, database integrity, and upload/storage resources.

| Operation | Intended policy | Current implementation |
| --- | --- | --- |
| Published artwork reads | Public | Implemented in item list and ID/slug detail querysets |
| Draft artwork metadata | Active MFA-verified staff only | Shared verified-staff helper scopes list and ID/slug detail querysets |
| API create/update/delete | Authenticated MFA-verified staff | Explicit per-view permission on item and artist CRUD |
| Django admin | Active, MFA-verified staff; model permissions also apply | OTP-required admin site configured |
| Published image bytes | Public | Authorization-aware image endpoint implemented |
| Draft image bytes | Active MFA-verified staff only | Image endpoint enforces this; URL integration/testing unfinished |
| After unpublishing | Subsequent anonymous image requests denied | Endpoint checks current publication state; lifecycle test pending |

A read permission alone does not select visible records. Queryset scoping determines which objects can be found. Image authorization is separate from artwork JSON authorization because callers can request an image URL directly.

## 2. Session authentication and API authorization

Sources: [settings](../config/settings.py), [permission class](../items/permissions.py), [API views](../items/views.py).

DRF is explicitly configured with `SessionAuthentication`. The previous default Basic Authentication path is not enabled. Browsers authenticate with Django sessions; CSRF checks apply to unsafe session-authenticated requests.

`IsAdminOrReadOnly.has_permission()` allows DRF safe methods (`GET`, `HEAD`, `OPTIONS`). Writes explicitly require an authenticated, active user with `is_staff` and `is_verified()`. OTP middleware supplies the latter method for session users.

The permission decorator is applied to `getData`, `operateItem`, `artistAPI`, `operateArtist`, and the GET-only `artwork_detail`. The regular Django image view performs its own checks rather than using DRF permissions.

Important limitations:

- `DEFAULT_PERMISSION_CLASSES` now uses `items.permissions.IsAdminOrReadOnly`. New DRF views inherit the read-public/write-verified-staff policy unless explicitly overridden. This does not scope draft querysets or protect ordinary Django views.
- API staff authorization does not enforce individual Django model permissions. Admin does enforce its own model permissions. Decide the policy before granting additional staff accounts.
- `is_active` is explicitly checked by the write permission as defense in depth, in addition to the standard backend rejecting inactive sessions. New/custom authentication mechanisms must preserve OTP verification behavior.
- `force_authenticate()` is a testing shortcut, not a production login flow, and can bypass the session-user path used by OTP middleware.

Evidence: [permission tests](../items/tests/test_permissions.py) cover staff creation/update/deletion and selected anonymous/non-staff rejections. Artist write coverage and a complete role/operation matrix remain incomplete. The non-staff creation test currently posts `Admin vase` but checks absence of `Permission test vase`; correct the name so the database assertion verifies the attempted record.

## 3. MFA and admin access

Sources: [installed apps and middleware](../config/settings.py), [admin site and account routes](../config/urls.py), [admin model registration](../items/admin.py), [session tests](../items/tests/test_session_security.py).

Installed components:

- `django_otp`: session verification support.
- `otp_totp`: authenticator-app time-based codes.
- `otp_static`: recovery-code storage capability.
- `two_factor`: enrollment and login screens.

`OTPMiddleware` follows `AuthenticationMiddleware`, so it can associate the authenticated user with the verified device recorded in the session. The existing admin site uses `AdminSiteOTPRequired`. This adds OTP verification to admin access rather than merely offering optional enrollment.

The MFA package routes are included before the admin routes. `LOGIN_URL` names the MFA login route. The real login-flow test submits the password step, verifies that authentication is not complete, submits a generated TOTP code, and asserts both authenticated-user and OTP-device session state.

The package identifies the primary enrolled TOTP device by its internal name `default`; tests exercising actual login must reproduce that enrollment convention. A differently named device can be missed by primary-device selection. Password authentication must never be treated as proof of MFA.

[Test helpers](../items/tests/helpers.py) also simulate a completed verified session for unrelated permission/behavior tests. They create a confirmed device, establish a session, and record its persistent ID. This tests downstream authorization, not actual code verification.

Remaining work: incorrect numeric codes, replay rejection, recovery-code single use, recovery procedures, additional bypass checks, and login rate limiting. Having the recovery-code plugin installed does not prove recovery has been configured, exercised, or safely documented.

## 4. CSRF and logout

Sources: [middleware and authentication settings](../config/settings.py), [session/CSRF tests](../items/tests/test_session_security.py).

CSRF mitigates requests that exploit a browser automatically attaching authentication cookies. It is separate from authentication, authorization, and XSS defenses.

The tests use `APIClient(enforce_csrf_checks=True)` where CSRF behavior matters. JSON API requests supply a token in `X-CSRFToken`; HTML form requests use the `csrfmiddlewaretoken` field and multipart encoding. The test client's default request format is JSON, which does not populate Django's form-data dictionary.

Coverage includes missing-token rejection, valid-token creation with a verified session, admin login routing, logout clearing authentication, and denied writes after logout. A CSRF token without an authenticated verified staff session does not grant write access.

The missing-token admin test calls the admin URL; this should not be described as comprehensive coverage of every step of the MFA login/enrollment/recovery forms. Production trusted origins, HTTPS, secure cookies, and proxy handling still need configuration and tests.

### Session lifetime and CSRF-token lifetime

[Session settings](../config/settings.py) now specify `SESSION_COOKIE_AGE = 8 * 60 * 60`, `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`, and `SESSION_SAVE_EVERY_REQUEST = False`.

The server-side database session expires eight hours from its last save. Ordinary read requests do not continually refresh that expiry, but changes to session data can. This is not an absolute eight-hour cap measured from initial login. Existing sessions may retain their previous expiry until saved; log out and back in after changing policy.

Browser-close expiry creates a browser-session cookie; browser restoration behavior can preserve it. Closing a browser does not revoke the database session, and manually supplied cookies can still be accepted until server-side expiry or invalidation. Logout invalidates the corresponding session. Test expiry/revocation explicitly before claiming full lifecycle coverage.

CSRF tokens have no independent short server-enforced expiry timer. Cookie retention is different from token validity. Login rotates the CSRF secret; replaying a matching cookie/header pair does not by itself authenticate a user. Session expiry and permission checks remain essential.

## 5. Artwork publication and object access

Sources: [Item model](../items/models.py), `getData`, `operateItem`, and `artwork_detail` in [views](../items/views.py), [publication tests](../items/tests/test_publication.py).

Items default to `draft`. List and detail querysets for callers who are not MFA-verified staff are restricted to `published` before filtering/pagination or `get_object_or_404()`. This prevents public result counts from revealing drafts and returns 404 for draft detail lookups. Slugs improve URLs; they are identifiers, not secrets or authorization controls.

Draft metadata and image views now use the same `is_verified_staff()` helper. It requires authenticated, active staff and OTP verification; a missing verification method returns False. Publication tests explicitly reject password-only staff at both ID and slug detail URLs and allow verified-staff ID preview and list access. Public artist endpoints expose artist records independently of item publication; decide what artist data is intentionally public.

Tests cover anonymous ID/slug draft hiding, published access, non-staff list visibility, staff preview, search, and pagination counts. Full related-response and non-staff detail coverage is still to be completed.

## 6. Upload validation

Sources: [ArtworkImage model](../items/models.py), [validators](../items/validators.py), [admin inline](../items/admin.py), [image validation tests](../items/tests/test_image_validation.py).

Uploads are currently managed through the OTP-protected Django admin inline. Nested image serialization is read-only; it is not an image-upload API.

`validate_image_size()` rejects files larger than 10 MiB. `validate_image_format()` opens content with Pillow, permits JPEG/PNG/WebP, verifies structural integrity, and restores the original file position afterward. Client MIME types and filename extensions are not used as proof of image validity.

Validators are attached to the model field and run through admin model forms. Direct `save()` does not automatically run model validation. Future upload APIs, imports, or background jobs must validate deliberately.

Validation limits images to 25 million pixels before structural verification. Pillow decompression-bomb warnings are locally converted to exceptions; both warnings and errors become ValidationError with a safe message. The file position is restored in finally.

Tests cover the 10 MiB size boundary, genuine PNG acceptance, disguised-text rejection, the 25-million-pixel boundary, and decompression-bomb warning/error handling. Dimension and bomb tests mock Pillow rather than allocate huge files; they verify application behavior, not the correctness of Pillow internals. Unit size tests simulate the reported size; they are not ingress/body-limit tests. Unsupported real image formats, corrupt image variants, and admin upload integration still need additional coverage.

Before deployment: add remaining negative-format/admin integration coverage, set request/upload limits at ingress, review multi-frame/resource handling, consider image re-encoding and metadata removal, and keep Pillow patched. Structural verification does not guarantee a file is harmless in every downstream context.

## 7. Authorization-aware image delivery

Sources: `artwork_image` in [views](../items/views.py), [URL configuration](../config/urls.py), [image serializer](../items/serializers.py).

`GET /artwork-images/<image_id>/` checks the current parent artwork's publication status. Active authenticated MFA-verified staff can access drafts; other callers are restricted to published artwork images. Missing/disallowed records and missing files return 404. `FileResponse` streams the bytes without redirecting to a raw storage URL.

`never_cache` sets private/no-store and related anti-cache directives. `X-Content-Type-Options: nosniff` is explicitly set; SecurityMiddleware normally adds it too. This header does not replace correct content types, upload validation, or safe storage.

The direct DEBUG media-serving URL pattern has been removed. Files remain on local disk, but that old route is no longer deliberately exposed through Django's URL configuration.

Image delivery integration and remaining limitations:

- The duplicate `artwork_image` definition has been removed; one implementation remains.
- `ArtworkImageSerializer.image` now reverses the protected image endpoint instead of exposing a raw storage URL.
- Admin image inlines use a plain file-upload widget and a protected View image link rather than displaying the storage URL.
- [Image delivery tests](../items/tests/test_image_delivery.py) verify published bytes, unpublish-to-404 at the same URL, retained MFA-verified staff access, and private/no-store headers on successful responses. Additional roles, missing files, and direct media denial still need coverage.
- Raised Http404 exceptions bypass never_cache response processing; cache policy for error responses remains unfinished. Configure edge caching accordingly and add regression coverage.
- Production originals must remain private. Already downloaded copies cannot be recalled, and no-store is not a guarantee against a malicious client saving bytes.

## 8. Built-in headers, rendering, and development configuration

Sources: [settings](../config/settings.py), [account base template](../templates/two_factor/_base.html).

SecurityMiddleware and XFrameOptionsMiddleware are enabled. Default header behavior is a framework baseline, not a completed production review. The login presentation template changes styling, not authentication policy. Review external stylesheet dependencies when designing CSP and consider locally hosted assets.

Development still uses `DEBUG=True`, a publicly known development-only secret key, localhost allowed hosts, and SQLite. These are not production settings. Replace the key with an environment-managed secret and configure HTTPS, secure session/CSRF cookies, host/origin policy, logging, and production database credentials before deployment. Never reuse the development key for production sessions.

## 9. Source control and dependencies

Sources: [.gitignore](../.gitignore), [requirements](../requirements.txt), [lockfile](../requirements-lock.txt).

Ignore rules exclude the virtual environment, environment files, SQLite databases, media uploads, and the local project checklist. Ignore rules do not remove already-tracked content or Git history. Review staged files and history and rotate any exposed credentials.

Dependency declarations include MFA and Pillow, and the refreshed lockfile records their installed dependencies. Keep both synchronized after future package changes. Add dependency/secret scanning and a deliberate update process before release.

No credentials, OTP secrets, recovery codes, database dumps, or private image originals belong in architecture documentation.

## 10. Agreed infrastructure design — not implemented

Plan: Next.js frontend on Vercel, Django backend on Render, PostgreSQL on Neon, free tiers initially, and private persistent object storage to be selected.

All production API traffic should pass through Cloudflare. Published reads remain public; administration, enrollment/recovery, and management operations require Access in addition to Django protections. Confirm provider/free-tier support before adopting a specific topology.

DNS proxying alone does not prevent origin bypass. Protect alternate backend hostnames and validate signed Access assertions for protected operations, including signature, issuer, audience, and expiry. Public-read origin restrictions require a separate compatible design; Access validation on private routes alone does not force all public traffic through Cloudflare.

Do not cache drafts, authenticated responses, or writes in shared caches. Keep unpublished media private and check publication state on delivery. Configure trusted proxies carefully rather than trusting forwarded identity/IP headers from arbitrary clients.

Cloudflare, production origin controls, object storage, production TLS/cookies, monitoring, backups/restore exercises, incident response, and rate limiting remain planned work—not delivered guarantees.

## 11. Verification commands and next priorities

```bash
./.venv/bin/python manage.py test
./.venv/bin/python manage.py test items.tests.test_session_security
./.venv/bin/python manage.py test items.tests.test_image_validation
./.venv/bin/python manage.py makemigrations --check --dry-run
```

Run `check --deploy` against the eventual production settings; a clean local system check is not a deployment audit.

Immediate priorities:

1. Expand image-access role coverage and define cache headers for denied/missing-image responses.
2. Test image publication transitions, role restrictions, and cache headers.
3. Complete remaining format/admin upload tests and ingress/resource limits; application size/pixel/bomb handling is implemented.
4. Expand regression coverage for password-only staff list visibility, verified-staff slug preview, inactive users, and the global permission default.
5. Finish recovery, bypass, and rate-limiting work before release.
6. Complete production settings, storage/Cloudflare origin design, dependency checks, and backup/incident procedures.

The local PROJECT_CHECKLIST.md tracks the larger guided-learning plan. This document should be updated whenever controls or their supporting evidence change.
