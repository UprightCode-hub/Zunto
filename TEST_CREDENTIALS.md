# Zunto Test Credentials

These accounts are demo/test accounts only. Seed commands repair them on every run so they remain login-ready.

## Core Test Users

| Email | Password | Notes |
| --- | --- | --- |
| `buyer@test.com` | `Test123!` | Basic buyer created by `create_test_users` |
| `seller@test.com` | `Test123!` | Approved seller created by `create_test_users` |
| `service@test.com` | `Test123!` | Service provider created by `create_test_users` |

## Demo Marketplace Sellers

Password for all seeded marketplace sellers below: `Seller1234!`

| Email | Notes |
| --- | --- |
| `chukwuemeka.obi@zunto-demo.com` | Seeded by `seed_db` / `seed_demo` |
| `adaeze.nwosu@zunto-demo.com` | Seeded by `seed_db` / `seed_demo` |
| `babatunde.adeyemi@zunto-demo.com` | Seeded by `seed_db` / `seed_demo` |
| `scale-seller-01@zunto-scale.local` | Created/repaired by scale product seeding |
| `scale-seller-02@zunto-scale.local` | Created/repaired by scale product seeding |
| `scale-seller-03@zunto-scale.local` | Created/repaired by scale product seeding |

## Demo Marketplace Buyers

Password for buyers seeded by `seed_db`: `Seller1234!`

Examples:

| Email | Notes |
| --- | --- |
| `adaora.okafor@zunto-buyer.com` | Seeded by `seed_db` / `seed_demo` |
| `kunle.balogun@zunto-buyer.com` | Seeded by `seed_db` / `seed_demo` |
| `zainab.suleiman@zunto-buyer.com` | Seeded by `seed_db` / `seed_demo` |

## Email Verification Demo

Signup creates an inactive account and sends a 6-digit verification code. If the Django email backend is `django.core.mail.backends.console.EmailBackend`, the backend prints the code with this prefix:

```text
[Zunto email verification] user@example.com code: 123456
```
